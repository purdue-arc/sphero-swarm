import { app, BrowserWindow, ipcMain } from "electron";
import path from "path";
import os from "os";
import { fileURLToPath } from "url";
import { spawn, spawnSync } from "child_process";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

function getPythonExecutable() {
  const home = os.homedir();
  const candidates = [
    // PATH-based lookups (uses shell so conda/pyenv/brew envs are found)
    "python3",
    "python",
    // macOS Homebrew (Apple Silicon)
    "/opt/homebrew/bin/python3",
    // macOS Homebrew (Intel)
    "/usr/local/bin/python3",
    // conda (common install locations)
    `${home}/miniconda3/bin/python3`,
    `${home}/anaconda3/bin/python3`,
    `${home}/miniforge3/bin/python3`,
    // pyenv shims
    `${home}/.pyenv/shims/python3`,
  ];
  for (const v of candidates) {
    const result = spawnSync(v, ["--version"], { shell: false });
    if (result.status === 0) {
      console.log(`Using Python executable: ${v}`);
      return v;
    }
  }
  throw new Error("Python not found. Install Python 3 via Homebrew (brew install python) or conda.");
}

function getConfig() {
  return new Promise((resolve, reject) => {
    const pythonExec = getPythonExecutable();
    const moduleFolder = path.join(__dirname, "../link");
    const pythonProcess = spawn(pythonExec, ["-m", "gui"], {
      cwd: moduleFolder,
      stdio: "pipe"
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

const DEFAULT_PERCEPTION_CONFIG = {
  inputSource: "webcam",
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
    .map((t) => (t === "head" ? "head" : "tail"));
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
  const pythonExec = getPythonExecutable();
  const moduleFolder = path.join(__dirname, "../../perception");

  const pyArgs = ["sphero_spotter.py", "-s"]; // -s = WebSocket server mode

  if (cfg.inputSource === "webcam") {
    pyArgs.push("-w");
  } else if (cfg.inputSource === "video" && cfg.videoPath) {
    pyArgs.push("-v", cfg.videoPath);
  }
  // oakd = no flag needed

  pyArgs.push("-m", cfg.model);
  pyArgs.push("--conf", String(cfg.conf));
  pyArgs.push("--imgsz", String(cfg.imgsz));
  if (cfg.grid)    pyArgs.push("-g");
  if (cfg.locked)  pyArgs.push("-l");
  if (cfg.latency) pyArgs.push("-t");

  spheroProcess = spawn(pythonExec, pyArgs, { cwd: moduleFolder, stdio: "pipe" });
  spheroProcess.stderr.on("data", (data: any) => { console.error(`Python error: ${data.toString()}`); });
  spheroProcess.on("close", (code: any, signal: any) => {
    console.log(`Sphero Spotter exited (code=${code}, signal=${signal})`);
    spheroProcess = null;
  });
  return true;
}

function stopSpheroSpotter(force = false) {
  if (!spheroProcess) return;
  console.log("Stopping Sphero Spotter...");
  spheroProcess.kill(force ? "SIGKILL" : "SIGTERM");
  spheroProcess = null;
  return true;
}

function startControls(config: any = {}) {
  if (controlsProcess) { console.log("Controls already running"); return; }
  const pythonExec = getPythonExecutable();
  const moduleFolder = path.join(__dirname, "../../");

  console.log(`Starting controls server with Python: ${pythonExec}`);

  controlsProcess = spawn(pythonExec, ["-u", "-m", "controls.Fall_2025_Sphero_Swarm_Server", "-s"], {
    cwd: moduleFolder,
    stdio: "pipe",
    env: {
      ...process.env,
      PYTHONUNBUFFERED: "1",
    },
  });

  controlsProcess.stdout.on("data", (data: any) => {
    process.stdout.write(data.toString());
  });
  controlsProcess.stderr.on("data", (data: any) => {
    process.stderr.write(data.toString());
  });
  controlsProcess.on("error", (error: any) => {
    console.error(`Controls server failed to start: ${error?.message ?? error}`);
  });
  controlsProcess.on("close", (code: any, signal: any) => {
    console.log(`Controls server exited (code=${code}, signal=${signal})`);
    controlsProcess = null;
  });
  return true;
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

  // Simulate loading progress on the splash while Vite/React loads.
  // Cap at 95 — will jump to 100 when React is ready
  let progress = 0;
  const progressInterval = setInterval(() => {
    // Advance quickly at first, then slow down to wait for the real ready signal
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

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});