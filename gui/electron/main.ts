import { app, BrowserWindow, ipcMain } from "electron";
import path from "path";
import { fileURLToPath } from "url";
import { spawn, spawnSync } from "child_process";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Helper to find a valid Python executable
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

    let dataString = '';

    pythonProcess.stdout.on('data', (data) => {
      dataString += data.toString();
    });

    pythonProcess.stderr.on('data', (data) => {
      console.error(`Python Error: ${data}`);
    });

    pythonProcess.on('close', (code) => {
      if (code !== 0) {
        reject(new Error(`Python process exited with code ${code}`));
        return;
      }

      try {
        const jsonState = JSON.parse(dataString);
        resolve(jsonState);
      } catch (error: any) {
        reject(new Error(`Failed to parse JSON: ${error.message}`));
      }
    });
  });
}

let spheroProcess: any = null;

function startSpheroSpotter() {
  if (spheroProcess) {
    console.log("Sphero Spotter already running");
    return;
  }

  const pythonExec = getPythonExecutable();

  const moduleFolder = path.join(__dirname, "../../perception");

  spheroProcess = spawn(pythonExec, ["sphero_spotter.py", "-w", "-s"], {
    cwd: moduleFolder,
    stdio: "pipe"
  });

  spheroProcess.stderr.on("data", (data: any) => {
    console.error(`Python error: ${data.toString()}`);
  });

  spheroProcess.on("close", (code: any, signal: any) => {
    console.log(`Sphero Spotter exited (code=${code}, signal=${signal})`);
    spheroProcess = null;
  });

  return true;
}

function stopSpheroSpotter(force = false) {
  if (!spheroProcess) return;

  console.log("Stopping Sphero Spotter...");

  if (force) {
    spheroProcess.kill("SIGKILL");
  } else {
    spheroProcess.kill("SIGTERM");
  }

  spheroProcess = null;

  return true
}


ipcMain.handle("start-sphero-spotter", async () => {
  startSpheroSpotter();
  return { status: "started" };
});

ipcMain.handle("stop-sphero-spotter", async () => {
  stopSpheroSpotter();
  return { status: "stopped" };
});

ipcMain.handle('get-constants', async () => {
  try {
    const constants = await getConfig();
    return constants;
  } catch (error) {
    console.error('Error getting Python constants:', error);
    throw error;
  }
});


function createWindow() {
  const win = new BrowserWindow({
    width: 1000,
    height: 700,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  win.loadURL("http://localhost:5173");
}

app.whenReady().then(createWindow);

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});