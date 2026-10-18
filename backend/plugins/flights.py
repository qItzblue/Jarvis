from ..core.plugins import Plugin, tool


class FlightsPlugin(Plugin):
    name, title, category, icon = "flights", "Flight status", "info", "plane"
    description = "Live flight status via AviationStack (free tier key)."
    settings_schema = {"api_key": {"label": "AviationStack API key", "type": "string", "secret": True,
                                   "env": "AVIATIONSTACK_API_KEY"}}
    requires = ("api_key",)

    @tool("Get the status of a flight by IATA flight number, e.g. BA117.", {"flight": {"type": "string"}})
    async def flight_status(self, flight: str):
        r = await self.ctx.http.get("http://api.aviationstack.com/v1/flights", params={
            "access_key": self.setting("api_key"), "flight_iata": flight.replace(" ", "").upper(), "limit": 1})
        r.raise_for_status()
        data = r.json().get("data") or []
        if not data:
            return {"error": f"No data for flight {flight}"}
        f = data[0]
        return {"flight": f["flight"].get("iata"), "airline": f["airline"].get("name"),
                "status": f.get("flight_status"),
                "departure": {k: f["departure"].get(k) for k in ("airport", "scheduled", "estimated", "gate", "delay")},
                "arrival": {k: f["arrival"].get(k) for k in ("airport", "scheduled", "estimated", "gate", "delay")}}
