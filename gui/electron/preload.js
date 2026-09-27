const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld("electronAPI", {
  startSpheroSpotter: (config) =>
    ipcRenderer.invoke("start-sphero-spotter", config),
  stopSpheroSpotter: () =>
    ipcRenderer.invoke("stop-sphero-spotter"),
  getConstants: () =>
    ipcRenderer.invoke('get-constants'),
  saveConstants: (constants) =>
    ipcRenderer.invoke('save-constants', constants),
  getPerceptionTuning: () =>
    ipcRenderer.invoke('get-perception-tuning'),
  savePerceptionTuning: (values) =>
    ipcRenderer.invoke('save-perception-tuning', values),
  quitApp: () => 
    ipcRenderer.invoke('quit-app'),
  onSplashProgress: (callback) => {
    ipcRenderer.on("splash-progress", (_event, pct) => callback(pct));
  },
  startControls: () =>
    ipcRenderer.invoke("start-controls"),
  stopControls: () =>
    ipcRenderer.invoke("stop-controls"),
  refreshControls: () =>
    ipcRenderer.invoke("refresh-controls"),
  appRenderComplete: () =>
    ipcRenderer.invoke("app-render-complete"),
  signalAppReady: () =>
    ipcRenderer.invoke("app-ready"),
  splashButtonClicked: () =>
    ipcRenderer.invoke("splash-button-clicked"),
});