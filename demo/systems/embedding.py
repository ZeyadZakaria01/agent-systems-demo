"""MiniLM unit vectors, shared by the in-process systems (the versioned row, the reference GEM): one model load and one
text -> vector cache per process, so a text is embedded once however many systems or ramps ask for it."""

from __future__ import annotations

import numpy as np

MODEL = "sentence-transformers/all-MiniLM-L6-v2"

_embedder = None
_vectors: dict[str, np.ndarray] = {}


def unit_vectors(texts: list[str]) -> np.ndarray:
    """One unit vector per text (rows in the order given); texts not seen before are embedded in one batch."""
    global _embedder
    missing = [t for t in dict.fromkeys(texts) if t not in _vectors]
    if missing:
        if _embedder is None:
            from fastembed import TextEmbedding

            _embedder = TextEmbedding(model_name=MODEL)
        for text, v in zip(missing, _embedder.embed([t if t.strip() else " " for t in missing])):
            v = np.asarray(v, dtype=np.float64)
            _vectors[text] = v / (np.linalg.norm(v) or 1.0)
    return np.stack([_vectors[t] for t in texts]) if texts else np.zeros((0, 0))


def unit_vector(text: str) -> np.ndarray:
    return unit_vectors([text])[0]
