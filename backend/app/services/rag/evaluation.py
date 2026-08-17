"""Repeatable, local retrieval evaluation for SentinelAI's RAG components."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

import faiss
import numpy as np

from app.services.rag.embeddings import embed_documents, embed_query
from app.services.rag.fusion import reciprocal_rank_fusion
from app.services.rag.keyword import keyword_search
from app.services.rag.reranker import rerank
from app.services.rag.serializers import RagDocument

DATASET_PATH = Path(__file__).with_name("evaluation_dataset.json")
TOP_KS = (1, 3, 5)
FINAL_TOP_K = 5
SEMANTIC_CANDIDATE_K = 10
KEYWORD_CANDIDATE_K = 10
RERANK_CANDIDATE_K = 15


@dataclass(frozen=True)
class EvaluationCase:
    query: str
    relevant_finding_ids: tuple[str, ...]


def load_dataset(path: Path = DATASET_PATH) -> tuple[list[RagDocument], list[EvaluationCase]]:
    """Load stable, SentinelAI-style fixtures without touching production data."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    documents = [RagDocument(item["id"], item["text"], {"service": item["service"]}) for item in raw["findings"]]
    cases = [EvaluationCase(item["query"], tuple(item["relevant_finding_ids"])) for item in raw["cases"]]
    return documents, cases


def first_relevant_rank(retrieved_ids: Iterable[str], relevant_ids: Iterable[str]) -> int | None:
    relevant = set(relevant_ids)
    return next((rank for rank, document_id in enumerate(retrieved_ids, start=1) if document_id in relevant), None)


def metrics_for_query(retrieved_ids: list[str], relevant_ids: Iterable[str], k: int) -> dict[str, float | bool]:
    """Calculate set-aware Hit@K and Recall@K for a single query."""
    relevant = set(relevant_ids)
    retrieved = set(retrieved_ids[:k])
    matches = len(relevant & retrieved)
    return {"hit": bool(matches), "recall": matches / len(relevant) if relevant else 0.0}


def aggregate_metrics(records: list[dict[str, object]]) -> dict[str, float]:
    """Average per-query Hit/Recall and MRR; every query retains all relevant IDs."""
    if not records:
        return {**{f"hit_at_{k}": 0.0 for k in TOP_KS}, **{f"recall_at_{k}": 0.0 for k in TOP_KS}, "mrr": 0.0}
    totals: dict[str, float] = {f"hit_at_{k}": 0.0 for k in TOP_KS} | {f"recall_at_{k}": 0.0 for k in TOP_KS} | {"mrr": 0.0}
    for record in records:
        rank = record["first_relevant_rank"]
        totals["mrr"] += 1 / rank if isinstance(rank, int) else 0.0
        for k in TOP_KS:
            totals[f"hit_at_{k}"] += float(record[f"hit_at_{k}"])
            totals[f"recall_at_{k}"] += float(record[f"recall_at_{k}"])
    return {key: value / len(records) for key, value in totals.items()}


def evaluate_rankings(cases: list[EvaluationCase], rankings: dict[str, list[list[str]]]) -> dict[str, object]:
    """Evaluate supplied rankings, enabling fast deterministic unit tests."""
    systems: dict[str, object] = {}
    for system, per_query_ids in rankings.items():
        if len(per_query_ids) != len(cases):
            raise ValueError(f"{system} rankings do not match the evaluation dataset")
        records: list[dict[str, object]] = []
        for case, retrieved_ids in zip(cases, per_query_ids, strict=True):
            rank = first_relevant_rank(retrieved_ids, case.relevant_finding_ids)
            record: dict[str, object] = {
                "query": case.query,
                "system": system,
                "retrieved_finding_ids": retrieved_ids,
                "relevant_finding_ids": list(case.relevant_finding_ids),
                "first_relevant_rank": rank,
            }
            for k in TOP_KS:
                values = metrics_for_query(retrieved_ids, case.relevant_finding_ids, k)
                record[f"hit_at_{k}"] = values["hit"]
                record[f"recall_at_{k}"] = values["recall"]
            records.append(record)
        failures = [record for record in records if not record["hit_at_5"]]
        systems[system] = {"metrics": aggregate_metrics(records), "per_query": records, "failures": failures}
    best = max(systems, key=lambda name: (systems[name]["metrics"]["mrr"], systems[name]["metrics"]["hit_at_5"])) if systems else None
    return {"dataset_queries": len(cases), "systems": systems, "best_configuration": best}


