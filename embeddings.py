"""Local embeddings (sentence-transformers, offline & free)."""
from __future__ import annotations

import numpy as np

import config

_model = None


def get_model():
    global _model
    if _model is None:
        # lazy import (heavy dependency); first call downloads the model (~2GB) then caches it locally
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(config.EMBEDDING_MODEL)
    return _model


def embed(texts: list[str]) -> np.ndarray:
    """Return normalized vectors; cosine similarity = dot product."""
    return get_model().encode(texts, normalize_embeddings=True, show_progress_bar=False)


def warmup() -> None:
    """Preload the model and run one forward pass so cold start happens at app startup."""
    get_model().encode(["warmup"], normalize_embeddings=True, show_progress_bar=False)
