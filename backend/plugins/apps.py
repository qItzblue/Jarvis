import psutil

from ..core import osctl
from ..core.plugins import Plugin, tool


class AppsPlugin(Plugin):
    name, title, category, icon = "apps", "Apps", "computer", "app-window"
    description = "Opens and closes applications and websites."

    @tool("Open an application by name, or a URL/file.", {"target": {"type": "string"}})
    async def open(self, target: str):
        if osctl.SYSTEM == "Windows":
            return await osctl.run("cmd", "/c", "start", "", target)
        if osctl.SYSTEM == "Darwin":
            if target.startswith(("http", "/", "~")):
                return await osctl.run("open", target)
            return await osctl.run("open", "-a", target)
        if target.startswith(("http", "/", "~")):
            return await osctl.run("xdg-open", target)
        return await osctl.run("gtk-launch", target) if osctl.have("gtk-launch") else await osctl.run(target)

    @tool("Close (terminate) an application by process name.", {"name": {"type": "string"}}, confirm=True)
    async def close(self, name: str):
        killed = []
        for p in psutil.process_iter(["pid", "name"]):
            if name.lower() in (p.info["name"] or "").lower():
                try:
                    p.terminate()
                    killed.append(p.info["name"])
                except psutil.Error:
                    pass
        return {"closed": killed} if killed else {"error": f"No running app matching '{name}'"}

    @tool("List running applications.", {})
    async def running(self):
        names = sorted({(p.info["name"] or "") for p in psutil.process_iter(["name"])} - {""})
        return names[:300]
