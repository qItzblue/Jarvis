from ..core.plugins import Plugin, tool

LEAGUES = {"nfl": "football/nfl", "nba": "basketball/nba", "mlb": "baseball/mlb", "nhl": "hockey/nhl",
           "premier league": "soccer/eng.1", "epl": "soccer/eng.1", "la liga": "soccer/esp.1",
           "bundesliga": "soccer/ger.1", "serie a": "soccer/ita.1", "champions league": "soccer/uefa.champions",
           "mls": "soccer/usa.1", "f1": "racing/f1"}


class SportsPlugin(Plugin):
    name, title, category, icon = "sports", "Sports scores", "info", "trophy"
    description = "Live and recent scores from ESPN's public scoreboards."
    settings_schema = {"favorites": {"label": "Favourite leagues", "type": "string", "default": "premier league,nba"}}

    @tool("Get today's scores for a league.", {
        "league": {"type": "string", "description": "e.g. " + ", ".join(LEAGUES)},
        "team": {"type": "string", "description": "Optional team filter"}}, required=["league"])
    async def scores(self, league: str, team: str = ""):
        path = LEAGUES.get(league.lower().strip())
        if not path:
            return {"error": f"Unknown league. Try one of: {', '.join(LEAGUES)}"}
        r = await self.ctx.http.get(f"https://site.api.espn.com/apis/site/v2/sports/{path}/scoreboard")
        r.raise_for_status()
        games = []
        for ev in r.json().get("events", []):
            comp = ev["competitions"][0]
            teams = [{"team": c["team"]["displayName"], "score": c.get("score"), "home": c.get("homeAway") == "home"}
                     for c in comp.get("competitors", [])]
            games.append({"name": ev.get("name"), "status": ev["status"]["type"]["description"],
                          "detail": ev["status"]["type"].get("shortDetail"), "teams": teams})
        if team:
            games = [g for g in games if team.lower() in (g["name"] or "").lower()]
        return games
