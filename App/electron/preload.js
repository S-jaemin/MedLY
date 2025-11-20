// electron/preload.js

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  loadMainUI: () => ipcRenderer.invoke('load-main-ui')
});