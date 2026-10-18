import asyncio

from .. import db
from ..db import ClipboardItem, row_dict
from ..core.plugins import Plugin, tool


class ClipboardPlugin(Plugin):
    name, title, category, icon = "clipboard", "Clipboard history", "productivity", "clipboard"
    description = "Keeps a local history of copied text and can paste old items back."
    optional_deps = ("pyperclip",)
    default_enabled = False  # opt-in: it records everything you copy
    settings_schema = {"max_items": {"label": "Items to keep", "type": "number", "default": 200}}

    def __init__(self, ctx):
        super().__init__(ctx)
        self._task = None
        self._last = None

    def record(self, text: str) -> bool:
        if not text or text == self._last:
            return False
        self._last = text
        with db.session() as s:
            s.add(ClipboardItem(text=text[:10000]))
            keep = int(self.setting("max_items"))
            old = s.query(ClipboardItem.id).order_by(ClipboardItem.id.desc()).offset(keep).all()
            if old:
                s.query(ClipboardItem).filter(ClipboardItem.id.in_([o[0] for o in old])).delete()
        return True

    async def _poll(self):
        import pyperclip
        while True:
            try:
                self.record(await asyncio.to_thread(pyperclip.paste))
            except Exception:
                pass
            await asyncio.sleep(1.5)

    async def start(self):
        self._task = asyncio.create_task(self._poll())

    async def stop(self):
        if self._task:
            self._task.cancel()

    @tool("Show recent clipboard history.", {"limit": {"type": "integer"}}, required=[])
    async def history(self, limit: int = 10):
        with db.session() as s:
            return [row_dict(c) for c in s.query(ClipboardItem).order_by(ClipboardItem.id.desc()).limit(int(limit))]

    @tool("Copy an earlier clipboard item back to the clipboard.", {"id": {"type": "integer"}})
    async def restore(self, id: int):
        import pyperclip
        with db.session() as s:
            item = s.get(ClipboardItem, int(id))
        if not item:
            return {"error": "not found"}
        pyperclip.copy(item.text)
        return {"copied": item.text[:100]}
