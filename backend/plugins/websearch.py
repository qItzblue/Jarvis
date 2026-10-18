import html
import re
from urllib.parse import parse_qs, unquote, urlparse

from ..core.plugins import Plugin, tool

_RESULT = re.compile(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>.*?'
                     r'class="result__snippet"[^>]*>(.*?)</(?:a|td|div)>', re.S)
_TAGS = re.compile(r"<[^>]+>")


def _clean(s: str) -> str:
    return html.unescape(_TAGS.sub("", s)).strip()


def _real_url(href: str) -> str:
    if "uddg=" in href:
        return unquote(parse_qs(urlparse(href).query).get("uddg", [href])[0])
    return href if href.startswith("http") else "https:" + href


class WebSearchPlugin(Plugin):
    name, title, category, icon = "websearch", "Web search", "info", "search"
    description = "Searches the web (DuckDuckGo, no key needed) and reads pages."

    def parse(self, page: str, limit: int) -> list[dict]:
        return [{"title": _clean(t), "url": _real_url(h), "snippet": _clean(sn)}
                for h, t, sn in _RESULT.findall(page)[:limit]]

    @tool("Search the web and return the top results.", {"query": {"type": "string"},
                                                          "limit": {"type": "integer"}}, required=["query"])
    async def search(self, query: str, limit: int = 6):
        r = await self.ctx.http.post("https://html.duckduckgo.com/html/", data={"q": query})
        r.raise_for_status()
        return self.parse(r.text, int(limit))

    @tool("Fetch a web page and return its readable text.", {"url": {"type": "string"}})
    async def read_page(self, url: str):
        r = await self.ctx.http.get(url)
        r.raise_for_status()
        text = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", r.text, flags=re.S | re.I)
        text = re.sub(r"\s+", " ", _clean(text))
        return {"url": url, "text": text[:8000]}
