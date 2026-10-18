"""Text-to-speech: Piper (local), ElevenLabs (cloud, optional) or the browser's built-in voice."""
import asyncio
import importlib.util
import io
import wave


class TTSUnavailable(Exception):
    pass


class TTS:
    def __init__(self, settings, http):
        self.settings = settings
        self.http = http
        self._piper = None
        self._piper_path = None

    def engine(self) -> str:
        return self.settings.get("voice.tts_engine") or "browser"

    def status(self) -> dict:
        return {"engine": self.engine(),
                "piper": importlib.util.find_spec("piper") is not None and bool(self.settings.get("voice.piper_model")),
                "elevenlabs": bool(self.settings.get("voice.elevenlabs_key"))}

    def _piper_synth(self, text: str) -> bytes:
        path = self.settings.get("voice.piper_model")
        if importlib.util.find_spec("piper") is None or not path:
            raise TTSUnavailable("Piper is not installed or no voice model is set.")
        if self._piper is None or self._piper_path != path:
            from piper import PiperVoice
            self._piper, self._piper_path = PiperVoice.load(path), path
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            if hasattr(self._piper, "synthesize_wav"):
                self._piper.synthesize_wav(text, wf)
            else:
                self._piper.synthesize(text, wf)
        return buf.getvalue()

    async def synth(self, text: str) -> tuple[bytes, str]:
        engine = self.engine()
        if engine == "piper":
            return await asyncio.to_thread(self._piper_synth, text), "audio/wav"
        if engine == "elevenlabs":
            key = self.settings.get("voice.elevenlabs_key")
            if not key:
                raise TTSUnavailable("ElevenLabs API key is not set.")
            voice = self.settings.get("voice.elevenlabs_voice")
            r = await self.http.post(f"https://api.elevenlabs.io/v1/text-to-speech/{voice}",
                                     headers={"xi-api-key": key},
                                     json={"text": text, "model_id": "eleven_turbo_v2_5"}, timeout=60)
            r.raise_for_status()
            return r.content, "audio/mpeg"
        raise TTSUnavailable("Browser voice selected; the UI speaks locally.")
