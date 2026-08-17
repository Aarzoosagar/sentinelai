"""Audit-local BM25 keyword retrieval for the hybrid RAG first stage."""

from __future__ import annotations

import re

from rank_bm25 import BM25Plus

from app.services.rag.serializers import RagDocument

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_.:-]*")


def tokenize(text: str) -> list[str]:
    """Keep security identifiers such as S3, CIS 2.1.5, and SSH searchable."""
    return _TOKEN_RE.findall(text.lower())


def keyword_search(documents: list[RagDocument], query: str, top_k: int) -> list[tuple[str, float]]:
    """Return document IDs ranked by BM25, never across audit boundaries."""
    if not documents or top_k < 1:
        return []
    query_tokens = tokenize(query)
    if not query_tokens:
        return []
    tokenized_documents = [tokenize(document.text) for document in documents]
    # BM25Plus avoids negative IDF values in very small audit corpora. Retain
    # only true lexical matches so its additive delta never surfaces unrelated
    # documents merely because the audit has few findings.
    scores = BM25Plus(tokenized_documents).get_scores(query_tokens)
    ranked = sorted(zip(documents, tokenized_documents, scores, strict=True), key=lambda item: float(item[2]), reverse=True)
    query_terms = set(query_tokens)
    return [
        (document.id, float(score))
        for document, document_tokens, score in ranked
        if query_terms.intersection(document_tokens)
    ][:top_k]
