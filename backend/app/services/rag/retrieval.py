"""Database-authoritative, audit-scoped retrieval and context assembly."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config.settings import get_settings
from app.models.finding import Finding
from app.repositories.audit_repository import AuditSessionRepository
from app.services.rag.embeddings import embed_documents, embed_query
from app.services.rag.fusion import reciprocal_rank_fusion
from app.services.rag.keyword import keyword_search
from app.services.rag.reranker import rerank
from app.services.rag.serializers import finding_to_rag_document
from app.services.rag.vector_store import AuditVectorStore
from app.services.ai.observability import increment, record, timed


@dataclass(frozen=True)
class RetrievedContext:
    findings: list[Finding]


def index_audit_findings(db: Session, audit_session_id: str) -> None:
    """Rebuild an audit's derived index from canonical, persisted findings."""
    findings = list(db.scalars(select(Finding).where(Finding.audit_session_id == audit_session_id)))
    documents = [finding_to_rag_document(finding) for finding in findings]
    embeddings = embed_documents([document.text for document in documents])
    AuditVectorStore(audit_session_id).rebuild(documents, embeddings)


def retrieve(
    db: Session, audit_session_id: str, user_id: str, query: str, *, top_k: int | None = None
) -> RetrievedContext:
    """Hybrid-search one authorized audit and re-hydrate canonical DB findings.

    FAISS and audit-local BM25 each provide candidates. Reciprocal Rank Fusion
    combines their orderings, then the cross-encoder scores only that bounded
    fused set. The SQL query is both the source of candidate documents and the
    final authority for every returned finding.
    """
    if AuditSessionRepository(db).get_for_user(audit_session_id, user_id) is None:
        increment("rag_retrieval_errors_total")
        record("rag_retrieval", status="failure", error_type="authorization_error")
        raise PermissionError("Audit session not found or not accessible")

    settings = get_settings()
    findings = list(db.scalars(select(Finding).where(Finding.audit_session_id == audit_session_id)))
    documents = [finding_to_rag_document(finding) for finding in findings]
    documents_by_id = {document.id: document for document in documents}

    with timed("rag_retrieval", counter="rag_retrieval", audit_session_id=audit_session_id):
        store = AuditVectorStore(audit_session_id)
        store.load()
        semantic_matches = store.search(embed_query(query), settings.rag_semantic_candidate_k)
        semantic_ids = [match["finding_id"] for match in semantic_matches if match["finding_id"] in documents_by_id]
        keyword_ids = [document_id for document_id, _ in keyword_search(documents, query, settings.rag_keyword_candidate_k)]
        fused_ids = reciprocal_rank_fusion(semantic_ids, keyword_ids)[: settings.rag_rerank_candidate_k]
        final_k = top_k or settings.rag_final_top_k
        if settings.rag_rerank_enabled:
            with timed("rag_reranking", counter="rag_reranking", candidate_count=len(fused_ids)):
                finding_ids = rerank(query, [documents_by_id[document_id] for document_id in fused_ids], final_k)
        else:
            finding_ids = fused_ids[:final_k]
        record("rag_candidates", semantic_candidates=len(semantic_ids), keyword_candidates=len(keyword_ids), fused_candidates=len(fused_ids), reranked_candidates=len(finding_ids), final_context=len(finding_ids), top_finding_ids=finding_ids[:5])
    if not finding_ids:
        increment("rag_empty_results_total")
        return RetrievedContext(findings=[])
    canonical = list(
        db.scalars(select(Finding).where(Finding.audit_session_id == audit_session_id, Finding.id.in_(finding_ids)))
    )
    canonical_by_id = {finding.id: finding for finding in canonical}
    return RetrievedContext(findings=[canonical_by_id[finding_id] for finding_id in finding_ids if finding_id in canonical_by_id])
