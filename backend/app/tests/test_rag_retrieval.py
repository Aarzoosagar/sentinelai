"""Focused tests for derived, audit-isolated FAISS retrieval."""

from __future__ import annotations

import numpy as np
import pytest
from types import SimpleNamespace

from app.models.audit_session import AuditSession
from app.models.aws_account import AwsAccount
from app.models.enums import AuditStatus, AwsAuthMethod, AwsService, Severity
from app.models.finding import Finding
from app.models.user import User
from app.services.rag import retrieval
from app.services.rag.keyword import keyword_search
from app.services.rag.reranker import rerank
from app.services.rag.serializers import RagDocument
from app.services.rag.vector_store import AuditVectorStore


def test_index_persists_replaces_rebuilds_and_handles_empty(tmp_path):
    store = AuditVectorStore("audit-a", tmp_path)
    first = RagDocument("finding-1", "public bucket", {"finding_id": "finding-1", "audit_session_id": "audit-a"})
    store.rebuild([first], np.array([[1.0, 0.0]], dtype=np.float32))
    reloaded = AuditVectorStore("audit-a", tmp_path)
    reloaded.load()
    assert reloaded.search(np.array([[1.0, 0.0]], dtype=np.float32), 5)[0]["finding_id"] == "finding-1"
    replacement = RagDocument("finding-1", "fixed bucket", {"finding_id": "finding-1", "audit_session_id": "audit-a"})
    reloaded.add([replacement], np.array([[0.0, 1.0]], dtype=np.float32))
    assert reloaded.search(np.array([[0.0, 1.0]], dtype=np.float32), 5)[0]["finding_id"] == "finding-1"
    reloaded.rebuild([], np.empty((0, 2), dtype=np.float32))
    empty = AuditVectorStore("audit-a", tmp_path)
    empty.load()
    assert empty.search(np.array([[1.0, 0.0]], dtype=np.float32), 5) == []


def test_retrieval_is_audit_scoped_and_top_k(monkeypatch, tmp_path, db_session):
    user = User(email="rag@test.io", hashed_password="x", full_name="RAG")
    db_session.add(user); db_session.flush()
    account = AwsAccount(user_id=user.id, account_alias="a", aws_account_id="1", region="us-east-1", auth_method=AwsAuthMethod.ASSUME_ROLE, role_arn="arn")
    db_session.add(account); db_session.flush()
    audit_a = AuditSession(aws_account_id=account.id, status=AuditStatus.COMPLETED)
    audit_b = AuditSession(aws_account_id=account.id, status=AuditStatus.COMPLETED)
    db_session.add_all([audit_a, audit_b]); db_session.flush()
    relevant = Finding(audit_session_id=audit_a.id, service=AwsService.S3, title="Public bucket", description="public access", severity=Severity.CRITICAL, remediation="block")
    irrelevant = Finding(audit_session_id=audit_a.id, service=AwsService.KMS, title="Rotation", description="rotation disabled", severity=Severity.LOW, remediation="enable")
    other = Finding(audit_session_id=audit_b.id, service=AwsService.IAM, title="Other audit", description="admin policy", severity=Severity.HIGH, remediation="restrict")
    db_session.add_all([relevant, irrelevant, other]); db_session.flush()
    monkeypatch.setattr(retrieval, "embed_documents", lambda docs: np.array([[1., 0.], [0., 1.]], dtype=np.float32))
    monkeypatch.setattr(retrieval, "embed_query", lambda query: np.array([[1., 0.]], dtype=np.float32))
    monkeypatch.setattr(retrieval, "AuditVectorStore", lambda audit_id: AuditVectorStore(audit_id, tmp_path))
    retrieval.index_audit_findings(db_session, audit_a.id)
    result = retrieval.retrieve(db_session, audit_a.id, user.id, "public", top_k=1)
    assert [finding.id for finding in result.findings] == [relevant.id]
    assert all(finding.audit_session_id == audit_a.id for finding in result.findings)
    with pytest.raises(PermissionError):
        retrieval.retrieve(db_session, audit_a.id, "not-the-user", "public")


def test_keyword_search_matches_security_terms():
    s3 = RagDocument("s3", "AWS service: s3\nTitle: Public S3 bucket\nCIS control: 2.1.5", {})
    iam = RagDocument("iam", "AWS service: iam\nTitle: Overly permissive IAM policy\nNIST control: AC-6", {})
    assert keyword_search([s3, iam], "S3 public access", 2)[0][0] == "s3"
    assert keyword_search([s3, iam], "IAM NIST", 2)[0][0] == "iam"
    assert keyword_search([s3, iam], "CIS 2.1.5", 2)[0][0] == "s3"


