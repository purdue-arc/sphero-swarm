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
  quitApp: () => 
    ipcRenderer.invoke('quit-app'),
  onSplashProgress: (callback) => {
    ipcRenderer.on("splash-progress", (_event, pct) => callback(pct));
  },
  appRenderComplete: () =>
    ipcRenderer.invoke("app-render-complete"),
  signalAppReady: () =>
    ipcRenderer.invoke("app-ready"),
  splashButtonClicked: () =>
    ipcRenderer.invoke("splash-button-clicked"),
});