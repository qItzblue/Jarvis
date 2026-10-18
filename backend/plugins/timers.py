import asyncio
import time
from datetime import datetime, timedelta

from fastapi import APIRouter

from .. import db
from ..db import Reminder, row_dict
from ..core.plugins import Plugin, tool


class TimersPlugin(Plugin):
    name, title, category, icon = "timers", "Timers & reminders", "productivity", "timer"
    description = "Countdown timers and dated reminders, announced when due."

    def __init__(self, ctx):
        super().__init__(ctx)
        self.timers: dict[int, dict] = {}
        self._next = 1
        self._loop: asyncio.Task | None = None

    @tool("Start a countdown timer.", {"seconds": {"type": "integer"}, "label": {"type": "string"}},
          required=["seconds"])
    async def start_timer(self, seconds: int, label: str = "Timer"):
        tid, self._next = self._next, self._next + 1
        ends = time.time() + int(seconds)
        task = asyncio.create_task(self._ring(tid, int(seconds)))
        self.timers[tid] = {"id": tid, "label": label, "ends_at": ends, "task": task}
        self._publish()
        return {"id": tid, "label": label, "seconds": int(seconds)}

    async def _ring(self, tid: int, seconds: int):
        await asyncio.sleep(seconds)
        t = self.timers.pop(tid, None)
        if t:
            self.ctx.bus.alert(f"⏰ {t['label']} finished", "", "alarm")
            self._publish()

    @tool("List running timers.", {})
    async def list_timers(self):
        now = time.time()
        return [{"id": t["id"], "label": t["label"], "remaining": int(t["ends_at"] - now)}
                for t in self.timers.values()]

    @tool("Cancel a timer by id.", {"id": {"type": "integer"}})
    async def cancel_timer(self, id: int):
        t = self.timers.pop(int(id), None)
        if t:
            t["task"].cancel()
            self._publish()
        return {"cancelled": t is not None}

    def _publish(self):
        self.ctx.bus.publish({"type": "timers", "timers": [
            {"id": t["id"], "label": t["label"], "ends_at": t["ends_at"]} for t in self.timers.values()]})

    @tool("Create a reminder at a specific local date/time.", {
        "text": {"type": "string"},
        "when": {"type": "string", "description": "ISO 8601 local datetime, e.g. 2026-05-01T09:00"}})
    async def add_reminder(self, text: str, when: str):
        due = datetime.fromisoformat(when.replace("Z", ""))
        with db.session() as s:
            r = Reminder(text=text, due_at=due)
            s.add(r)
            s.flush()
            return row_dict(r)

    @tool("Create a reminder a number of minutes from now.", {"text": {"type": "string"},
                                                                "minutes": {"type": "integer"}})
    async def remind_in(self, text: str, minutes: int):
        return await self.add_reminder(text, (datetime.now() + timedelta(minutes=int(minutes))).isoformat())

    @tool("List upcoming reminders.", {})
    async def list_reminders(self):
        with db.session() as s:
            return [row_dict(r) for r in s.query(Reminder).filter_by(fired=False).order_by(Reminder.due_at)]

    @tool("Delete a reminder by id.", {"id": {"type": "integer"}})
    async def delete_reminder(self, id: int):
        with db.session() as s:
            return {"deleted": s.query(Reminder).filter_by(id=int(id)).delete() > 0}

    def check_due(self) -> list[dict]:
        fired = []
        with db.session() as s:
            for r in s.query(Reminder).filter(Reminder.fired.is_(False), Reminder.due_at <= datetime.now()):
                r.fired = True
                fired.append(row_dict(r))
        for r in fired:
            self.ctx.bus.alert("🔔 Reminder", r["text"], "alarm")
        return fired

    async def _watch(self):
        while True:
            self.check_due()
            await asyncio.sleep(15)

    async def start(self):
        self._loop = asyncio.create_task(self._watch())

    async def stop(self):
        if self._loop:
            self._loop.cancel()
        for t in self.timers.values():
            t["task"].cancel()

    def router(self):
        r = APIRouter()
        r.get("/timers")(self.list_timers)
        r.get("/reminders")(self.list_reminders)
        r.delete("/reminders/{id}")(self.delete_reminder)
        r.delete("/timers/{id}")(self.cancel_timer)
        return r
