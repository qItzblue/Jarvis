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
from fastapi.responses import FileResponse, StreamingResponse

NANOGPT_BASE = os.environ.get("NANOGPT_BASE", "https://nano-gpt.com/api/v1").rstrip("/")
NANOGPT_KEY = os.environ.get("NANOGPT_API_KEY", "")
DEFAULT_MODEL = os.environ.get("NANOGPT_MODEL", "chatgpt-4o-latest")
APP_PASSWORD = os.environ.get("APP_PASSWORD", "")
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


def _headers() -> dict:
    if not NANOGPT_KEY:
        raise HTTPException(500, "NANOGPT_API_KEY is not set on the server")
    return {"Authorization": f"Bearer {NANOGPT_KEY}"}


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/config")
def config():
    return {"needs_password": bool(APP_PASSWORD), "default_model": DEFAULT_MODEL}


@app.get("/api/models")
async def models(request: Request):
    _check_auth(request)
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(f"{NANOGPT_BASE}/models", headers=_headers())
    if r.status_code != 200:
        raise HTTPException(r.status_code, r.text[:300])
    ids = sorted(m["id"] for m in r.json().get("data", []) if "id" in m)
    return {"models": ids}


@app.post("/api/chat")
async def chat(request: Request):
    _check_auth(request)
    body = await request.json()
    messages = [m for m in body.get("messages", []) if m.get("role") in ("user", "assistant")][-40:]
    payload = {
        "model": body.get("model") or DEFAULT_MODEL,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}, *messages],
        "stream": True,
    }
    headers = _headers()

    async def relay():
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", f"{NANOGPT_BASE}/chat/completions",
                                     headers=headers, json=payload) as r:
                if r.status_code != 200:
                    err = (await r.aread()).decode(errors="replace")[:300]
                    yield f"data: {json.dumps({'error': err})}\n\n"
                    return
                async for line in r.aiter_lines():
                    if line:
                        yield line + "\n\n"

    return StreamingResponse(relay(), media_type="text/event-stream")