def test_hybrid_retrieval_surfaces_bm25_candidate_missed_by_semantic(monkeypatch, db_session):
    user = User(email="hybrid@test.io", hashed_password="x", full_name="Hybrid")
    db_session.add(user); db_session.flush()
    account = AwsAccount(user_id=user.id, account_alias="h", aws_account_id="2", region="us-east-1", auth_method=AwsAuthMethod.ASSUME_ROLE, role_arn="arn")
    db_session.add(account); db_session.flush()
    audit = AuditSession(aws_account_id=account.id, status=AuditStatus.COMPLETED)
    db_session.add(audit); db_session.flush()
    s3 = Finding(audit_session_id=audit.id, service=AwsService.S3, title="Public S3 bucket", description="public access", severity=Severity.CRITICAL, remediation="block")
    iam = Finding(audit_session_id=audit.id, service=AwsService.IAM, title="IAM policy", description="permissions", severity=Severity.HIGH, remediation="restrict")
    db_session.add_all([s3, iam]); db_session.flush()

    class SemanticMissStore:
        def __init__(self, audit_id): pass
        def load(self): pass
        def search(self, query, top_k): return [{"finding_id": iam.id, "score": 0.9}]

    monkeypatch.setattr(retrieval, "AuditVectorStore", SemanticMissStore)
    monkeypatch.setattr(retrieval, "embed_query", lambda query: np.array([[1.0]], dtype=np.float32))
    monkeypatch.setattr(retrieval, "get_settings", lambda: SimpleNamespace(rag_semantic_candidate_k=10, rag_keyword_candidate_k=10, rag_rerank_candidate_k=10, rag_final_top_k=2, rag_rerank_enabled=False))
    result = retrieval.retrieve(db_session, audit.id, user.id, "S3 public access")
    assert s3.id in [finding.id for finding in result.findings]


def test_reranker_can_change_fused_candidate_order(monkeypatch):
    first = RagDocument("first", "weak match", {})
    second = RagDocument("second", "strong match", {})

    class FakeCrossEncoder:
        def rerank(self, query, documents): return [0.1, 2.0]

    monkeypatch.setattr("app.services.rag.reranker.get_reranker", lambda: FakeCrossEncoder())
    assert rerank("query", [first, second], 2) == ["second", "first"]


def test_retrieval_rejects_cross_audit_candidate_before_canonical_revalidation(monkeypatch, db_session):
    user = User(email="isolation@test.io", hashed_password="x", full_name="Isolation")
    db_session.add(user); db_session.flush()
    account = AwsAccount(user_id=user.id, account_alias="i", aws_account_id="3", region="us-east-1", auth_method=AwsAuthMethod.ASSUME_ROLE, role_arn="arn")
    db_session.add(account); db_session.flush()
    audit_a = AuditSession(aws_account_id=account.id, status=AuditStatus.COMPLETED)
    audit_b = AuditSession(aws_account_id=account.id, status=AuditStatus.COMPLETED)
    db_session.add_all([audit_a, audit_b]); db_session.flush()
    allowed = Finding(audit_session_id=audit_a.id, service=AwsService.S3, title="Allowed", description="public S3 access", severity=Severity.HIGH, remediation="block")
    foreign = Finding(audit_session_id=audit_b.id, service=AwsService.IAM, title="Foreign", description="IAM admin", severity=Severity.HIGH, remediation="restrict")
    db_session.add_all([allowed, foreign]); db_session.flush()

    class UnsafeStore:
        def __init__(self, audit_id): pass
        def load(self): pass
        def search(self, query, top_k): return [{"finding_id": foreign.id, "score": 1.0}, {"finding_id": allowed.id, "score": 0.5}]

    monkeypatch.setattr(retrieval, "AuditVectorStore", UnsafeStore)
    monkeypatch.setattr(retrieval, "embed_query", lambda query: np.array([[1.0]], dtype=np.float32))
    monkeypatch.setattr(retrieval, "get_settings", lambda: SimpleNamespace(rag_semantic_candidate_k=10, rag_keyword_candidate_k=0, rag_rerank_candidate_k=10, rag_final_top_k=2, rag_rerank_enabled=False))
    result = retrieval.retrieve(db_session, audit_a.id, user.id, "public S3")
    assert [finding.id for finding in result.findings] == [allowed.id]
