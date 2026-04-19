import { app, BrowserWindow, ipcMain } from "electron";
import path from "path";
import { existsSync } from "fs";
import { fileURLToPath } from "url";
import { spawn, spawnSync } from "child_process";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

type UvCommand = {
  executable: string;
};

function getUvCommand(): UvCommand {
  const repoRoot = path.resolve(__dirname, "../../");

  if (!existsSync(path.join(repoRoot, "pyproject.toml"))) {
    throw new Error("pyproject.toml not found. Run the GUI from the repository root.");
  }

  if (!existsSync(path.join(repoRoot, "uv.lock"))) {
    throw new Error("uv.lock not found. Install dependencies with uv before launching the GUI.");
  }

  const uvCheck = spawnSync("uv", ["--version"], { shell: false });
  if (uvCheck.status !== 0) {
    throw new Error("uv is required but was not found on PATH.");
  }

  return { executable: "uv" };
}

function getConfig() {
  return new Promise((resolve, reject) => {
    const uvCmd = getUvCommand();
    const repoRoot = path.resolve(__dirname, "../../");
    const moduleFolder = path.join(__dirname, "../link");
    const pythonProcess = spawn(uvCmd.executable, ["run", "--project", repoRoot, "python", "-m", "gui"], {
      cwd: moduleFolder,
      stdio: "pipe",
    });

    let dataString = "";
    pythonProcess.stdout.on("data", (data) => { dataString += data.toString(); });
    pythonProcess.stderr.on("data", (data) => { console.error(`Python Error: ${data}`); });
    pythonProcess.on("close", (code) => {
      if (code !== 0) { reject(new Error(`Python process exited with code ${code}`)); return; }
      try { resolve(JSON.parse(dataString)); }
      catch (error: any) { reject(new Error(`Failed to parse JSON: ${error.message}`)); }
    });
  });
}

let spheroProcess: any = null;
let controlsProcess: any = null;
const expectedControlsExitPids = new Set<number>();

function getListeningPidsForPort(port: number): number[] {
  if (process.platform !== "win32") return [];

  const result = spawnSync("netstat", ["-ano", "-p", "tcp"], {
    shell: false,
    windowsHide: true,
    encoding: "utf8",
  });

  if (result.status !== 0 || !result.stdout) return [];

  const suffix = `:${port}`;
  const pids = new Set<number>();

  for (const rawLine of result.stdout.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line.startsWith("TCP")) continue;

    const cols = line.split(/\s+/);
    // Expected: TCP local-address foreign-address state pid
    if (cols.length < 5) continue;

    const localAddress = cols[1] ?? "";
    const state = cols[3] ?? "";
    const pid = Number(cols[4]);

    if (!localAddress.endsWith(suffix)) continue;
    if (state.toUpperCase() !== "LISTENING") continue;
    if (!Number.isInteger(pid) || pid <= 0) continue;

    pids.add(pid);
  }

  return [...pids];
}

function killWindowsPidTree(pid: number, force = true) {
  const args = ["/pid", String(pid), "/t"];
  if (force) args.push("/f");
  spawnSync("taskkill", args, { shell: false, windowsHide: true });
}

function cleanupOrphanedControlsServer(port = 6768) {
  if (process.platform !== "win32") return;

  const pids = getListeningPidsForPort(port);
  if (pids.length === 0) return;

  for (const pid of pids) {
    // Best-effort cleanup for stale controls servers that survived abrupt exits.
    killWindowsPidTree(pid, true);
  }
}

function cleanupOrphanedPerceptionServers() {
  if (process.platform !== "win32") return;

  const perceptionPorts = [6767, 6770];
  const pids = new Set<number>();

  for (const port of perceptionPorts) {
    for (const pid of getListeningPidsForPort(port)) {
      pids.add(pid);
    }
  }

  if (pids.size === 0) return;

  for (const pid of pids) {
    // Best-effort cleanup for stale perception servers that survive interrupts.
    killWindowsPidTree(pid, true);
  }
}

function terminateProcessTree(child: any, force = false) {
  if (!child || child.killed || typeof child.pid !== "number") return;

  if (process.platform === "win32") {
    // On Windows, kill the full process tree so uv and spawned python both exit.
    killWindowsPidTree(child.pid, force);
    return;
  }

  try {
    child.kill(force ? "SIGKILL" : "SIGTERM");
  } catch (error) {
    console.error("Failed to terminate child process:", error);
  }
}

const DEFAULT_PERCEPTION_CONFIG = {
  inputSource: "oakd",
  model: "./models/bestv3.pt",
  conf: 0.25,
  imgsz: 640,
  grid: false,
  locked: false,
  latency: false,
};

