"""LLM providers behind one streaming + tool-use interface.

History messages use a neutral format: {"role": "user"|"assistant", "content": str,
"images": [base64 png, ...]?}. Each provider converts that into its own wire format and
keeps provider-native messages for the tool-use rounds inside a single turn.
"""
import json
from typing import AsyncIterator

from .settings import Settings

NANOGPT_BASE = "https://nano-gpt.com/api/v1"
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/openai/"


class LLMNotConfigured(Exception):
    pass


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, api_key: str, model: str):
        from anthropic import AsyncAnthropic
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model

    def native(self, history: list[dict]) -> list[dict]:
        out = []
        for m in history:
            if m.get("images"):
                blocks = [{"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b}}
                          for b in m["images"]]
                out.append({"role": m["role"], "content": blocks + [{"type": "text", "text": m["content"]}]})
            else:
                out.append({"role": m["role"], "content": m["content"]})
        return out

    async def stream(self, system: str, messages: list, tools: list[dict]) -> AsyncIterator[dict]:
        kwargs = {"model": self.model, "max_tokens": 4096, "system": system, "messages": messages}
        if tools:
            kwargs["tools"] = [{"name": t["name"], "description": t["description"],
                                "input_schema": t["schema"]} for t in tools]
        async with self.client.messages.stream(**kwargs) as s:
            async for text in s.text_stream:
                yield {"type": "text", "text": text}
            final = await s.get_final_message()
        calls = [{"id": b.id, "name": b.name, "args": b.input or {}} for b in final.content if b.type == "tool_use"]
        content = [b.model_dump(exclude_none=True) for b in final.content]
        yield {"type": "end", "tool_calls": calls, "assistant": {"role": "assistant", "content": content}}

    def tool_results(self, results: list[tuple[str, object]]) -> list[dict]:
        return [{"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": cid, "content": json.dumps(res, default=str)[:20000]}
            for cid, res in results]}]


class OpenAICompatProvider:
    """NanoGPT and Gemini both speak the OpenAI chat-completions dialect."""

    def __init__(self, name: str, api_key: str, model: str, base_url: str):
        from openai import AsyncOpenAI
        self.name = name
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self._system = ""

    def native(self, history: list[dict]) -> list[dict]:
        out = []
        for m in history:
            if m.get("images"):
                parts = [{"type": "text", "text": m["content"]}] + [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b}"}} for b in m["images"]]
                out.append({"role": m["role"], "content": parts})
            else:
                out.append({"role": m["role"], "content": m["content"]})
        return out

    async def stream(self, system: str, messages: list, tools: list[dict]) -> AsyncIterator[dict]:
        kwargs = {"model": self.model, "stream": True,
                  "messages": [{"role": "system", "content": system}] + messages}
        if tools:
            kwargs["tools"] = [{"type": "function", "function": {
                "name": t["name"], "description": t["description"], "parameters": t["schema"]}} for t in tools]
        text, calls = "", {}
        resp = await self.client.chat.completions.create(**kwargs)
        async for chunk in resp:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta.content:
                text += delta.content
                yield {"type": "text", "text": delta.content}
            for tc in delta.tool_calls or []:
                slot = calls.setdefault(tc.index, {"id": "", "name": "", "args": ""})
                if tc.id:
                    slot["id"] = tc.id
                if tc.function and tc.function.name:
                    slot["name"] += tc.function.name
                if tc.function and tc.function.arguments:
                    slot["args"] += tc.function.arguments
        parsed = []
        for i, c in sorted(calls.items()):
            try:
                args = json.loads(c["args"] or "{}")
            except json.JSONDecodeError:
                args = {}
            parsed.append({"id": c["id"] or f"call_{i}", "name": c["name"], "args": args})
        assistant = {"role": "assistant", "content": text or None}
        if parsed:
            assistant["tool_calls"] = [{"id": c["id"], "type": "function", "function": {
                "name": c["name"], "arguments": json.dumps(c["args"])}} for c in parsed]
        yield {"type": "end", "tool_calls": parsed, "assistant": assistant}

    def tool_results(self, results: list[tuple[str, object]]) -> list[dict]:
        return [{"role": "tool", "tool_call_id": cid, "content": json.dumps(res, default=str)[:20000]}
                for cid, res in results]


class LLMService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def provider_name(self) -> str:
        return str(self.settings.get("llm.provider") or "anthropic")

    def configured(self) -> bool:
        key = {"anthropic": "anthropic.api_key", "nanogpt": "nanogpt.api_key", "gemini": "google.api_key"}
        return bool(self.settings.get(key.get(self.provider_name(), "")))

    def provider(self):
        s, name = self.settings, self.provider_name()
        if name == "nanogpt":
            key = s.get("nanogpt.api_key")
            if not key:
                raise LLMNotConfigured("NanoGPT API key is not set.")
            return OpenAICompatProvider("nanogpt", key, s.get("nanogpt.model"), NANOGPT_BASE)
        if name == "gemini":
            key = s.get("google.api_key")
            if not key:
                raise LLMNotConfigured("Google API key is not set.")
            return OpenAICompatProvider("gemini", key, s.get("gemini.model"), GEMINI_BASE)
        key = s.get("anthropic.api_key")
        if not key:
            raise LLMNotConfigured("Anthropic API key is not set. Add it in Settings or .env.")
        return AnthropicProvider(key, s.get("anthropic.model"))

    async def complete(self, prompt: str, system: str = "You are a helpful assistant.",
                       images: list[str] | None = None) -> str:
        p = self.provider()
        msgs = p.native([{"role": "user", "content": prompt, "images": images or []}])
        out = ""
        async for ev in p.stream(system, msgs, []):
            if ev["type"] == "text":
                out += ev["text"]
        return out.strip()