def _semantic_ranker(documents: list[RagDocument]) -> Callable[[str], tuple[list[str], dict[str, float]]]:
    embeddings = embed_documents([document.text for document in documents])
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)

    def rank(query: str) -> tuple[list[str], dict[str, float]]:
        scores, indexes = index.search(embed_query(query), min(SEMANTIC_CANDIDATE_K, len(documents)))
        pairs = [(documents[int(idx)].id, float(score)) for score, idx in zip(scores[0], indexes[0], strict=True) if idx >= 0]
        return [document_id for document_id, _ in pairs], dict(pairs)

    return rank


def run_evaluation() -> dict[str, object]:
    """Run FAISS, hybrid, and hybrid-plus-reranking over the same fixed corpus."""
    documents, cases = load_dataset()
    documents_by_id = {document.id: document for document in documents}
    semantic_rank = _semantic_ranker(documents)
    rankings: dict[str, list[list[str]]] = {"FAISS": [], "Hybrid": [], "Hybrid + Reranking": []}
    semantic_scores: list[dict[str, float]] = []
    for case in cases:
        semantic_ids, scores = semantic_rank(case.query)
        keyword_ids = [document_id for document_id, _ in keyword_search(documents, case.query, KEYWORD_CANDIDATE_K)]
        hybrid_ids = reciprocal_rank_fusion(semantic_ids, keyword_ids)[:RERANK_CANDIDATE_K]
        reranked_ids = rerank(case.query, [documents_by_id[document_id] for document_id in hybrid_ids], FINAL_TOP_K)
        rankings["FAISS"].append(semantic_ids[:FINAL_TOP_K])
        rankings["Hybrid"].append(hybrid_ids[:FINAL_TOP_K])
        rankings["Hybrid + Reranking"].append(reranked_ids)
        semantic_scores.append(scores)
    report = evaluate_rankings(cases, rankings)
    for result in report["systems"].values():
        for record, scores in zip(result["per_query"], semantic_scores, strict=True):
            record["semantic_scores"] = scores
        for failure in result["failures"]:
            failure["relevant_services"] = [documents_by_id[item].metadata["service"] for item in failure["relevant_finding_ids"]]
    return report


def _summary(report: dict[str, object]) -> str:
    lines = ["SentinelAI RAG Evaluation", "=" * 26, f"Dataset: {report['dataset_queries']} queries", ""]
    for system, result in report["systems"].items():
        metrics = result["metrics"]
        metric_labels = {
            "hit_at_1": "Hit@1", "hit_at_3": "Hit@3", "hit_at_5": "Hit@5",
            "recall_at_1": "Recall@1", "recall_at_3": "Recall@3", "recall_at_5": "Recall@5",
        }
        lines.extend([system, *[f"{metric_labels[name]}: {metrics[name]:.3f}" for name in metric_labels], f"MRR: {metrics['mrr']:.3f}", f"Failures (Hit@5=0): {len(result['failures'])}", ""])
    lines.append(f"Best configuration: {report['best_configuration']}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate SentinelAI RAG retrieval locally.")
    parser.add_argument("--output", type=Path, default=Path("rag_evaluation_report.json"), help="JSON report path")
    args = parser.parse_args()
    report = run_evaluation()
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(_summary(report))
    print(f"JSON report: {args.output}")


if __name__ == "__main__":
    main()
