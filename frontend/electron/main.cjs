// Electron shell: one window, a global push-to-talk hotkey and a compact "mini mode".
const { app, BrowserWindow, globalShortcut, ipcMain, session, shell } = require("electron");
const path = require("path");

const DEV = !!process.env.VITE_DEV;
const PTT_KEY = process.env.JARVIS_PTT_KEY || "CommandOrControl+Shift+Space";
let win;
let fullBounds = null;

function createWindow() {
  win = new BrowserWindow({
    width: 1440, height: 900, minWidth: 380, minHeight: 560,
    backgroundColor: "#05080F", title: "Jarvis", autoHideMenuBar: true,
    webPreferences: { preload: path.join(__dirname, "preload.cjs"), contextIsolation: true, nodeIntegration: false },
  });
  if (DEV) win.loadURL("http://localhost:5173");
  else win.loadFile(path.join(__dirname, "..", "dist", "index.html"));
  win.webContents.setWindowOpenHandler(({ url }) => { shell.openExternal(url); return { action: "deny" }; });
}

app.whenReady().then(() => {
  // Only the microphone and camera are ever requested, and only by our own UI.
  session.defaultSession.setPermissionRequestHandler((_wc, permission, cb) => cb(permission === "media"));
  createWindow();
  globalShortcut.register(PTT_KEY, () => win && win.webContents.send("ptt"));
  ipcMain.handle("mini-mode", (_e, on) => {
    if (!win) return;
    if (on) {
      fullBounds = win.getBounds();
      win.setAlwaysOnTop(true, "floating");
      win.setBounds({ width: 420, height: 640 });
    } else {
      win.setAlwaysOnTop(false);
      if (fullBounds) win.setBounds(fullBounds);
    }
  });
});

app.on("will-quit", () => globalShortcut.unregisterAll());
app.on("window-all-closed", () => { if (process.platform !== "darwin") app.quit(); });
app.on("activate", () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });
