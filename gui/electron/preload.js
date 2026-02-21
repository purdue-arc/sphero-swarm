const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld("electronAPI", {
  startSpheroSpotter: () =>
    ipcRenderer.invoke("start-sphero-spotter"),
  stopSpheroSpotter: () =>
    ipcRenderer.invoke("stop-sphero-spotter"),
  getConstants: () =>
    ipcRenderer.invoke('get-constants'),
  quitApp: () => 
    ipcRenderer.invoke('quit-app')
});