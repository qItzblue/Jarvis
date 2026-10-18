import asyncio

from ..core.plugins import Plugin, tool

DEFAULT_FEEDS = "https://feeds.bbci.co.uk/news/rss.xml, https://www.theverge.com/rss/index.xml"


class NewsPlugin(Plugin):
    name, title, category, icon = "news", "News", "info", "newspaper"
    description = "Headlines from RSS feeds you choose."
    optional_deps = ("feedparser",)
    settings_schema = {"feeds": {"label": "RSS feed URLs (comma separated)", "type": "text",
                                 "default": DEFAULT_FEEDS}}

    def parse(self, raw: bytes, source: str, limit: int) -> list[dict]:
        import feedparser
        feed = feedparser.parse(raw)
        name = feed.feed.get("title", source)
        return [{"title": e.get("title"), "link": e.get("link"), "source": name,
                 "published": e.get("published", ""), "summary": (e.get("summary") or "")[:300]}
                for e in feed.entries[:limit]]

    @tool("Get the latest news headlines.", {"limit": {"type": "integer"},
                                             "topic": {"type": "string", "description": "Optional keyword filter"}},
          required=[])
    async def headlines(self, limit: int = 8, topic: str = ""):
        urls = [u.strip() for u in str(self.setting("feeds")).split(",") if u.strip()]

        async def one(url):
            try:
                r = await self.ctx.http.get(url)
                return self.parse(r.content, url, 30)
            except Exception:
                return []
        items = [i for group in await asyncio.gather(*(one(u) for u in urls)) for i in group]
        if topic:
            items = [i for i in items if topic.lower() in f"{i['title']} {i['summary']}".lower()]
        # interleave sources so one feed doesn't dominate
        by_src: dict[str, list] = {}
        for i in items:
            by_src.setdefault(i["source"], []).append(i)
        mixed = [x for tup in zip(*by_src.values()) for x in tup] if len(by_src) > 1 else items
        return (mixed or items)[:int(limit)]

    def router(self):
        from fastapi import APIRouter
        r = APIRouter()
        r.get("")(self.headlines)
        return r
