import base64
import uuid

from fastapi import APIRouter
from fastapi.responses import FileResponse

from .. import config
from ..core.llm import NANOGPT_BASE
from ..core.plugins import Plugin, tool

FOLDER = config.DATA_DIR / "images"


class ImagesPlugin(Plugin):
    name, title, category, icon = "images", "Image generation", "extras", "image"
    description = "Generates images with NanoGPT or Google Gemini, and describes images."
    settings_schema = {
        "provider": {"label": "Image provider", "type": "select", "options": ["gemini", "nanogpt"], "default": "gemini"},
        "gemini_model": {"label": "Gemini image model", "type": "string", "default": "gemini-2.5-flash-image"},
        "nanogpt_model": {"label": "NanoGPT image model", "type": "string", "default": "dall-e-3"},
    }

    def is_configured(self) -> bool:
        key = "google.api_key" if self.setting("provider") == "gemini" else "nanogpt.api_key"
        return bool(self.ctx.settings.get(key))

    def _save(self, data: bytes) -> dict:
        FOLDER.mkdir(parents=True, exist_ok=True)
        name = f"{uuid.uuid4().hex[:12]}.png"
        (FOLDER / name).write_bytes(data)
        return {"file": str(FOLDER / name), "url": f"/api/p/images/file/{name}"}

    @tool("Generate an image from a text prompt.", {"prompt": {"type": "string"}})
    async def generate(self, prompt: str):
        if self.setting("provider") == "nanogpt":
            r = await self.ctx.http.post(f"{NANOGPT_BASE}/images/generations", timeout=120, json={
                "model": self.setting("nanogpt_model"), "prompt": prompt, "n": 1, "size": "1024x1024",
                "response_format": "b64_json"}, headers={"Authorization": f"Bearer {self.ctx.settings.get('nanogpt.api_key')}"})
            r.raise_for_status()
            item = r.json()["data"][0]
            data = base64.b64decode(item["b64_json"]) if item.get("b64_json") else (await self.ctx.http.get(item["url"])).content
            return self._save(data)
        model = self.setting("gemini_model")
        r = await self.ctx.http.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent", timeout=120,
            params={"key": self.ctx.settings.get("google.api_key")},
            json={"contents": [{"parts": [{"text": prompt}]}],
                  "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]}})
        r.raise_for_status()
        for part in r.json()["candidates"][0]["content"]["parts"]:
            if "inlineData" in part:
                return self._save(base64.b64decode(part["inlineData"]["data"]))
        return {"error": "The model returned no image."}

    @tool("Describe a local image file.", {"path": {"type": "string"}, "question": {"type": "string"}},
          required=["path"])
    async def describe(self, path: str, question: str = "Describe this image."):
        from pathlib import Path
        b64 = base64.b64encode(Path(path).expanduser().read_bytes()).decode()
        return {"answer": await self.ctx.llm.complete(question, images=[b64])}

    def router(self):
        r = APIRouter()

        @r.get("/file/{name}")
        async def file(name: str):
            return FileResponse(FOLDER / name.replace("/", ""))

        @r.get("")
        async def gallery():
            return sorted((f"/api/p/images/file/{p.name}" for p in FOLDER.glob("*.png")), reverse=True) if FOLDER.exists() else []
        return r
