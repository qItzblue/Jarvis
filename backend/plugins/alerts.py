import asyncio
from datetime import datetime, timezone

import psutil

from ..core.plugins import Plugin


class AlertsPlugin(Plugin):
    name, title, category, icon = "alerts", "Proactive alerts", "automation", "bell"
    description = "Warns you about upcoming meetings and low battery without being asked."
    settings_schema = {
        "meeting_minutes": {"label": "Warn before meetings (minutes)", "type": "number", "default": 10},
        "battery_percent": {"label": "Low battery warning (%)", "type": "number", "default": 15},
    }

    def __init__(self, ctx):
        super().__init__(ctx)
        self._task = None
        self._warned: set[str] = set()

    def check_battery(self) -> dict | None:
        bat = psutil.sensors_battery() if hasattr(psutil, "sensors_battery") else None
        if not bat or bat.power_plugged:
            self._warned.discard("battery")
            return None
        if bat.percent <= float(self.setting("battery_percent")) and "battery" not in self._warned:
            self._warned.add("battery")
            self.ctx.bus.alert("🔋 Battery low", f"{round(bat.percent)}% remaining — plug in soon.", "warning")
            return {"battery": bat.percent}
        return None

    async def check_meetings(self) -> list[str]:
        cal = self.ctx.registry.get("calendar")
        if not cal:
            return []
        warned = []
        lead = float(self.setting("meeting_minutes")) * 60
        now = datetime.now(timezone.utc)
        for ev in await cal.upcoming(1, 10):
            try:
                start = datetime.fromisoformat(ev["start"].replace("Z", "+00:00"))
            except ValueError:
                continue
            if start.tzinfo and 0 < (start - now).total_seconds() <= lead and ev["id"] not in self._warned:
                self._warned.add(ev["id"])
                mins = round((start - now).total_seconds() / 60)
                self.ctx.bus.alert("📅 Meeting soon", f"{ev['summary']} starts in {mins} minutes.", "warning")
                warned.append(ev["id"])
        return warned

    async def _loop(self):
        while True:
            try:
                self.check_battery()
                await self.check_meetings()
            except Exception:
                pass
            await asyncio.sleep(60)

    async def start(self):
        self._task = asyncio.create_task(self._loop())

    async def stop(self):
        if self._task:
            self._task.cancel()
