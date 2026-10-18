"""Long-term memory: facts about the user, embedded locally and recalled by similarity.

The default embedder is a dependency-free hashing vectoriser (word + bigram features),
so memory works offline with no model download.
"""
import hashlib
import math
import re

from .. import db
from ..db import MemoryFact

DIM = 512
_WORD = re.compile(r"[a-z0-9']+")
_STOP = set("a an the is are was were i my me to of and or in on at for it that this be with as by you your".split())


def embed(text: str) -> list[float]:
    words = [w for w in _WORD.findall(text.lower()) if w not in _STOP]
    feats = words + [f"{a}_{b}" for a, b in zip(words, words[1:])]
    vec = [0.0] * DIM
    for f in feats:
        h = int(hashlib.md5(f.encode()).hexdigest(), 16)
        vec[h % DIM] += 1.0 if (h >> 9) & 1 else -1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


class MemoryStore:
    def add(self, text: str) -> dict:
        with db.session() as s:
            fact = MemoryFact(text=text.strip(), vector=embed(text))
            s.add(fact)
            s.flush()
            return {"id": fact.id, "text": fact.text}

    def search(self, query: str, k: int = 5, min_score: float = 0.1) -> list[dict]:
        q = embed(query)
        with db.session() as s:
            scored = [(cosine(q, f.vector), f) for f in s.query(MemoryFact).all()]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [{"id": f.id, "text": f.text, "score": round(sc, 3)} for sc, f in scored[:k] if sc >= min_score]

    def list(self) -> list[dict]:
        with db.session() as s:
            return [{"id": f.id, "text": f.text, "created_at": f.created_at.isoformat()}
                    for f in s.query(MemoryFact).order_by(MemoryFact.id.desc()).all()]

    def update(self, fid: int, text: str) -> bool:
        with db.session() as s:
            f = s.get(MemoryFact, fid)
            if not f:
                return False
            f.text, f.vector = text, embed(text)
            return True

    def delete(self, fid: int) -> bool:
        with db.session() as s:
            f = s.get(MemoryFact, fid)
            if f:
                s.delete(f)
            return f is not None
