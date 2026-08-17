"""Cached FastEmbed cross-encoder reranking for a small candidate set only."""

from __future__ import annotations

from functools import lru_cache

from fastembed.rerank.cross_encoder import TextCrossEncoder

from app.core.config.settings import get_settings
from app.services.rag.serializers import RagDocument


class RerankerError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def get_reranker() -> TextCrossEncoder:
    try:
        return TextCrossEncoder(model_name=get_settings().rag_reranker_model)
    except Exception as exc:  # pragma: no cover - model/runtime dependent
        raise RerankerError("Unable to load the configured RAG reranker") from exc


def rerank(query: str, documents: list[RagDocument], top_k: int) -> list[str]:
    """Return IDs ordered by cross-encoder relevance; callers cap candidates first."""
    if not documents or top_k < 1:
        return []
    try:
        scores = list(get_reranker().rerank(query, [document.text for document in documents]))
    except RerankerError:
        raise
    except Exception as exc:  # pragma: no cover - model/runtime dependent
        raise RerankerError("Unable to rerank RAG candidates") from exc
    ranked = sorted(zip(documents, scores, strict=True), key=lambda item: float(item[1]), reverse=True)
    return [document.id for document, _ in ranked[:top_k]]
