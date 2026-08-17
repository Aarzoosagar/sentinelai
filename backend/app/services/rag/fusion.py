"""Small, explainable rank fusion for hybrid retrieval."""

from __future__ import annotations


def reciprocal_rank_fusion(*rank_lists: list[str], k: int = 60) -> list[str]:
    """Fuse ranked IDs by RRF: score(id) = sum(1 / (k + rank)).

    RRF combines independently scaled FAISS and BM25 rankings without treating
    their raw scores as comparable. Ties preserve first-seen rank-list order.
    """
    scores: dict[str, float] = {}
    first_seen: dict[str, int] = {}
    sequence = 0
    for rank_list in rank_lists:
        for rank, document_id in enumerate(rank_list, start=1):
            scores[document_id] = scores.get(document_id, 0.0) + 1.0 / (k + rank)
            first_seen.setdefault(document_id, sequence)
            sequence += 1
    return sorted(scores, key=lambda document_id: (-scores[document_id], first_seen[document_id]))
