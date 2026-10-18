from urllib.parse import quote

from ..core.plugins import Plugin, tool


class WikipediaPlugin(Plugin):
    name, title, category, icon = "wikipedia", "Wikipedia", "info", "book-open"
    description = "Looks up encyclopedia summaries."
    settings_schema = {"language": {"label": "Wikipedia language code", "type": "string", "default": "en"}}

    @tool("Get a Wikipedia summary for a topic.", {"topic": {"type": "string"}})
    async def lookup(self, topic: str):
        lang = self.setting("language")
        s = await self.ctx.http.get(f"https://{lang}.wikipedia.org/w/api.php", params={
            "action": "opensearch", "search": topic, "limit": 1, "format": "json"})
        s.raise_for_status()
        titles = s.json()[1]
        if not titles:
            return {"error": f"No article found for '{topic}'"}
        r = await self.ctx.http.get(f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{quote(titles[0])}")
        r.raise_for_status()
        d = r.json()
        return {"title": d.get("title"), "summary": d.get("extract"),
                "url": d.get("content_urls", {}).get("desktop", {}).get("page")}
