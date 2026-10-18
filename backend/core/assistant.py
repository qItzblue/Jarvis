"""The assistant loop: history + memory -> LLM -> tools -> streamed reply."""
import asyncio
import json
import logging
import re
from datetime import datetime
from typing import Awaitable, Callable

from .. import db
from ..db import Conversation, Message, utcnow
from .llm import LLMNotConfigured
from .plugins import Context

log = logging.getLogger("jarvis.assistant")
Emit = Callable[[dict], Awaitable[None]]
_BOUNDARY = re.compile(r"[.!?…]+[\"')\]]?\s+|\n+")
MAX_TOOL_ROUNDS = 8
HISTORY_LIMIT = 24


class SentenceSplitter:
    """Collects streamed tokens and yields complete sentences for TTS."""

    def __init__(self):
        self.buf = ""

    def feed(self, text: str) -> list[str]:
        self.buf += text
        out = []
        while m := _BOUNDARY.search(self.buf):
            sentence, self.buf = self.buf[:m.end()].strip(), self.buf[m.end():]
            if sentence:
                out.append(sentence)
        return out

    def flush(self) -> list[str]:
        rest, self.buf = self.buf.strip(), ""
        return [rest] if rest else []


def clean_for_speech(text: str) -> str:
    text = re.sub(r"```.*?```", " (code shown on screen) ", text, flags=re.S)
    return re.sub(r"[*_`#>|]", "", text).strip()


class Assistant:
    def __init__(self, ctx: Context):
        self.ctx = ctx

    def system_prompt(self, user_text: str) -> str:
        s = self.ctx.settings
        lang = s.get("assistant.language")
        lines = [
            f"You are {s.get('assistant.name')}, a personal AI assistant running on the user's computer.",
            f"Personality: {s.get('assistant.personality')}",
            f"Address the user as '{s.get('assistant.user_name')}'.",
            f"Verbosity level {s.get('assistant.verbosity')}/5: replies are usually spoken aloud, so keep them "
            "short and natural unless asked for detail. Avoid markdown tables in spoken answers.",
            "Reply in the same language the user writes in." if lang in (None, "", "auto")
            else f"Always reply in {lang}.",
            f"Current local time: {datetime.now().strftime('%A %d %B %Y, %H:%M')}.",
            "Use tools whenever they help. If a tool reports it is not configured, tell the user which "
            "setting is missing. Never claim you did something a tool did not confirm.",
            "When the user tells you a lasting personal fact or preference, save it with memory__remember.",
        ]
        facts = self.ctx.memory.search(user_text, k=6) if self.ctx.memory else []
        if facts:
            lines.append("Things you remember about the user:\n" + "\n".join(f"- {f['text']}" for f in facts))
        return "\n".join(lines)

    # --- persistence ----------------------------------------------------
    def _ensure_conversation(self, conversation_id: int | None, text: str, source: str) -> int:
        with db.session() as s:
            conv = s.get(Conversation, conversation_id) if conversation_id else None
            if conv is None:
                conv = Conversation(title=text[:60] or "New conversation", source=source)
                s.add(conv)
                s.flush()
            conv.updated_at = utcnow()
            return conv.id

    def _history(self, conversation_id: int) -> list[dict]:
        with db.session() as s:
            rows = (s.query(Message).filter_by(conversation_id=conversation_id)
                    .order_by(Message.id.desc()).limit(HISTORY_LIMIT).all())
        hist = [{"role": r.role, "content": r.content} for r in reversed(rows)]
        while hist and hist[0]["role"] != "user":  # providers want a user turn first
            hist.pop(0)
        return hist

    def _save(self, conversation_id: int, role: str, content: str) -> None:
        with db.session() as s:
            s.add(Message(conversation_id=conversation_id, role=role, content=content))

    # --- main entry point ----------------------------------------------
    async def handle(self, text: str, emit: Emit, conversation_id: int | None = None,
                     source: str = "desktop", images: list[str] | None = None) -> str:
        conv_id = self._ensure_conversation(conversation_id, text, source)
        await emit({"type": "start", "conversation_id": conv_id})
        self._save(conv_id, "user", text)

        routines = self.ctx.registry.get("routines") if self.ctx.registry else None
        if routines and (routine := routines.match(text)):
            reply = await routines.run(routine, emit=emit)
            return await self._finish(conv_id, reply, emit, speak_all=True)

        try:
            provider = self.ctx.llm.provider()
        except LLMNotConfigured as e:
            await emit({"type": "error", "message": str(e)})
            return ""

        history = self._history(conv_id)
        if images and history:
            history[-1]["images"] = images
        messages = provider.native(history)
        tools = self.ctx.registry.tools() if self.ctx.registry else []
        specs = [t.spec() for t in tools]
        splitter, full = SentenceSplitter(), ""
        try:
            for _ in range(MAX_TOOL_ROUNDS):
                end = None
                async for ev in provider.stream(self.system_prompt(text), messages, specs):
                    if ev["type"] == "text":
                        full += ev["text"]
                        await emit({"type": "token", "text": ev["text"]})
                        for sent in splitter.feed(ev["text"]):
                            await emit({"type": "sentence", "text": clean_for_speech(sent)})
                    elif ev["type"] == "end":
                        end = ev
                if not end or not end["tool_calls"]:
                    break
                messages.append(end["assistant"])
                results = []
                for call in end["tool_calls"]:
                    await emit({"type": "tool", "name": call["name"], "args": call["args"], "status": "running"})
                    result = await self.ctx.registry.call(call["name"], call["args"], source=source)
                    await emit({"type": "tool", "name": call["name"], "status": "done",
                                "ok": not (isinstance(result, dict) and "error" in result),
                                "result": json.loads(json.dumps(result, default=str))})
                    results.append((call["id"], result))
                messages.extend(provider.tool_results(results))
                if full and not full.endswith(("\n", " ")):
                    full += "\n"
                    await emit({"type": "token", "text": "\n"})
        except asyncio.CancelledError:
            if full:
                self._save(conv_id, "assistant", full + " …(interrupted)")
            raise
        except Exception as e:
            log.exception("LLM error")
            await emit({"type": "error", "message": f"{type(e).__name__}: {e}"})
            if not full:
                return ""
        for sent in splitter.flush():
            await emit({"type": "sentence", "text": clean_for_speech(sent)})
        return await self._finish(conv_id, full, emit)

    async def _finish(self, conv_id: int, text: str, emit: Emit, speak_all: bool = False) -> str:
        text = text.strip()
        if text:
            self._save(conv_id, "assistant", text)
        if speak_all and text:
            await emit({"type": "token", "text": text})
            await emit({"type": "sentence", "text": clean_for_speech(text)})
        await emit({"type": "done", "conversation_id": conv_id, "text": text})
        return text
