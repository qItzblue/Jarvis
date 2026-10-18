"""Settings store: values saved from the UI (SQLite) win over environment variables."""
import os

from .. import db
from ..db import Setting

# Core (non-plugin) settings shown in the Settings tab.
CORE_SCHEMA: dict[str, dict] = {
    "llm.provider": {"label": "AI provider", "type": "select", "options": ["anthropic", "nanogpt", "gemini"],
                     "env": "JARVIS_LLM_PROVIDER", "default": "anthropic"},
    "anthropic.api_key": {"label": "Anthropic API key", "type": "string", "secret": True, "env": "ANTHROPIC_API_KEY"},
    "anthropic.model": {"label": "Claude model", "type": "string", "default": "claude-sonnet-5-5"},
    "nanogpt.api_key": {"label": "NanoGPT API key", "type": "string", "secret": True, "env": "NANOGPT_API_KEY"},
    "nanogpt.model": {"label": "NanoGPT model", "type": "string", "default": "gpt-4o-mini"},
    "google.api_key": {"label": "Google API key (Gemini)", "type": "string", "secret": True, "env": "GOOGLE_API_KEY"},
    "gemini.model": {"label": "Gemini model", "type": "string", "default": "gemini-2.5-flash"},
    "assistant.name": {"label": "Assistant name", "type": "string", "default": "Jarvis"},
    "assistant.user_name": {"label": "What Jarvis calls you", "type": "string", "default": "sir"},
    "assistant.personality": {"label": "Personality", "type": "text",
                              "default": "Calm, witty and concise, like a loyal British butler. Dry humour, never rude."},
    "assistant.verbosity": {"label": "Verbosity (1 terse – 5 chatty)", "type": "number", "default": 2},
    "assistant.language": {"label": "Reply language", "type": "string", "default": "auto"},
    "voice.wake_word": {"label": "Wake word enabled", "type": "boolean", "default": False},
    "voice.stt_model": {"label": "Whisper model", "type": "select",
                        "options": ["tiny.en", "base.en", "small.en", "base", "small", "medium"], "default": "base.en"},
    "voice.tts_engine": {"label": "Voice engine", "type": "select", "options": ["browser", "piper", "elevenlabs"],
                         "default": "browser"},
    "voice.piper_model": {"label": "Piper voice model (.onnx path)", "type": "string", "env": "PIPER_MODEL_PATH"},
    "voice.elevenlabs_key": {"label": "ElevenLabs API key", "type": "string", "secret": True, "env": "ELEVENLABS_API_KEY"},
    "voice.elevenlabs_voice": {"label": "ElevenLabs voice ID", "type": "string", "default": "pNInz6obpgDQGcFmaJgB"},
    "voice.speed": {"label": "Speaking speed", "type": "number", "default": 1.0},
    "ui.theme": {"label": "Theme", "type": "select", "options": ["dark", "light"], "default": "dark"},
    "ui.reduced_motion": {"label": "Reduce motion", "type": "boolean", "default": False},
}


def mask(value) -> str:
    s = str(value or "")
    return "" if not s else ("•" * 8 + s[-4:] if len(s) > 4 else "•" * len(s))


class Settings:
    def __init__(self):
        self._cache: dict[str, object] = {}
        self._loaded = False

    def _load(self):
        if not self._loaded:
            with db.session() as s:
                self._cache = {row.key: row.value for row in s.query(Setting).all()}
            self._loaded = True

    def get(self, key: str, default=None, env: str | None = None):
        self._load()
        val = self._cache.get(key)
        if val not in (None, ""):
            return val
        schema = CORE_SCHEMA.get(key, {})
        env = env or schema.get("env")
        if env and os.getenv(env):
            return os.getenv(env)
        return schema.get("default", default) if default is None else default

    def set(self, key: str, value) -> None:
        self._load()
        with db.session() as s:
            row = s.get(Setting, key)
            if row is None:
                s.add(Setting(key=key, value=value))
            else:
                row.value = value
        self._cache[key] = value

    def core_view(self) -> list[dict]:
        out = []
        for key, sch in CORE_SCHEMA.items():
            val = self.get(key)
            out.append({"key": key, **sch, "value": mask(val) if sch.get("secret") else val,
                        "is_set": val not in (None, "")})
        return out
