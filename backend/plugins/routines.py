import asyncio
import re

from fastapi import APIRouter
from pydantic import BaseModel

from .. import db
from ..db import Routine, row_dict
from ..core.plugins import Plugin, tool

DEFAULTS = [
    {"name": "Good morning", "phrase": "good morning",
     "steps": [{"say": "Good morning. Here's your briefing."}, {"tool": "briefing__morning", "args": {}}]},
    {"name": "Good night", "phrase": "good night",
     "steps": [{"tool": "homeassistant__scene", "args": {"scene": "good night"}},
               {"tool": "media__set_volume", "args": {"level": 10}}, {"say": "Good night. Sleep well."}]},
]


class RoutineBody(BaseModel):
    name: str
    phrase: str
    steps: list[dict]
    enabled: bool = True


def normalise(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()


class RoutinesPlugin(Plugin):
    name, title, category, icon = "routines", "Routines", "automation", "workflow"
    description = "Chains several actions under one phrase, like 'good night'."

    async def start(self):
        with db.session() as s:
            if s.query(Routine).count() == 0:
                for d in DEFAULTS:
                    s.add(Routine(**d))

    def match(self, text: str):
        t = normalise(text)
        t = re.sub(r"^(hey |ok )?(jarvis )?", "", t).strip()
        with db.session() as s:
            for r in s.query(Routine).filter_by(enabled=True):
                if normalise(r.phrase) == t:
                    return row_dict(r)
        return None

    async def run(self, routine: dict, emit=None) -> str:
        """Run steps in order. Steps are {"tool": name, "args": {...}}, {"say": text} or {"wait": seconds}."""
        said, results = [], []
        for step in routine["steps"]:
            if "say" in step:
                said.append(step["say"])
            elif "wait" in step:
                await asyncio.sleep(float(step["wait"]))
            elif "tool" in step:
                if emit:
                    await emit({"type": "tool", "name": step["tool"], "args": step.get("args", {}), "status": "running"})
                res = await self.ctx.registry.call(step["tool"], step.get("args", {}), source="routine")
                ok = not (isinstance(res, dict) and "error" in res)
                results.append({"tool": step["tool"], "ok": ok})
                if emit:
                    await emit({"type": "tool", "name": step["tool"], "status": "done", "ok": ok, "result": res})
        failed = [r["tool"] for r in results if not r["ok"]]
        text = " ".join(said) or f"Routine '{routine['name']}' complete."
        if failed:
            text += f" ({len(failed)} step(s) could not run: {', '.join(failed)}.)"
        return text

    @tool("List the user's routines.", {})
    async def list_routines(self):
        with db.session() as s:
            return [row_dict(r) for r in s.query(Routine)]

    @tool("Run a routine by name.", {"name": {"type": "string"}})
    async def run_routine(self, name: str):
        with db.session() as s:
            r = s.query(Routine).filter(Routine.name.ilike(name)).first()
            r = row_dict(r) if r else None
        if not r:
            return {"error": f"No routine called '{name}'"}
        return {"result": await self.run(r)}

    def router(self):
        rt = APIRouter()
        rt.get("")(self.list_routines)

        @rt.post("")
        async def create(b: RoutineBody):
            with db.session() as s:
                r = Routine(**b.model_dump())
                s.add(r)
                s.flush()
                return row_dict(r)

        @rt.put("/{rid}")
        async def update(rid: int, b: RoutineBody):
            with db.session() as s:
                r = s.get(Routine, rid)
                for k, v in b.model_dump().items():
                    setattr(r, k, v)
                return row_dict(r)

        @rt.delete("/{rid}")
        async def delete(rid: int):
            with db.session() as s:
                s.query(Routine).filter_by(id=rid).delete()
            return {"ok": True}

        @rt.post("/{rid}/run")
        async def run(rid: int):
            with db.session() as s:
                r = row_dict(s.get(Routine, rid))
            return {"result": await self.run(r)}
        return rt
