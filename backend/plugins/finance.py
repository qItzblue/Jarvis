from ..core.plugins import Plugin, tool


class FinancePlugin(Plugin):
    name, title, category, icon = "finance", "Stocks & crypto", "info", "trending-up"
    description = "Stock quotes (Yahoo Finance) and crypto prices (CoinGecko), no key needed."
    settings_schema = {"watchlist": {"label": "Watchlist (comma separated)", "type": "string",
                                     "default": "AAPL,MSFT,NVDA,bitcoin,ethereum"},
                       "currency": {"label": "Crypto currency", "type": "string", "default": "usd"}}

    @tool("Get a stock quote by ticker symbol.", {"symbol": {"type": "string"}})
    async def stock(self, symbol: str):
        r = await self.ctx.http.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol.upper()}",
                                    params={"range": "5d", "interval": "1d"})
        r.raise_for_status()
        res = r.json()["chart"]["result"][0]
        meta = res["meta"]
        price, prev = meta["regularMarketPrice"], meta.get("chartPreviousClose") or meta.get("previousClose")
        closes = [c for c in res["indicators"]["quote"][0]["close"] if c is not None]
        return {"symbol": meta["symbol"], "price": price, "currency": meta.get("currency"),
                "change_percent": round((price - prev) / prev * 100, 2) if prev else None, "history": closes}

    @tool("Get cryptocurrency prices by CoinGecko id (e.g. bitcoin, ethereum, solana).",
          {"ids": {"type": "string", "description": "Comma-separated ids"}})
    async def crypto(self, ids: str):
        cur = self.setting("currency")
        r = await self.ctx.http.get("https://api.coingecko.com/api/v3/simple/price", params={
            "ids": ids.lower().replace(" ", ""), "vs_currencies": cur, "include_24hr_change": "true"})
        r.raise_for_status()
        return [{"id": k, "price": v.get(cur), "currency": cur,
                 "change_percent": round(v.get(f"{cur}_24h_change") or 0, 2)} for k, v in r.json().items()]

    @tool("Get prices for everything on the watchlist.", {})
    async def watchlist(self):
        items = [s.strip() for s in str(self.setting("watchlist")).split(",") if s.strip()]
        stocks = [s for s in items if s.isupper()]
        coins = [s for s in items if not s.isupper()]
        out = []
        for s in stocks:
            try:
                out.append(await self.stock(s))
            except Exception as e:
                out.append({"symbol": s, "error": str(e)})
        if coins:
            try:
                out += await self.crypto(",".join(coins))
            except Exception as e:
                out.append({"id": ",".join(coins), "error": str(e)})
        return out

    def router(self):
        from fastapi import APIRouter
        r = APIRouter()
        r.get("/watchlist")(self.watchlist)
        return r
