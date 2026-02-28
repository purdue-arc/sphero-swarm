import { app, BrowserWindow, ipcMain } from "electron";
import path from "path";
import { fileURLToPath } from "url";
import { spawn, spawnSync } from "child_process";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

function getPythonExecutable() {
  const versions = ["python3", "python"];
  for (const v of versions) {
    const result = spawnSync(v, ["--version"]);
    if (result.status === 0) {
      console.log(`Using Python executable: ${v}`);
      return v;
    }
  }
  throw new Error("Python not found in PATH");
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

function startSpheroSpotter() {
  if (spheroProcess) { console.log("Sphero Spotter already running"); return; }
  const pythonExec = getPythonExecutable();
  const moduleFolder = path.join(__dirname, "../../perception");
  spheroProcess = spawn(pythonExec, ["sphero_spotter.py", "-w", "-s"], { cwd: moduleFolder, stdio: "pipe" });
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

ipcMain.handle("start-sphero-spotter", async () => { startSpheroSpotter(); return { status: "started" }; });
ipcMain.handle("stop-sphero-spotter", async () => { stopSpheroSpotter(); return { status: "stopped" }; });
ipcMain.handle("get-constants", async () => {
  try { return await getConfig(); }
  catch (error) { console.error("Error getting Python constants:", error); throw error; }
});
ipcMain.handle("quit-app", () => { app.quit(); });
ipcMain.handle("splash-button-clicked", () => {
  showMainAndCloseSplash();
  return { status: "splash-dismissed" };
});
ipcMain.handle("save-constants", async (_event, constants) => {
  try {
    const fs = await import("fs/promises");
    const constantsPath = path.join(__dirname, "../../constants.json");
    await fs.writeFile(constantsPath, JSON.stringify(constants, null, 2));
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