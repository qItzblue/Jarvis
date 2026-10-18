from ..core import osctl
from ..core.plugins import Plugin, tool


class WindowsPlugin(Plugin):
    name, title, category, icon = "windows", "Window manager", "computer", "layout-grid"
    description = "Lists, focuses, minimises and maximises windows."

    @tool("List open windows.", {})
    async def list_windows(self):
        if osctl.SYSTEM == "Windows":
            r = await osctl.powershell("Get-Process | ? {$_.MainWindowTitle} | % {$_.MainWindowTitle}")
        elif osctl.SYSTEM == "Darwin":
            r = await osctl.osascript('tell application "System Events" to get name of every process '
                                      'whose background only is false')
            return [w.strip() for w in r.get("stdout", "").split(",") if w.strip()]
        else:
            if not osctl.have("wmctrl"):
                return {"error": "Install wmctrl for window control on Linux."}
            r = await osctl.run("wmctrl", "-l")
            return [" ".join(l.split()[3:]) for l in r.get("stdout", "").splitlines()]
        return [l.strip() for l in r.get("stdout", "").splitlines() if l.strip()]

    @tool("Bring a window to the front by (part of) its title or app name.", {"title": {"type": "string"}})
    async def focus(self, title: str):
        if osctl.SYSTEM == "Windows":
            return await osctl.powershell(f"(New-Object -ComObject WScript.Shell).AppActivate('{title}')")
        if osctl.SYSTEM == "Darwin":
            return await osctl.osascript(f'tell application "{title}" to activate')
        return await osctl.run("wmctrl", "-a", title)

    @tool("Minimise, maximise or restore a window.", {
        "title": {"type": "string"}, "action": {"type": "string", "enum": ["minimize", "maximize", "restore"]}})
    async def arrange(self, title: str, action: str):
        if osctl.SYSTEM == "Linux":
            flag = {"maximize": "add,maximized_vert,maximized_horz", "restore": "remove,maximized_vert,maximized_horz",
                    "minimize": "add,hidden"}[action]
            return await osctl.run("wmctrl", "-r", title, "-b", flag)
        if osctl.SYSTEM == "Darwin":
            val = "true" if action == "minimize" else "false"
            return await osctl.osascript(f'tell application "System Events" to set value of attribute '
                                         f'"AXMinimized" of every window of process "{title}" to {val}')
        try:
            import pygetwindow as gw
        except ImportError:
            return {"error": "pip install pygetwindow for window control on Windows."}
        wins = gw.getWindowsWithTitle(title)
        if not wins:
            return {"error": "window not found"}
        getattr(wins[0], action)()
        return {"ok": True}
