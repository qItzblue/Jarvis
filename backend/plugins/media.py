from ..core import osctl
from ..core.plugins import Plugin, tool

WIN_KEYS = {"play_pause": 0xB3, "next": 0xB0, "previous": 0xB1, "mute": 0xAD, "volume_up": 0xAF, "volume_down": 0xAE}


class MediaPlugin(Plugin):
    name, title, category, icon = "media", "Volume, brightness & media", "computer", "volume-2"
    description = "Controls system volume, screen brightness and media playback."

    async def _win_key(self, key: str, times: int = 1):
        code = WIN_KEYS[key]
        script = ("$w=New-Object -ComObject WScript.Shell;" +
                  f"1..{times}|%{{$w.SendKeys([char]{code})}}")
        return await osctl.powershell(script)

    @tool("Set the system volume (0-100).", {"level": {"type": "integer"}})
    async def set_volume(self, level: int):
        level = max(0, min(int(level), 100))
        if osctl.SYSTEM == "Darwin":
            return await osctl.osascript(f"set volume output volume {level}")
        if osctl.SYSTEM == "Windows":
            await self._win_key("volume_down", 50)
            return await self._win_key("volume_up", level // 2)
        if osctl.have("pactl"):
            return await osctl.run("pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{level}%")
        return await osctl.run("amixer", "sset", "Master", f"{level}%")

    @tool("Mute or unmute audio.", {"mute": {"type": "boolean"}})
    async def mute(self, mute: bool):
        if osctl.SYSTEM == "Darwin":
            return await osctl.osascript(f"set volume output muted {'true' if mute else 'false'}")
        if osctl.SYSTEM == "Windows":
            return await self._win_key("mute")
        return await osctl.run("pactl", "set-sink-mute", "@DEFAULT_SINK@", "1" if mute else "0")

    @tool("Set screen brightness (0-100).", {"level": {"type": "integer"}})
    async def set_brightness(self, level: int):
        level = max(0, min(int(level), 100))
        if osctl.SYSTEM == "Windows":
            return await osctl.powershell(
                f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,{level})")
        if osctl.SYSTEM == "Darwin":
            if osctl.have("brightness"):
                return await osctl.run("brightness", str(level / 100))
            return {"error": "Install the 'brightness' CLI (brew install brightness)."}
        return await osctl.run("brightnessctl", "set", f"{level}%")

    @tool("Control media playback.", {"action": {"type": "string", "enum": ["play_pause", "next", "previous"]}})
    async def playback(self, action: str):
        if osctl.SYSTEM == "Windows":
            return await self._win_key(action)
        if osctl.SYSTEM == "Darwin":
            cmd = {"play_pause": "playpause", "next": "next track", "previous": "previous track"}[action]
            return await osctl.osascript(f'tell application "Music" to {cmd}')
        cmd = {"play_pause": "play-pause", "next": "next", "previous": "previous"}[action]
        return await osctl.run("playerctl", cmd)