function normalizeConstantsForSave(raw: any) {
  const n = Math.max(
    1,
    Number(raw?.N_SPHEROS ?? raw?.SPHERO_TAGS?.length ?? raw?.INITIAL_POSITIONS?.length ?? 1)
  );

  const tags = Array.isArray(raw?.SPHERO_TAGS) ? [...raw.SPHERO_TAGS] : [];
  const positions = Array.isArray(raw?.INITIAL_POSITIONS)
    ? raw.INITIAL_POSITIONS.map((p: any) => [Number(p?.[0] ?? 0), Number(p?.[1] ?? 0)])
    : [];
  const traits = Array.isArray(raw?.INITIAL_TRAITS) ? [...raw.INITIAL_TRAITS] : [];

  while (tags.length < n) tags.push("SB-XXXX");
  while (positions.length < n) positions.push([0, 0]);
  while (traits.length < n) traits.push("tail");

  const normalizedTraits = traits
    .slice(0, n)
    .map((t: any) => (t === "head" ? "head" : "tail"));
  if (!normalizedTraits.includes("head")) normalizedTraits[0] = "head";

  return {
    ...raw,
    N_SPHEROS: n,
    SPHERO_TAGS: tags.slice(0, n),
    INITIAL_POSITIONS: positions.slice(0, n),
    INITIAL_TRAITS: normalizedTraits,
  };
}

function startSpheroSpotter(config: any = {}) {
  if (spheroProcess) { console.log("Sphero Spotter already running"); return; }
  const cfg = { ...DEFAULT_PERCEPTION_CONFIG, ...config };
  const uvCmd = getUvCommand();
  const repoRoot = path.resolve(__dirname, "../../");
  const moduleFolder = path.join(__dirname, "../../perception");

  // Prevent stale perception instances from keeping camera/ports active.
  cleanupOrphanedPerceptionServers();

  const pyArgs = ["run", "--project", repoRoot, "python", "sphero_spotter.py", "-s"]; // -s = WebSocket server mode

  if (cfg.inputSource === "webcam") {
    pyArgs.push("-w");
  } else if (cfg.inputSource === "video" && cfg.videoPath) {
    pyArgs.push("-v", cfg.videoPath);
  }
  // // oakd = no flag needed

  pyArgs.push("-m", cfg.model);
  pyArgs.push("--conf", String(cfg.conf));
  pyArgs.push("--imgsz", String(cfg.imgsz));
  if (cfg.grid)    pyArgs.push("-g");
  if (cfg.locked)  pyArgs.push("-l");
  if (cfg.latency) pyArgs.push("-t");

  spheroProcess = spawn(uvCmd.executable, pyArgs, { cwd: moduleFolder, stdio: "pipe" });
  spheroProcess.stderr.on("data", (data: any) => { console.error(`Python error: ${data.toString()}`); });
  spheroProcess.on("close", (code: any, signal: any) => {
    console.log(`Sphero Spotter exited (code=${code}, signal=${signal})`);
    spheroProcess = null;
  });
  return true;
}

function stopSpheroSpotter(force = false) {
  if (spheroProcess) {
    console.log("Stopping Sphero Spotter...");
    terminateProcessTree(spheroProcess, force);
    spheroProcess = null;
  }

  // Also clean up stale listeners if PID tracking missed an orphaned child.
  cleanupOrphanedPerceptionServers();
  return true;
}

function stopControls(force = false) {
  if (controlsProcess) {
    console.log("Stopping controls server...");
    if (typeof controlsProcess.pid === "number") {
      expectedControlsExitPids.add(controlsProcess.pid);
    }
    terminateProcessTree(controlsProcess, force);
    controlsProcess = null;
  }

  // Also clean up any stale listener if a previous run was interrupted.
  cleanupOrphanedControlsServer(6768);
  return true;
}

function startControls(config: any = {}) {
  if (controlsProcess) { console.log("Controls already running"); return; }
  const uvCmd = getUvCommand();
  const repoRoot = path.resolve(__dirname, "../../");
  const moduleFolder = path.join(__dirname, "../../");

  // Prevent bind failures from orphaned servers left by abrupt shutdowns.
  cleanupOrphanedControlsServer(6768);

  console.log(`Starting controls server with uv: uv run --project ${repoRoot} python -u -m controls.Controls_Server -s`);

  controlsProcess = spawn(
    uvCmd.executable,
    ["run", "--project", repoRoot, "python", "-u", "-m", "controls.Controls_Server", "-s"],
    {
      cwd: moduleFolder,
      stdio: "pipe",
      env: {
        ...process.env,
        PYTHONUNBUFFERED: "1",
      },
    }
  );

  controlsProcess.stdout.on("data", (data: any) => {
    process.stdout.write(data.toString());
  });
  controlsProcess.stderr.on("data", (data: any) => {
    process.stderr.write(data.toString());
  });
  controlsProcess.on("error", (error: any) => {
    console.error(`Controls server failed to start: ${error?.message ?? error}`);
  });
  const startedProcessPid = typeof controlsProcess.pid === "number" ? controlsProcess.pid : null;
  controlsProcess.on("close", (code: any, signal: any) => {
    if (startedProcessPid !== null && expectedControlsExitPids.has(startedProcessPid)) {
      expectedControlsExitPids.delete(startedProcessPid);
      console.log(`Controls server stopped (code=${code}, signal=${signal})`);
    } else {
      console.log(`Controls server exited (code=${code}, signal=${signal})`);
    }
    controlsProcess = null;
  });
  return true;
}

