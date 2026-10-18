"""'Hey Jarvis' wake word detection with openWakeWord (optional dependency)."""
import importlib.util

import numpy as np

FRAME = 1280  # 80 ms at 16 kHz


class WakeWord:
    def __init__(self, threshold: float = 0.5):
        self.threshold = threshold
        self._model = None
        self._buf = np.zeros(0, dtype=np.int16)

    @staticmethod
    def available() -> bool:
        return importlib.util.find_spec("openwakeword") is not None

    def _load(self):
        if self._model is None:
            import openwakeword
            from openwakeword.model import Model
            try:
                self._model = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")
            except Exception:
                openwakeword.utils.download_models(["hey_jarvis"])
                self._model = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")
        return self._model

    def feed(self, pcm16: bytes) -> bool:
        """Feed raw 16 kHz mono int16 audio; returns True when the wake word is heard."""
        model = self._load()
        self._buf = np.concatenate([self._buf, np.frombuffer(pcm16, dtype=np.int16)])
        hit = False
        while len(self._buf) >= FRAME:
            frame, self._buf = self._buf[:FRAME], self._buf[FRAME:]
            scores = model.predict(frame)
            if any(v >= self.threshold for v in scores.values()):
                hit = True
                model.reset()
        return hit
