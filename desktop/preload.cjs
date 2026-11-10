// What the viewer sees of the app (web/src/ui/desktop.ts): with it, Esc and a controller's Menu button open its menu
// (full screen, quit); the website has no such object and no menu. main.mjs answers only the app's own pages.
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('voxelpestDesktop', {
  quit: () => ipcRenderer.invoke('quit'),
  fullscreen: (on) => ipcRenderer.invoke('fullscreen', on),
  version: () => ipcRenderer.invoke('version'),
});
