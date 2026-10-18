import asyncio

import pytest
from fastapi.testclient import TestClient

from backend.core.assistant import Assistant, SentenceSplitter, clean_for_speech
from backend.core.memory import cosine, embed
from backend.tests.conftest import FakeLLM


def test_sentence_splitter_streams_sentences():
    sp = SentenceSplitter()
    out = sp.feed("Hello there. How ") + sp.feed("are you? Fine") + sp.flush()
    assert out == ["Hello there.", "How are you?", "Fine"]


def test_clean_for_speech_strips_markdown_and_code():
    assert clean_for_speech("**Hi** `x`") == "Hi x"
    assert "code shown" in clean_for_speech("```py\nprint()\n```")


def test_embedding_similarity_prefers_related_text():
    q = embed("what is my favourite colour")
    assert cosine(q, embed("favourite colour is blue")) > cosine(q, embed("dentist on tuesday"))


def test_memory_store_roundtrip(ctx):
    f = ctx.memory.add("User's dog is called Rex")
    assert ctx.memory.search("dog name")[0]["id"] == f["id"]
    assert ctx.memory.update(f["id"], "User's dog is called Max")
    assert ctx.memory.delete(f["id"]) and ctx.memory.list() == []


def test_settings_env_fallback_and_override(ctx, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key")
    assert ctx.settings.get("anthropic.api_key") == "env-key"
    ctx.settings.set("anthropic.api_key", "ui-key")
    assert ctx.settings.get("anthropic.api_key") == "ui-key"
    view = {s["key"]: s for s in ctx.settings.core_view()}
    assert view["anthropic.api_key"]["value"].endswith("-key") and "ui" not in view["anthropic.api_key"]["value"]


async def test_confirmation_flow(ctx):
    q = ctx.bus.subscribe()
    task = asyncio.create_task(ctx.confirm.request("Shut down?"))
    ev = await asyncio.wait_for(q.get(), 1)
    assert ev["type"] == "confirm_request"
    ctx.confirm.resolve(ev["id"], True)
    assert await task is True


async def test_registry_denied_confirmation(reg, monkeypatch):
    async def no(*a, **k):
        return False
    monkeypatch.setattr(reg.ctx.confirm, "request", no)
    res = await reg.call("power__shutdown", {})
    assert "declined" in res["error"]


async def test_registry_unknown_tool_and_disabled_plugin(reg, ctx):
    assert "not available" in (await reg.call("nope__x"))["error"]
    ctx.settings.set("plugin.weather.enabled", False)
    assert reg.find_tool("weather__forecast") is None


class ScriptedProvider:
    """Fake provider: first round calls a tool, second round answers."""
    name = "scripted"

    def __init__(self):
        self.rounds = 0

    def native(self, history):
        return list(history)

    async def stream(self, system, messages, tools):
        self.rounds += 1
        if self.rounds == 1:
            yield {"type": "text", "text": "Let me check. "}
            yield {"type": "end", "tool_calls": [{"id": "1", "name": "convert__units",
                                                  "args": {"value": 1, "from_unit": "km", "to_unit": "m"}}],
                   "assistant": {"role": "assistant", "content": "Let me check."}}
        else:
            assert messages[-1]["role"] == "tool"
            yield {"type": "text", "text": "It is 1000 metres."}
            yield {"type": "end", "tool_calls": [], "assistant": {}}

    def tool_results(self, results):
        return [{"role": "tool", "content": str(r)} for _, r in results]


async def test_assistant_tool_loop_streams_and_saves(ctx):
    ctx.llm = FakeLLM(ScriptedProvider())
    events = []

    async def emit(ev):
        events.append(ev)
    reply = await Assistant(ctx).handle("how many metres in a km", emit)
    kinds = [e["type"] for e in events]
    assert reply.endswith("It is 1000 metres.")
    assert "tool" in kinds and kinds[-1] == "done"
    assert any(e["type"] == "sentence" and e["text"] == "It is 1000 metres." for e in events)
    tool_done = next(e for e in events if e["type"] == "tool" and e["status"] == "done")
    assert tool_done["result"]["result"] == 1000


async def test_assistant_reports_missing_key(app):
    from backend.core.llm import LLMService
    ctx = app.state.ctx
    ctx.llm = LLMService(ctx.settings)
    ctx.settings.set("anthropic.api_key", "")
    events = []

    async def emit(ev):
        events.append(ev)
    import os
    os.environ.pop("ANTHROPIC_API_KEY", None)
    await Assistant(ctx).handle("hi", emit)
    assert events[-1]["type"] == "error" and "API key" in events[-1]["message"]


def test_rest_api_basics(app):
    with TestClient(app) as c:
        assert c.get("/api/health").json() == {"ok": True}
        plugins = c.get("/api/plugins").json()
        assert {p["status"] for p in plugins} >= {"ok", "not_configured"}
        r = c.put("/api/plugins/weather", json={"settings": {"location": "Paris"}}).json()
        assert next(s for s in r["settings"] if s["key"] == "location")["value"] == "Paris"
        c.put("/api/settings", json={"values": {"assistant.name": "Friday"}})
        assert c.get("/api/status").json()["assistant_name"] == "Friday"
        assert c.post("/api/tools/convert__units", json={"args": {"value": 0, "from_unit": "c",
                                                                   "to_unit": "f"}}).json()["result"]["result"] == 32
        mem = c.post("/api/memory", json={"text": "likes tea"}).json()
        assert c.get("/api/memory").json()[0]["id"] == mem["id"]


def test_websocket_chat_without_key_returns_error(app, monkeypatch):
    from backend.core.llm import LLMService
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    app.state.ctx.llm = LLMService(app.state.ctx.settings)
    with TestClient(app) as c, c.websocket_connect("/ws") as ws:
        ws.send_json({"type": "chat", "text": "hello"})
        assert ws.receive_json()["type"] == "start"
        assert ws.receive_json()["type"] == "error"


@pytest.mark.parametrize("provider,key", [("nanogpt", "nanogpt.api_key"), ("gemini", "google.api_key")])
def test_openai_compatible_providers_selected(ctx, provider, key):
    from backend.core.llm import LLMService
    llm = LLMService(ctx.settings)
    ctx.settings.set("llm.provider", provider)
    ctx.settings.set(key, "k")
    p = llm.provider()
    assert p.name == provider and str(p.client.base_url).startswith("https://")
