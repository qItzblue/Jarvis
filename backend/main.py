"""Jarvis backend entry point: `python -m backend.main`."""
import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import config, db
from .api import routes, ws
from .core.assistant import Assistant
from .core.confirm import Confirmations
from .core.events import EventBus
from .core.llm import LLMService
from .core.memory import MemoryStore
from .core.plugins import Context, Registry
from .core.settings import Settings
from .voice.stt import STT
from .voice.tts import TTS


def create_app(db_url: str | None = None, discover: bool = True, start_plugins: bool = True) -> FastAPI:
    db.init_db(db_url or config.DB_URL)
    settings = Settings()
    bus = EventBus()
    http = httpx.AsyncClient(timeout=20, follow_redirects=True, headers={"User-Agent": "Jarvis/1.0"})
    ctx = Context(settings=settings, bus=bus, confirm=Confirmations(bus), llm=LLMService(settings),
                  memory=MemoryStore(), http=http)
    ctx.voice = {"stt": STT(settings), "tts": TTS(settings, http)}
    registry = Registry(ctx)
    if discover:
        registry.discover()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if start_plugins:
            await registry.start_all()
        yield
        await registry.stop_all()
        await http.aclose()

    app = FastAPI(title="Jarvis", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    app.state.ctx = ctx
    app.state.assistant = Assistant(ctx)
    ctx.extra["assistant"] = app.state.assistant
    app.include_router(routes.router)
    app.include_router(ws.router)
    for p in registry.plugins.values():
        r = p.router()
        if r is not None:
            app.include_router(r, prefix=f"/api/p/{p.name}")
    return app


def run():
    import uvicorn
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    uvicorn.run(create_app(), host=config.HOST, port=config.PORT)


if __name__ == "__main__":
    run()
