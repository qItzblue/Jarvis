import asyncio
import logging

from ..core.plugins import Plugin

log = logging.getLogger("jarvis.telegram")


class TelegramPlugin(Plugin):
    name, title, category, icon = "telegram", "Telegram remote", "remote", "send"
    description = ("Talk to Jarvis from your phone via a Telegram bot. Only your user ID is accepted; "
                   "risky actions still need approval on the desktop.")
    settings_schema = {
        "bot_token": {"label": "Bot token (from @BotFather)", "type": "string", "secret": True, "env": "TELEGRAM_BOT_TOKEN"},
        "allowed_user_id": {"label": "Your Telegram user ID", "type": "string", "env": "TELEGRAM_ALLOWED_USER_ID"},
        "forward_alerts": {"label": "Send alerts to Telegram", "type": "boolean", "default": True},
    }
    requires = ("bot_token", "allowed_user_id")

    def __init__(self, ctx):
        super().__init__(ctx)
        self._tasks: list[asyncio.Task] = []
        self.conversation_id: int | None = None

    @property
    def api(self) -> str:
        return f"https://api.telegram.org/bot{self.setting('bot_token')}"

    async def send(self, text: str):
        await self.ctx.http.post(f"{self.api}/sendMessage", json={
            "chat_id": int(self.setting("allowed_user_id")), "text": text[:4000]})

    def authorised(self, update: dict) -> bool:
        sender = (update.get("message") or {}).get("from", {}).get("id")
        return str(sender) == str(self.setting("allowed_user_id")).strip()

    async def handle_update(self, update: dict) -> str | None:
        if not self.authorised(update):
            return None
        text = (update.get("message") or {}).get("text", "").strip()
        if not text:
            return None
        if text == "/new":
            self.conversation_id = None
            await self.send("Started a new conversation.")
            return ""

        async def emit(ev):
            if ev["type"] == "start":
                self.conversation_id = ev["conversation_id"]
            elif ev["type"] == "confirm_request":
                await self.send(f"⚠️ Approval needed on the desktop: {ev['title']}")
            elif ev["type"] == "error":
                await self.send(f"Error: {ev['message']}")
        reply = await self.ctx.extra["assistant"].handle(text, emit, self.conversation_id, source="telegram")
        if reply:
            await self.send(reply)
        return reply

    async def _poll(self):
        offset = 0
        while True:
            try:
                r = await self.ctx.http.get(f"{self.api}/getUpdates", params={"timeout": 30, "offset": offset},
                                            timeout=40)
                for upd in r.json().get("result", []):
                    offset = upd["update_id"] + 1
                    asyncio.create_task(self.handle_update(upd))
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("telegram poll failed")
                await asyncio.sleep(10)

    async def _forward_alerts(self):
        q = self.ctx.bus.subscribe()
        try:
            while True:
                ev = await q.get()
                if ev.get("type") == "alert" and self.setting("forward_alerts"):
                    await self.send(f"{ev['title']}\n{ev.get('body', '')}".strip())
                elif ev.get("type") == "confirm_request":
                    await self.send(f"⚠️ Jarvis is waiting for approval on the desktop: {ev['title']}")
        finally:
            self.ctx.bus.unsubscribe(q)

    async def start(self):
        self._tasks = [asyncio.create_task(self._poll()), asyncio.create_task(self._forward_alerts())]

    async def stop(self):
        for t in self._tasks:
            t.cancel()
