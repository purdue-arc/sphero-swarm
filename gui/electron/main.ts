import { app, BrowserWindow } from "electron";
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

// Spawn Python script
function startPythonScript() {
  const pythonExec = getPythonExecutable();

  // Module name (dot notation), not path
  const moduleName = "gui"; // e.g., gui.py inside ../link folder

  // Set cwd to folder containing the module
  const moduleFolder = path.join(__dirname, "../link");

  const pyProcess = spawn(pythonExec, ["-m", moduleName], {
    cwd: moduleFolder,
    stdio: "pipe" // allows reading stdout/stderr
  });

  pyProcess.stdout.on("data", (data) => {
    console.log(`Python says: ${data.toString()}`);
  });

  pyProcess.stderr.on("data", (data) => {
    console.error(`Python error: ${data.toString()}`);
  });

  pyProcess.on("close", (code) => {
    console.log(`Python script exited with code ${code}`);
  });

  return pyProcess;
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1000,
    height: 700,
  });

  win.loadURL("http://localhost:5173");

  // Optional: Start Python when window is ready
  startPythonScript();
}

app.whenReady().then(createWindow);

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});