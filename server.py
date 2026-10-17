"""Jarvis web — a small browser assistant backed by NanoGPT.

The browser never sees the NanoGPT key: it talks to this server, which adds the
key and forwards the request. Optional APP_PASSWORD keeps strangers from
spending your subscription.
"""
import json
import os
import secrets
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response, StreamingResponse

NANOGPT_BASE = os.environ.get("NANOGPT_BASE", "https://nano-gpt.com/api/v1").rstrip("/")
NANOGPT_KEY = os.environ.get("NANOGPT_API_KEY", "")
DEFAULT_MODEL = os.environ.get("NANOGPT_MODEL", "chatgpt-4o-latest")
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/openai"
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_PREFIX = "google-direct/"  # NanoGPT already has "google/..." models, so direct ones need their own prefix
APP_PASSWORD = os.environ.get("APP_PASSWORD", "")
# Spoken replies through NanoGPT's text-to-speech. Kokoro is cheap; ElevenLabs sounds best.
TTS_MODEL = os.environ.get("TTS_MODEL", "Kokoro-82m")
TTS_VOICE = os.environ.get("TTS_VOICE", "bm_george")
SYSTEM_PROMPT = os.environ.get(
    "SYSTEM_PROMPT",
    "You are J.A.R.V.I.S., a calm, witty, highly capable personal assistant. "
    "Answer concisely, address the user as 'sir' occasionally, and use Markdown when it helps.",
)

STATIC = Path(__file__).parent / "static"
app = FastAPI(docs_url=None, redoc_url=None)


def _check_auth(request: Request) -> None:
    if not APP_PASSWORD:
        return
    given = request.headers.get("x-app-password", "")
    if not secrets.compare_digest(given, APP_PASSWORD):
        raise HTTPException(401, "Wrong password")


def _route(model: str) -> tuple[str, dict, str]:
    """Pick the provider for a model: (base url, auth headers, model name it expects)."""
    if model.startswith(GEMINI_PREFIX):
        if not GEMINI_KEY:
            raise HTTPException(500, "GEMINI_API_KEY is not set on the server")
        return GEMINI_BASE, {"Authorization": f"Bearer {GEMINI_KEY}"}, model[len(GEMINI_PREFIX):]
    if not NANOGPT_KEY:
        raise HTTPException(500, "NANOGPT_API_KEY is not set on the server")
    return NANOGPT_BASE, {"Authorization": f"Bearer {NANOGPT_KEY}"}, model


async def _list_models(client: httpx.AsyncClient, base: str, key: str) -> list[str]:
    r = await client.get(f"{base}/models", headers={"Authorization": f"Bearer {key}"})
    r.raise_for_status()
    return [m["id"] for m in r.json().get("data", []) if "id" in m]


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/config")
def config():
    return {"needs_password": bool(APP_PASSWORD), "default_model": DEFAULT_MODEL,
            "server_voice": bool(NANOGPT_KEY and TTS_MODEL)}


@app.post("/api/tts")
async def tts(request: Request):
    _check_auth(request)
    if not NANOGPT_KEY:
        raise HTTPException(500, "NANOGPT_API_KEY is not set on the server")
    text = str((await request.json()).get("text", ""))[:4000]
    if not text.strip():
        raise HTTPException(400, "Nothing to say")
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            f"{NANOGPT_BASE}/audio/speech",
            headers={"Authorization": f"Bearer {NANOGPT_KEY}", "x-api-key": NANOGPT_KEY},
            json={"model": TTS_MODEL, "voice": TTS_VOICE, "input": text, "response_format": "mp3"},
        )
    if r.status_code != 200 or not r.headers.get("content-type", "").startswith("audio"):
        raise HTTPException(502, r.text[:300])
    return Response(r.content, media_type=r.headers["content-type"])


@app.get("/api/models")
async def models(request: Request):
    _check_auth(request)
    ids, errors = [], []
    async with httpx.AsyncClient(timeout=20) as client:
        if NANOGPT_KEY:
            try:
                ids += sorted(await _list_models(client, NANOGPT_BASE, NANOGPT_KEY))
            except httpx.HTTPError as e:
                errors.append(f"NanoGPT: {e}")
        if GEMINI_KEY:
            try:
                gem = await _list_models(client, GEMINI_BASE, GEMINI_KEY)
                ids += sorted(GEMINI_PREFIX + m.removeprefix("models/") for m in gem if "gemini" in m)
            except httpx.HTTPError as e:
                errors.append(f"Google: {e}")
    if not ids:
        raise HTTPException(502, "; ".join(errors) or "No API keys are set on the server")
    return {"models": ids}


@app.post("/api/chat")
async def chat(request: Request):
    _check_auth(request)
    body = await request.json()
    messages = [m for m in body.get("messages", []) if m.get("role") in ("user", "assistant")][-40:]
    base, headers, model = _route(body.get("model") or DEFAULT_MODEL)
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}, *messages],
        "stream": True,
    }

    async def relay():
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", f"{base}/chat/completions",
                                     headers=headers, json=payload) as r:
                if r.status_code != 200:
                    err = (await r.aread()).decode(errors="replace")[:300]
                    yield f"data: {json.dumps({'error': err})}\n\n"
                    return
                async for line in r.aiter_lines():
                    if line:
                        yield line + "\n\n"

    return StreamingResponse(relay(), media_type="text/event-stream")
