from fastapi import APIRouter, File, UploadFile

from .. import db
from ..db import Note, row_dict
from ..core.plugins import Plugin, tool

PROMPT = ("Summarise this meeting transcript. Give: a 2-3 sentence overview, key decisions, "
          "action items with owners if mentioned, and open questions.\n\nTranscript:\n")


class MeetingsPlugin(Plugin):
    name, title, category, icon = "meetings", "Meeting notes", "productivity", "users"
    description = "Transcribes meeting recordings locally and writes a summary note."

    async def summarise_text(self, transcript: str, title: str = "Meeting") -> dict:
        summary = await self.ctx.llm.complete(PROMPT + transcript[:60000])
        with db.session() as s:
            n = Note(title=f"{title} – summary", body=f"{summary}\n\n---\nTranscript:\n{transcript}")
            s.add(n)
            s.flush()
            return {"note": row_dict(n), "summary": summary}

    @tool("Summarise a meeting transcript and save it as a note.", {"transcript": {"type": "string"},
                                                                     "title": {"type": "string"}},
          required=["transcript"])
    async def summarise(self, transcript: str, title: str = "Meeting"):
        return await self.summarise_text(transcript, title)

    def router(self):
        r = APIRouter()

        @r.post("/upload")
        async def upload(audio: UploadFile = File(...)):
            stt = self.ctx.voice["stt"]
            if not stt.available():
                return {"error": "Speech-to-text is not installed."}
            text = (await stt.transcribe(await audio.read()))["text"]
            return await self.summarise_text(text, audio.filename or "Meeting")
        return r
