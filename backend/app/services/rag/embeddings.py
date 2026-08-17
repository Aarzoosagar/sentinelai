"""Cached local FastEmbed embeddings for RAG.

BAAI/bge-small-en-v1.5 is a compact English model (384 dimensions, roughly
67 MB of model files) suitable for AWS/security finding retrieval. FastEmbed
uses ONNX Runtime, so this embedding path does not require PyTorch or TensorFlow.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np
from fastembed import TextEmbedding

from app.core.config.settings import get_settings


class EmbeddingServiceError(RuntimeError):
    """Raised when the local embedding model cannot produce usable vectors."""


@lru_cache(maxsize=1)
def get_embedding_model() -> TextEmbedding:
    try:
        settings = get_settings()
        return TextEmbedding(
            model_name=settings.rag_embedding_model,
            cache_dir=settings.fastembed_cache_dir,
        )
    except Exception as exc:  # pragma: no cover - model/runtime dependent
        raise EmbeddingServiceError("Unable to load the configured embedding model") from exc


def embed_documents(documents: list[str]) -> np.ndarray:
    return _embed(documents, prefix="passage: ")


def embed_query(query: str) -> np.ndarray:
    if not query.strip():
        raise EmbeddingServiceError("A non-empty query is required for retrieval")
    return _embed([query], prefix="query: ")


def _embed(texts: list[str], *, prefix: str) -> np.ndarray:
    if not texts:
        return np.empty((0, 0), dtype=np.float32)
    try:
        vectors = np.asarray(list(get_embedding_model().embed([f"{prefix}{text}" for text in texts])), dtype=np.float32)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        if np.any(norms == 0):
            raise EmbeddingServiceError("Embedding model returned a zero-length vector")
        return vectors / norms
    except EmbeddingServiceError:
        raise
    except Exception as exc:  # pragma: no cover - model/runtime dependent
        raise EmbeddingServiceError("Unable to generate embeddings") from exc
