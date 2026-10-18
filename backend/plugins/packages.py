from ..core.plugins import Plugin, tool

STATUS = {0: "not found", 10: "in transit", 20: "expired", 30: "ready for pickup", 35: "undelivered",
          40: "delivered", 50: "alert"}


class PackagesPlugin(Plugin):
    name, title, category, icon = "packages", "Package tracking", "info", "package"
    description = "Tracks parcels across carriers with 17TRACK (free tier needs an API key)."
    settings_schema = {"api_key": {"label": "17TRACK API key", "type": "string", "secret": True,
                                   "env": "TRACK17_API_KEY"}}
    requires = ("api_key",)
    BASE = "https://api.17track.net/track/v2.2"

    @tool("Track a parcel by tracking number.", {"number": {"type": "string"}})
    async def track(self, number: str):
        h = {"17token": self.setting("api_key")}
        await self.ctx.http.post(f"{self.BASE}/register", json=[{"number": number}], headers=h)
        r = await self.ctx.http.post(f"{self.BASE}/gettrackinfo", json=[{"number": number}], headers=h)
        r.raise_for_status()
        accepted = r.json().get("data", {}).get("accepted", [])
        if not accepted:
            return {"number": number, "status": "pending – try again in a minute"}
        info = accepted[0].get("track_info", {})
        latest = info.get("latest_event") or {}
        return {"number": number, "status": info.get("latest_status", {}).get("status"),
                "last_event": latest.get("description"), "location": latest.get("location"),
                "time": latest.get("time_iso")}
