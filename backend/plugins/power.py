from ..core import osctl
from ..core.plugins import Plugin, tool

COMMANDS = {
    "Windows": {"lock": ["rundll32.exe", "user32.dll,LockWorkStation"], "shutdown": ["shutdown", "/s", "/t", "5"],
                "restart": ["shutdown", "/r", "/t", "5"], "sleep": ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"]},
    "Darwin": {"lock": ["pmset", "displaysleepnow"], "shutdown": ["osascript", "-e", 'tell app "System Events" to shut down'],
               "restart": ["osascript", "-e", 'tell app "System Events" to restart'], "sleep": ["pmset", "sleepnow"]},
    "Linux": {"lock": ["loginctl", "lock-session"], "shutdown": ["systemctl", "poweroff"],
              "restart": ["systemctl", "reboot"], "sleep": ["systemctl", "suspend"]},
}


class PowerPlugin(Plugin):
    name, title, category, icon = "power", "Power", "computer", "power"
    description = "Lock, sleep, restart or shut down the computer (always asks first)."

    async def _do(self, action: str):
        return await osctl.run(*COMMANDS[osctl.SYSTEM][action])

    @tool("Lock the computer.", {}, confirm=True)
    async def lock(self):
        return await self._do("lock")

    @tool("Put the computer to sleep.", {}, confirm=True)
    async def sleep(self):
        return await self._do("sleep")

    @tool("Restart the computer.", {}, confirm=True)
    async def restart(self):
        return await self._do("restart")

    @tool("Shut down the computer.", {}, confirm=True)
    async def shutdown(self):
        return await self._do("shutdown")