function waitForControlsStartup(windowMs = 1200, pollMs = 100): Promise<boolean> {
  const startedAt = Date.now();

  return new Promise((resolve) => {
    const poll = () => {
      if (!controlsProcess) {
        resolve(false);
        return;
      }

      if (Date.now() - startedAt >= windowMs) {
        resolve(true);
        return;
      }

      setTimeout(poll, pollMs);
    };

    poll();
  });
}

ipcMain.handle("start-sphero-spotter", async (_event, config) => { startSpheroSpotter(config); return { status: "started" }; });
ipcMain.handle("stop-sphero-spotter", async () => { stopSpheroSpotter(); return { status: "stopped" }; });
ipcMain.handle("get-constants", async () => {
  try { return await getConfig(); }
  catch (error) { console.error("Error getting Python constants:", error); throw error; }
});
ipcMain.handle("quit-app", () => { app.quit(); });
ipcMain.handle("start-controls", () => {
  const started = startControls();
  return { status: started ? "started" : "already-running" };
});
ipcMain.handle("stop-controls", () => {
  const stopped = stopControls();
  return { status: stopped ? "stopped" : "not-running" };
});
ipcMain.handle("refresh-controls", async () => {
  stopControls(true);
  const started = startControls();
  if (!started) {
    return { status: "failed" };
  }

  const ready = await waitForControlsStartup(1200, 100);
  return { status: ready ? "started" : "failed" };
});
ipcMain.handle("splash-button-clicked", () => {
  showMainAndCloseSplash();
  return { status: "splash-dismissed" };
});
ipcMain.handle("save-constants", async (_event, constants) => {
  try {
    const fs = await import("fs/promises");
    const constantsPath = path.join(__dirname, "../../constants.json");
    const normalized = normalizeConstantsForSave(constants);
    await fs.writeFile(constantsPath, JSON.stringify(normalized, null, 2));
    return { status: "saved" };
  } catch (error) { console.error("Error saving constants:", error); throw error; }
});
ipcMain.handle("app-render-complete", () => {
  sendSplashProgress(100);
  return { status: "progress-complete" };
});

let appReadyTime: number | null = null;

// Signal from the React app that it has fully mounted and is ready to show
ipcMain.handle("app-ready", () => {
  appReadyTime = Date.now();
  showMainAndCloseSplash();
});

let splashWindow: BrowserWindow | null = null;
let mainWindow: BrowserWindow | null = null;
let mainWindowCreatedTime: number | null = null;

function sendSplashProgress(pct: number) {
  if (splashWindow && !splashWindow.isDestroyed()) {
    splashWindow.webContents.send("splash-progress", pct);
  }
}

function showMainAndCloseSplash() {
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.show();
  }

  if (splashWindow && !splashWindow.isDestroyed()) {
    setTimeout(() => {
      if (splashWindow && !splashWindow.isDestroyed()) {
        splashWindow.close();
      }
      splashWindow = null;
    }, 300);
  }
}

function createSplashWindow() {
  splashWindow = new BrowserWindow({
    fullscreen: true,
    frame: false,
    transparent: false,
    backgroundColor: "#060c14",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  splashWindow.loadFile(path.join(__dirname, "splash.html"));
  splashWindow.on("closed", () => { splashWindow = null; });
}

function createMainWindow() {
  mainWindowCreatedTime = Date.now();
  mainWindow = new BrowserWindow({
    fullscreen: true,
    show: false, // Hidden until React signals ready
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.loadURL("http://localhost:5173");
  mainWindow.on("closed", () => { mainWindow = null; });

  let progress = 0;
  const progressInterval = setInterval(() => {
    const step = progress < 60 ? Math.random() * 12 + 4 : Math.random() * 2 + 0.5;
    progress = Math.min(progress + step, 95); // Cap at 95 — jumps to 100 on app-ready
    sendSplashProgress(Math.round(progress));
    if (progress >= 95) clearInterval(progressInterval);
  }, 500);
}

app.whenReady().then(() => {
  createSplashWindow();
  createMainWindow();
});

app.on("before-quit", () => {
  // Ensure child processes release their sockets before Electron exits.
  stopControls(true);
  stopSpheroSpotter(true);
});

app.on("will-quit", () => {
  stopControls(true);
  stopSpheroSpotter(true);
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    stopControls(true);
    stopSpheroSpotter(true);
    app.quit();
  }
});

process.on("SIGINT", () => {
  stopControls(true);
  stopSpheroSpotter(true);
  app.quit();
});

process.on("SIGTERM", () => {
  stopControls(true);
  stopSpheroSpotter(true);
  app.quit();
});

process.on("exit", () => {
  stopControls(true);
  stopSpheroSpotter(true);
});