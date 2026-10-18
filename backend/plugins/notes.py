import uuid

from fastapi import APIRouter, File, Form, UploadFile
from pydantic import BaseModel

from .. import config, db
from ..db import Note, row_dict, utcnow
from ..core.plugins import Plugin, tool


class NoteBody(BaseModel):
    title: str = ""
    body: str = ""


class NotesPlugin(Plugin):
    name, title, category, icon = "notes", "Notes & voice memos", "productivity", "notebook"
    description = "Write, search and read back notes; record voice memos with automatic transcripts."

    @tool("Create a note.", {"title": {"type": "string"}, "body": {"type": "string"}}, required=["body"])
    async def create_note(self, body: str, title: str = ""):
        with db.session() as s:
            n = Note(title=title or body[:40], body=body)
            s.add(n)
            s.flush()
            return row_dict(n)

    @tool("Search notes by text.", {"query": {"type": "string"}})
    async def search_notes(self, query: str):
        q = f"%{query}%"
        with db.session() as s:
            rows = s.query(Note).filter((Note.title.ilike(q)) | (Note.body.ilike(q))).limit(20).all()
            return [row_dict(n) for n in rows]

    @tool("List recent notes.", {})
    async def list_notes(self):
        with db.session() as s:
            return [row_dict(n) for n in s.query(Note).order_by(Note.updated_at.desc()).limit(100)]

    @tool("Append text to an existing note.", {"id": {"type": "integer"}, "text": {"type": "string"}})
    async def append_note(self, id: int, text: str):
        with db.session() as s:
            n = s.get(Note, int(id))
            if not n:
                return {"error": "note not found"}
            n.body, n.updated_at = (n.body + "\n" + text).strip(), utcnow()
            return row_dict(n)

    @tool("Delete a note.", {"id": {"type": "integer"}}, confirm=True)
    async def delete_note(self, id: int):
        with db.session() as s:
            return {"deleted": s.query(Note).filter_by(id=int(id)).delete() > 0}

    def router(self):
        r = APIRouter()
        r.get("")(self.list_notes)

        @r.post("")
        async def create(b: NoteBody):
            return await self.create_note(b.body, b.title)

        @r.put("/{nid}")
        async def update(nid: int, b: NoteBody):
            with db.session() as s:
                n = s.get(Note, nid)
                n.title, n.body, n.updated_at = b.title, b.body, utcnow()
                return row_dict(n)

        @r.delete("/{nid}")
        async def delete(nid: int):
            with db.session() as s:
                s.query(Note).filter_by(id=nid).delete()
            return {"ok": True}

        @r.post("/memo")
        async def memo(audio: UploadFile = File(...), title: str = Form("Voice memo")):
            folder = config.DATA_DIR / "memos"
            folder.mkdir(exist_ok=True)
            path = folder / f"{uuid.uuid4().hex}.wav"
            data = await audio.read()
            path.write_bytes(data)
            stt = self.ctx.voice["stt"]
            text = (await stt.transcribe(data))["text"] if stt.available() else "(transcription unavailable)"
            with db.session() as s:
                n = Note(title=title, body=text, audio_path=str(path))
                s.add(n)
                s.flush()
                return row_dict(n)

        @r.get("/{nid}/audio")
        async def audio(nid: int):
            from fastapi.responses import FileResponse
            with db.session() as s:
                n = s.get(Note, nid)
            return FileResponse(n.audio_path, media_type="audio/wav")
        return r
