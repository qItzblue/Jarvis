from ..core.plugins import Plugin, tool


class CommutePlugin(Plugin):
    name, title, category, icon = "commute", "Commute & travel time", "info", "car"
    description = "Live travel times with Google Maps (uses your Google API key if the Routes API is enabled)."
    settings_schema = {
        "api_key": {"label": "Google Maps API key", "type": "string", "secret": True, "env": "GOOGLE_MAPS_API_KEY",
                    "fallback": "google.api_key"},
        "home": {"label": "Home address", "type": "string"},
        "work": {"label": "Work address", "type": "string"},
        "mode": {"label": "Travel mode", "type": "select", "options": ["driving", "transit", "walking", "bicycling"],
                 "default": "driving"},
    }
    requires = ("api_key",)

    @tool("Get travel time between two places.", {"origin": {"type": "string"}, "destination": {"type": "string"},
                                                   "mode": {"type": "string"}}, required=["origin", "destination"])
    async def travel_time(self, origin: str, destination: str, mode: str = ""):
        r = await self.ctx.http.get("https://maps.googleapis.com/maps/api/distancematrix/json", params={
            "origins": origin, "destinations": destination, "mode": mode or self.setting("mode"),
            "departure_time": "now", "key": self.setting("api_key")})
        r.raise_for_status()
        d = r.json()
        if d.get("status") != "OK":
            return {"error": d.get("error_message") or d.get("status")}
        el = d["rows"][0]["elements"][0]
        if el.get("status") != "OK":
            return {"error": el.get("status")}
        dur = el.get("duration_in_traffic") or el["duration"]
        return {"from": d["origin_addresses"][0], "to": d["destination_addresses"][0],
                "distance": el["distance"]["text"], "duration": dur["text"], "minutes": round(dur["value"] / 60)}

    @tool("Get the current commute time from home to work.", {})
    async def to_work(self):
        if not (self.setting("home") and self.setting("work")):
            return {"error": "Set home and work addresses in the Commute plugin settings."}
        return await self.travel_time(self.setting("home"), self.setting("work"))
