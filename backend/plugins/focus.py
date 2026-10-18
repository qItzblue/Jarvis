import asyncio
import time

from ..core.plugins import Plugin, tool


class FocusPlugin(Plugin):
    name, title, category, icon = "focus", "Focus / Pomodoro", "productivity", "target"
    description = "Pomodoro sessions with work/break cycles and announcements."
    settings_schema = {"work_minutes": {"label": "Work minutes", "type": "number", "default": 25},
                       "break_minutes": {"label": "Break minutes", "type": "number", "default": 5}}

    def __init__(self, ctx):
        super().__init__(ctx)
        self.session: dict | None = None
        self._task: asyncio.Task | None = None

    def _publish(self):
        self.ctx.bus.publish({"type": "focus", "session": self.session})

    async def _cycle(self, rounds: int):
        work, rest = float(self.setting("work_minutes")) * 60, float(self.setting("break_minutes")) * 60
        for i in range(rounds):
            for phase, secs in (("work", work), ("break", rest)):
                if phase == "break" and i == rounds - 1:
                    break
                self.session = {"phase": phase, "round": i + 1, "rounds": rounds, "ends_at": time.time() + secs}
                self._publish()
                await asyncio.sleep(secs)
                self.ctx.bus.alert("🎯 Focus" if phase == "break" else "☕ Break time",
                                   f"Round {i + 1}/{rounds} {phase} finished", "alarm")
        self.session = None
        self._publish()

    @tool("Start a Pomodoro focus session.", {"rounds": {"type": "integer"}}, required=[])
    async def start_focus(self, rounds: int = 4):
        await self.stop_focus()
        self._task = asyncio.create_task(self._cycle(int(rounds)))
        await asyncio.sleep(0)
        return {"started": True, "rounds": int(rounds), "work_minutes": self.setting("work_minutes")}

    @tool("Stop the current focus session.", {})
    async def stop_focus(self):
        running = self._task is not None and not self._task.done()
        if running:
            self._task.cancel()
        self.session = None
        self._publish()
        return {"stopped": running}

    @tool("Get the focus session status.", {})
    async def focus_status(self):
        if not self.session:
            return {"active": False}
        return {"active": True, **self.session, "remaining": int(self.session["ends_at"] - time.time())}

    async def stop(self):
        if self._task:
            self._task.cancel()
