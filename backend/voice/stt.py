"""Local speech-to-text with faster-whisper (optional dependency)."""
import asyncio
import importlib.util
import io
import wave

import numpy as np


class STT:
    def __init__(self, settings):
        self.settings = settings
        self._model = None
        self._model_name = None

    @staticmethod
    def available() -> bool:
        return importlib.util.find_spec("faster_whisper") is not None

    def _load(self):
        name = self.settings.get("voice.stt_model")
        if self._model is None or self._model_name != name:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(name, device="auto", compute_type="int8")
            self._model_name = name
        return self._model

    @staticmethod
    def wav_to_float(data: bytes) -> np.ndarray:
        with wave.open(io.BytesIO(data)) as w:
            frames = w.readframes(w.getnframes())
            audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
            if w.getnchannels() > 1:
                audio = audio.reshape(-1, w.getnchannels()).mean(axis=1)
            if w.getframerate() != 16000:  # crude resample; the UI already sends 16 kHz
                n = int(len(audio) * 16000 / w.getframerate())
                audio = np.interp(np.linspace(0, len(audio), n, endpoint=False), np.arange(len(audio)), audio)
        return audio.astype(np.float32)

    def _transcribe(self, data: bytes) -> dict:
        model = self._load()
        lang = self.settings.get("assistant.language")
        segments, info = model.transcribe(self.wav_to_float(data), beam_size=1, vad_filter=True,
                                          language=None if lang in (None, "", "auto") else lang[:2].lower())
        return {"text": " ".join(s.text.strip() for s in segments).strip(), "language": info.language}

    async def transcribe(self, data: bytes) -> dict:
        return await asyncio.to_thread(self._transcribe, data)
