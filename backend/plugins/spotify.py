import base64
import time

from ..core.plugins import Plugin, tool

API = "https://api.spotify.com/v1"


class SpotifyPlugin(Plugin):
    name, title, category, icon = "spotify", "Spotify", "computer", "music"
    description = "Plays, pauses and searches music on your Spotify devices (Premium needed for playback)."
    settings_schema = {
        "client_id": {"label": "Client ID", "type": "string", "env": "SPOTIFY_CLIENT_ID"},
        "client_secret": {"label": "Client secret", "type": "string", "secret": True, "env": "SPOTIFY_CLIENT_SECRET"},
        "refresh_token": {"label": "Refresh token", "type": "string", "secret": True, "env": "SPOTIFY_REFRESH_TOKEN"},
    }
    requires = ("client_id", "client_secret", "refresh_token")

    def __init__(self, ctx):
        super().__init__(ctx)
        self._token, self._expires = None, 0.0

    async def token(self) -> str:
        if self._token and time.time() < self._expires - 60:
            return self._token
        auth = base64.b64encode(f"{self.setting('client_id')}:{self.setting('client_secret')}".encode()).decode()
        r = await self.ctx.http.post("https://accounts.spotify.com/api/token",
                                     data={"grant_type": "refresh_token", "refresh_token": self.setting("refresh_token")},
                                     headers={"Authorization": f"Basic {auth}"})
        r.raise_for_status()
        d = r.json()
        self._token, self._expires = d["access_token"], time.time() + d.get("expires_in", 3600)
        return self._token

    async def _api(self, method: str, path: str, **kw):
        r = await self.ctx.http.request(method, API + path, headers={"Authorization": f"Bearer {await self.token()}"}, **kw)
        if r.status_code == 204 or not r.content:
            return {"ok": r.status_code < 300}
        return r.json()

    @tool("Play music: a search query (song, artist, album or playlist), or resume if empty.",
          {"query": {"type": "string"}, "kind": {"type": "string", "enum": ["track", "artist", "album", "playlist"]}},
          required=[])
    async def play(self, query: str = "", kind: str = "track"):
        if not query:
            return await self._api("PUT", "/me/player/play")
        res = await self._api("GET", "/search", params={"q": query, "type": kind, "limit": 1})
        items = res.get(f"{kind}s", {}).get("items", [])
        if not items:
            return {"error": f"Nothing found for '{query}'"}
        item = items[0]
        body = {"uris": [item["uri"]]} if kind == "track" else {"context_uri": item["uri"]}
        await self._api("PUT", "/me/player/play", json=body)
        return {"playing": item["name"]}

    @tool("Pause Spotify.", {})
    async def pause(self):
        return await self._api("PUT", "/me/player/pause")

    @tool("Skip to the next track.", {})
    async def next_track(self):
        return await self._api("POST", "/me/player/next")

    @tool("What's playing on Spotify right now.", {})
    async def now_playing(self):
        d = await self._api("GET", "/me/player/currently-playing")
        item = d.get("item") if isinstance(d, dict) else None
        if not item:
            return {"playing": False}
        return {"playing": d.get("is_playing"), "track": item["name"],
                "artists": ", ".join(a["name"] for a in item["artists"]), "album": item["album"]["name"]}
