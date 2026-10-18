import asyncio
import base64
import io

from fastapi import APIRouter
from pydantic import BaseModel

from .. import config
from ..core.plugins import Plugin, tool

FACES = config.DATA_DIR / "faces"


class Frame(BaseModel):
    image: str  # base64 jpeg/png
    name: str = ""


class VisionPlugin(Plugin):
    name, title, category, icon = "vision", "Camera vision", "vision", "scan-face"
    description = ("Opt-in webcam features: local face recognition to greet you, and hand-gesture control "
                   "(runs in the app). Nothing leaves your computer.")
    default_enabled = False
    settings_schema = {
        "face_greeting": {"label": "Greet me when I sit down", "type": "boolean", "default": False},
        "gestures": {"label": "Hand-gesture control", "type": "boolean", "default": False},
    }

    def face_available(self) -> bool:
        import importlib.util
        return importlib.util.find_spec("face_recognition") is not None

    def _encode(self, b64: str):
        import face_recognition
        import numpy as np
        from PIL import Image
        img = np.array(Image.open(io.BytesIO(base64.b64decode(b64.split(",")[-1]))).convert("RGB"))
        enc = face_recognition.face_encodings(img)
        return enc[0] if enc else None

    def enroll(self, b64: str, name: str) -> dict:
        import numpy as np
        enc = self._encode(b64)
        if enc is None:
            return {"error": "No face found in the image"}
        FACES.mkdir(parents=True, exist_ok=True)
        np.save(FACES / f"{name}.npy", enc)
        return {"enrolled": name}

    def identify(self, b64: str) -> dict:
        import face_recognition
        import numpy as np
        enc = self._encode(b64)
        if enc is None:
            return {"face": False}
        known = {p.stem: np.load(p) for p in FACES.glob("*.npy")} if FACES.exists() else {}
        if not known:
            return {"face": True, "name": None}
        names = list(known)
        dists = face_recognition.face_distance([known[n] for n in names], enc)
        best = int(dists.argmin())
        return {"face": True, "name": names[best] if dists[best] < 0.55 else None}

    @tool("List people enrolled for face recognition.", {})
    async def known_faces(self):
        return sorted(p.stem for p in FACES.glob("*.npy")) if FACES.exists() else []

    def router(self):
        r = APIRouter()

        @r.get("/config")
        async def cfg():
            return {"face_available": self.face_available(), "face_greeting": bool(self.setting("face_greeting")),
                    "gestures": bool(self.setting("gestures")), "known": await self.known_faces()}

        @r.post("/enroll")
        async def enroll(f: Frame):
            if not self.face_available():
                return {"error": "pip install face-recognition to enable face recognition."}
            return await asyncio.to_thread(self.enroll, f.image, f.name or "me")

        @r.post("/identify")
        async def identify(f: Frame):
            if not self.face_available():
                return {"error": "face recognition not installed"}
            res = await asyncio.to_thread(self.identify, f.image)
            if res.get("name"):
                self.ctx.bus.publish({"type": "greet", "name": res["name"]})
            return res

        @r.delete("/faces/{name}")
        async def forget(name: str):
            (FACES / f"{name}.npy").unlink(missing_ok=True)
            return {"ok": True}
        return r
