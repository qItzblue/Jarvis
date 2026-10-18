from pathlib import Path

from fastapi import APIRouter, File, UploadFile

from ..core.plugins import Plugin, tool


def extract_text(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        from pypdf import PdfReader
        return "\n".join(p.extract_text() or "" for p in PdfReader(str(path)).pages)
    return path.read_text(errors="replace")


class DocumentsPlugin(Plugin):
    name, title, category, icon = "documents", "Document summariser", "productivity", "file-text"
    description = "Summarises or answers questions about PDFs and text files."

    async def _ask(self, text: str, question: str) -> str:
        return await self.ctx.llm.complete(f"{question}\n\nDocument:\n{text[:80000]}")

    @tool("Summarise a local PDF or text file, or answer a question about it.", {
        "path": {"type": "string"}, "question": {"type": "string"}}, required=["path"])
    async def summarise(self, path: str, question: str = "Summarise this document in a few bullet points."):
        p = Path(path).expanduser()
        if not p.exists():
            return {"error": f"File not found: {p}"}
        text = extract_text(p)
        return {"file": str(p), "characters": len(text), "answer": await self._ask(text, question)}

    def router(self):
        r = APIRouter()

        @r.post("/upload")
        async def upload(file: UploadFile = File(...)):
            import tempfile
            suffix = Path(file.filename or "x.txt").suffix
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
                f.write(await file.read())
            return await self.summarise(f.name)
        return r
