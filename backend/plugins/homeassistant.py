from fastapi import APIRouter

from ..core.plugins import Plugin, tool

CONTROLLABLE = ("light", "switch", "fan", "climate", "scene", "script", "cover", "media_player", "lock")


class HomeAssistantPlugin(Plugin):
    name, title, category, icon = "homeassistant", "Smart home", "home", "house"
    description = "Controls lights, scenes, thermostats and plugs through Home Assistant."
    settings_schema = {
        "url": {"label": "Home Assistant URL", "type": "string", "env": "HOME_ASSISTANT_URL"},
        "token": {"label": "Long-lived access token", "type": "string", "secret": True, "env": "HOME_ASSISTANT_TOKEN"},
    }
    requires = ("url", "token")

    async def _req(self, method: str, path: str, json=None):
        r = await self.ctx.http.request(method, str(self.setting("url")).rstrip("/") + "/api" + path, json=json,
                                        headers={"Authorization": f"Bearer {self.setting('token')}"})
        r.raise_for_status()
        return r.json() if r.content else {}

    @tool("List smart home devices and their state.", {"domain": {"type": "string",
                                                                  "description": "Optional: light, switch, climate…"}},
          required=[])
    async def devices(self, domain: str = ""):
        states = await self._req("GET", "/states")
        out = []
        for s in states:
            dom = s["entity_id"].split(".")[0]
            if dom in CONTROLLABLE and (not domain or dom == domain):
                a = s.get("attributes", {})
                out.append({"entity_id": s["entity_id"], "name": a.get("friendly_name", s["entity_id"]),
                            "domain": dom, "state": s["state"], "area": a.get("area_id"),
                            "brightness": a.get("brightness"), "temperature": a.get("temperature"),
                            "current_temperature": a.get("current_temperature")})
        return out

    async def resolve(self, target: str) -> str:
        if "." in target and " " not in target:
            return target
        for d in await self.devices():
            if target.lower() in d["name"].lower():
                return d["entity_id"]
        raise ValueError(f"No device matching '{target}'")

    @tool("Turn a device on or off (lights, switches, plugs, fans).", {
        "target": {"type": "string", "description": "entity_id or friendly name"}, "on": {"type": "boolean"},
        "brightness": {"type": "integer", "description": "0-100, lights only"},
        "color": {"type": "string", "description": "Colour name, lights only"}}, required=["target", "on"])
    async def switch(self, target: str, on: bool, brightness: int | None = None, color: str | None = None):
        eid = await self.resolve(target)
        domain = eid.split(".")[0]
        data = {"entity_id": eid}
        if on and domain == "light":
            if brightness is not None:
                data["brightness_pct"] = int(brightness)
            if color:
                data["color_name"] = color
        await self._req("POST", f"/services/{'homeassistant' if domain not in ('light',) else domain}/"
                                f"turn_{'on' if on else 'off'}", data)
        return {"entity_id": eid, "on": on}

    @tool("Activate a scene.", {"scene": {"type": "string"}})
    async def scene(self, scene: str):
        eid = await self.resolve(scene if scene.startswith("scene.") else scene)
        await self._req("POST", "/services/scene/turn_on", {"entity_id": eid})
        return {"activated": eid}

    @tool("Set a thermostat temperature.", {"target": {"type": "string"}, "temperature": {"type": "number"}})
    async def thermostat(self, target: str, temperature: float):
        eid = await self.resolve(target)
        await self._req("POST", "/services/climate/set_temperature", {"entity_id": eid, "temperature": temperature})
        return {"entity_id": eid, "temperature": temperature}

    def router(self):
        r = APIRouter()

        @r.get("/devices")
        async def devices():
            try:
                return await self.devices()
            except Exception as e:
                return {"error": str(e)}
        return r
