"""本機 Embedding（sentence-transformers + BGE-M3，離線、零成本）。"""
from __future__ import annotations

import numpy as np

import config

_model = None


def get_model():
    global _model
    if _model is None:
        # 延遲匯入（較重依賴）；首次會下載模型（約 2GB）後走本機快取
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(config.EMBEDDING_MODEL)
    return _model


def embed(texts: list[str]) -> np.ndarray:
    """回傳正規化後的向量，cosine similarity = 內積。"""
    return get_model().encode(texts, normalize_embeddings=True, show_progress_bar=False)


def warmup() -> None:
    """預先載入模型並做一次前向，把冷啟動延遲移到 app 啟動時。"""
    get_model().encode(["warmup"], normalize_embeddings=True, show_progress_bar=False)
