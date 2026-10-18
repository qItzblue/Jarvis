from ..core.plugins import Plugin, tool


class BriefingPlugin(Plugin):
    name, title, category, icon = "briefing", "Morning briefing", "productivity", "sunrise"
    description = "Collects weather, calendar, tasks, news and commute into one briefing."
    settings_schema = {"news_items": {"label": "Headlines to include", "type": "number", "default": 5}}

    async def _try(self, tool: str, args: dict | None = None):
        reg = self.ctx.registry
        if not reg.find_tool(tool):
            return None
        res = await reg.call(tool, args or {}, source="briefing")
        return None if isinstance(res, dict) and "error" in res else res

    @tool("Get the morning briefing: weather, calendar, tasks, reminders, news and commute.", {})
    async def morning(self):
        news = await self._try("news__headlines", {"limit": int(self.setting("news_items"))})
        return {"weather": await self._try("weather__forecast", {"days": 1}),
                "calendar": await self._try("calendar__upcoming", {"days": 1}),
                "tasks": await self._try("todo__list"),
                "reminders": await self._try("timers__list_reminders"),
                "news": news,
                "commute": await self._try("commute__to_work")}

    def router(self):
        from fastapi import APIRouter
        r = APIRouter()
        r.get("")(self.morning)
        return r
