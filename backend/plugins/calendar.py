import asyncio
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter

from ..core import google_auth
from ..core.plugins import Plugin, tool


class CalendarPlugin(Plugin):
    name, title, category, icon = "calendar", "Google Calendar", "productivity", "calendar"
    description = "Reads and creates events in your Google Calendar."
    optional_deps = ("googleapiclient", "google_auth_oauthlib")
    settings_schema = {"client_file": {"label": "Google OAuth client JSON path", "type": "string",
                                       "env": "GOOGLE_OAUTH_CLIENT_FILE"},
                       "calendar_id": {"label": "Calendar ID", "type": "string", "default": "primary"}}
    requires = ("client_file",)

    def _events(self, start: datetime, end: datetime, limit: int) -> list[dict]:
        svc = google_auth.service("calendar", "v3")
        res = svc.events().list(calendarId=self.setting("calendar_id"), timeMin=start.isoformat(),
                                timeMax=end.isoformat(), singleEvents=True, orderBy="startTime",
                                maxResults=limit).execute()
        return [{"id": e["id"], "summary": e.get("summary", "(no title)"), "location": e.get("location"),
                 "start": e["start"].get("dateTime", e["start"].get("date")),
                 "end": e["end"].get("dateTime", e["end"].get("date"))} for e in res.get("items", [])]

    @tool("List calendar events in the coming days.", {"days": {"type": "integer"}}, required=[])
    async def upcoming(self, days: int = 1, limit: int = 20):
        now = datetime.now(timezone.utc)
        return await asyncio.to_thread(self._events, now, now + timedelta(days=int(days)), limit)

    @tool("Create a calendar event.", {
        "title": {"type": "string"}, "start": {"type": "string", "description": "ISO local datetime"},
        "minutes": {"type": "integer", "description": "Duration"}, "location": {"type": "string"}},
        required=["title", "start"], confirm=True)
    async def create_event(self, title: str, start: str, minutes: int = 60, location: str = ""):
        st = datetime.fromisoformat(start).astimezone()
        body = {"summary": title, "location": location, "start": {"dateTime": st.isoformat()},
                "end": {"dateTime": (st + timedelta(minutes=int(minutes))).isoformat()}}
        svc = google_auth.service("calendar", "v3")
        ev = await asyncio.to_thread(lambda: svc.events().insert(
            calendarId=self.setting("calendar_id"), body=body).execute())
        return {"created": ev.get("id"), "link": ev.get("htmlLink")}

    def router(self):
        r = APIRouter()

        @r.post("/connect")
        async def connect():
            return await google_auth.connect(self.setting("client_file"))

        @r.get("/events")
        async def events(days: int = 7):
            try:
                return await self.upcoming(days, 100)
            except Exception as e:
                return {"error": str(e)}
        return r
