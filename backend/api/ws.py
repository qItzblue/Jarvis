"""WebSockets: /ws carries chat + live events, /ws/audio carries mic audio for the wake word."""
import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..voice.wakeword import WakeWord

router = APIRouter()
log = logging.getLogger("jarvis.ws")


@router.websocket("/ws")
async def ws_main(ws: WebSocket):
    await ws.accept()
    ctx = ws.app.state.ctx
    assistant = ws.app.state.assistant
    queue = ctx.bus.subscribe()
    send_lock = asyncio.Lock()
    task: asyncio.Task | None = None

    async def send(msg: dict):
        async with send_lock:
            await ws.send_text(json.dumps(msg, default=str))

    async def pump():
        while True:
            await send(await queue.get())

    pump_task = asyncio.create_task(pump())
    try:
        while True:
            msg = json.loads(await ws.receive_text())
            kind = msg.get("type")
            if kind == "chat":
                if task and not task.done():
                    task.cancel()
                task = asyncio.create_task(assistant.handle(
                    msg.get("text", ""), send, msg.get("conversation_id"), images=msg.get("images")))
            elif kind == "cancel":
                if task and not task.done():
                    task.cancel()
                    await send({"type": "cancelled"})
            elif kind == "confirm":
                ctx.confirm.resolve(msg.get("id", ""), bool(msg.get("approved")))
            elif kind == "ping":
                await send({"type": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        pump_task.cancel()
        if task and not task.done():
            task.cancel()
        ctx.bus.unsubscribe(queue)


@router.websocket("/ws/audio")
async def ws_audio(ws: WebSocket):
    await ws.accept()
    if not WakeWord.available():
        await ws.send_json({"type": "wake_unavailable",
                            "message": "openWakeWord is not installed (pip install -r requirements-voice.txt)."})
        await ws.close()
        return
    detector = WakeWord()
    try:
        while True:
            data = await ws.receive_bytes()
            if await asyncio.to_thread(detector.feed, data):
                await ws.send_json({"type": "wake"})
    except WebSocketDisconnect:
        pass
