"""REST endpoints used by the desktop UI."""
from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from .. import db
from ..core.settings import CORE_SCHEMA
from ..db import Conversation, Message, row_dict
from ..voice.stt import STT
from ..voice.tts import TTSUnavailable
from ..voice.wakeword import WakeWord

router = APIRouter(prefix="/api")


def ctx(request: Request):
    return request.app.state.ctx


@router.get("/health")
async def health():
    return {"ok": True}


@router.get("/status")
async def status(request: Request):
    c = ctx(request)
    return {"provider": c.llm.provider_name(), "llm_configured": c.llm.configured(),
            "assistant_name": c.settings.get("assistant.name"),
            "voice": {"stt": STT.available(), "wake_word": WakeWord.available(), "tts": c.voice["tts"].status()},
            "plugins": {p.name: p.status() for p in c.registry.plugins.values()}}


# --- settings -------------------------------------------------------------
class SettingsUpdate(BaseModel):
    values: dict[str, object]


@router.get("/settings")
async def get_settings(request: Request):
    return ctx(request).settings.core_view()


@router.put("/settings")
async def put_settings(body: SettingsUpdate, request: Request):
    s = ctx(request).settings
    for key, val in body.values.items():
        if key not in CORE_SCHEMA:
            raise HTTPException(400, f"Unknown setting {key}")
        if CORE_SCHEMA[key].get("secret") and isinstance(val, str) and val.startswith("••"):
            continue  # masked value echoed back unchanged
        s.set(key, val)
    return s.core_view()


# --- plugins --------------------------------------------------------------
class PluginUpdate(BaseModel):
    enabled: bool | None = None
    settings: dict[str, object] | None = None


@router.get("/plugins")
async def list_plugins(request: Request):
    return [p.info() for p in ctx(request).registry.plugins.values()]


@router.put("/plugins/{name}")
async def update_plugin(name: str, body: PluginUpdate, request: Request):
    c = ctx(request)
    p = c.registry.plugins.get(name)
    if not p:
        raise HTTPException(404, "No such plugin")
    was_ok = p.status() == "ok"
    if body.enabled is not None:
        c.settings.set(f"plugin.{name}.enabled", body.enabled)
    for key, val in (body.settings or {}).items():
        if key not in p.settings_schema:
            raise HTTPException(400, f"Unknown setting {key}")
        if p.settings_schema[key].get("secret") and isinstance(val, str) and val.startswith("••"):
            continue
        c.settings.set(f"{name}.{key}", val)
    now_ok = p.status() == "ok"
    if now_ok and not was_ok:
        await p.start()
    elif was_ok and not now_ok:
        await p.stop()
    return p.info()


class ToolCall(BaseModel):
    args: dict = {}


@router.post("/tools/{name}")
async def call_tool(name: str, body: ToolCall, request: Request):
    """Lets UI widgets call tools directly; confirmation rules still apply."""
    return {"result": await ctx(request).registry.call(name, body.args, source="ui")}


@router.get("/tools")
async def list_tools(request: Request):
    return [{"name": t.name, "description": t.description, "confirm": t.confirm, "schema": t.schema}
            for t in ctx(request).registry.tools()]


# --- conversations --------------------------------------------------------
@router.get("/conversations")
async def conversations():
    with db.session() as s:
        rows = s.query(Conversation).order_by(Conversation.updated_at.desc()).limit(200).all()
        return [row_dict(r) for r in rows]


@router.get("/conversations/{cid}")
async def conversation(cid: int):
    with db.session() as s:
        conv = s.get(Conversation, cid)
        if not conv:
            raise HTTPException(404)
        msgs = s.query(Message).filter_by(conversation_id=cid).order_by(Message.id).all()
        return {**row_dict(conv), "messages": [row_dict(m) for m in msgs]}


@router.delete("/conversations/{cid}")
async def delete_conversation(cid: int):
    with db.session() as s:
        s.query(Message).filter_by(conversation_id=cid).delete()
        s.query(Conversation).filter_by(id=cid).delete()
    return {"ok": True}


# --- memory ---------------------------------------------------------------
class MemoryBody(BaseModel):
    text: str


@router.get("/memory")
async def memory_list(request: Request):
    return ctx(request).memory.list()


@router.post("/memory")
async def memory_add(body: MemoryBody, request: Request):
    return ctx(request).memory.add(body.text)


@router.put("/memory/{fid}")
async def memory_update(fid: int, body: MemoryBody, request: Request):
    return {"ok": ctx(request).memory.update(fid, body.text)}


@router.delete("/memory/{fid}")
async def memory_delete(fid: int, request: Request):
    return {"ok": ctx(request).memory.delete(fid)}


# --- voice ----------------------------------------------------------------
@router.post("/stt")
async def stt(request: Request, audio: UploadFile = File(...)):
    engine: STT = ctx(request).voice["stt"]
    if not engine.available():
        raise HTTPException(501, "Speech-to-text is not installed (pip install -r requirements-voice.txt).")
    return await engine.transcribe(await audio.read())


class TTSBody(BaseModel):
    text: str


@router.post("/tts")
async def tts(body: TTSBody, request: Request):
    try:
        data, mime = await ctx(request).voice["tts"].synth(body.text)
    except TTSUnavailable as e:
        raise HTTPException(501, str(e))
    return Response(content=data, media_type=mime)


# --- data export / wipe ---------------------------------------------------
@router.get("/export")
async def export_data(request: Request):
    from ..db import ClipboardItem, MemoryFact, Note, Reminder, Routine, Todo
    out = {}
    with db.session() as s:
        for model in (Conversation, Message, MemoryFact, Note, Todo, Reminder, Routine, ClipboardItem):
            out[model.__tablename__] = [{k: v for k, v in row_dict(r).items() if k != "vector"}
                                        for r in s.query(model).all()]
    return out
