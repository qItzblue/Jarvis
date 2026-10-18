const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("jarvisDesktop", {
  onPushToTalk: (cb) => {
    const listener = () => cb();
    ipcRenderer.on("ptt", listener);
    return () => ipcRenderer.removeListener("ptt", listener);
  },
  setMiniMode: (on) => ipcRenderer.invoke("mini-mode", on),
  hotkey: process.env.JARVIS_PTT_KEY || "Ctrl+Shift+Space",
});
