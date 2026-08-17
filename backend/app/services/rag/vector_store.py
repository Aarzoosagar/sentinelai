"""Per-audit FAISS indices; the SQL database remains authoritative."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

import faiss
import numpy as np

from app.core.config.settings import get_settings
from app.services.rag.serializers import RagDocument


class VectorStoreError(RuntimeError):
    pass


class AuditVectorStore:
    """One physical index per audit, so searches cannot cross audit boundaries."""

    def __init__(self, audit_session_id: str, index_dir: str | Path | None = None):
        self.audit_session_id = audit_session_id
        self.root = Path(index_dir or get_settings().rag_index_dir) / audit_session_id
        self.index_path = self.root / "findings.faiss"
        self.metadata_path = self.root / "findings.json"
        self.index: faiss.IndexIDMap2 | None = None
        self.metadata: dict[str, dict[str, Any]] = {}

    def load(self) -> None:
        if not self.index_path.exists() and not self.metadata_path.exists():
            return
        if not self.metadata_path.exists():
            raise VectorStoreError("RAG index and metadata are out of sync; rebuild this audit index")
        self.metadata = json.loads(self.metadata_path.read_text(encoding="utf-8"))
        # A successfully rebuilt audit with no findings deliberately persists
        # empty metadata and no FAISS file.
        if not self.index_path.exists():
            if self.metadata:
                raise VectorStoreError("RAG index and metadata are out of sync; rebuild this audit index")
            return
        self.index = faiss.read_index(str(self.index_path))
        if self.index.ntotal != len(self.metadata):
            raise VectorStoreError("RAG index and metadata counts differ; rebuild this audit index")

    def rebuild(self, documents: list[RagDocument], embeddings: np.ndarray) -> None:
        self.index = None
        self.metadata = {}
        self.add(documents, embeddings, persist=False)
        self.persist()

    def add(self, documents: list[RagDocument], embeddings: np.ndarray, *, persist: bool = True) -> None:
        if len(documents) != len(embeddings):
            raise VectorStoreError("Documents and embeddings must have the same length")
        if not documents:
            if persist:
                self.persist()
            return
        dim = int(embeddings.shape[1])
        if self.index is None:
            self.index = faiss.IndexIDMap2(faiss.IndexFlatIP(dim))
        if self.index.d != dim:
            raise VectorStoreError("Embedding dimension differs from the existing index")
        if len({doc.id for doc in documents}) != len(documents):
            raise VectorStoreError("Duplicate document IDs in a single update")
        self.delete([doc.id for doc in documents], persist=False)
        vector_ids = np.asarray([self._vector_id(doc.id) for doc in documents], dtype=np.int64)
        self.index.add_with_ids(np.asarray(embeddings, dtype=np.float32), vector_ids)
        for doc, vector_id in zip(documents, vector_ids, strict=True):
            self.metadata[doc.id] = {"vector_id": int(vector_id), **doc.metadata}
        if persist:
            self.persist()

    def delete(self, document_ids: list[str], *, persist: bool = True) -> None:
        if self.index is not None:
            ids = [self.metadata[doc_id]["vector_id"] for doc_id in document_ids if doc_id in self.metadata]
            if ids:
                self.index.remove_ids(np.asarray(ids, dtype=np.int64))
        for doc_id in document_ids:
            self.metadata.pop(doc_id, None)
        if persist:
            self.persist()

    def search(self, query_embedding: np.ndarray, top_k: int) -> list[dict[str, Any]]:
        if self.index is None or self.index.ntotal == 0:
            return []
        scores, ids = self.index.search(np.asarray(query_embedding, dtype=np.float32), min(top_k, self.index.ntotal))
        by_vector_id = {item["vector_id"]: {"document_id": doc_id, **item} for doc_id, item in self.metadata.items()}
        return [
            {**by_vector_id[int(vector_id)], "score": float(score)}
            for score, vector_id in zip(scores[0], ids[0], strict=True)
            if int(vector_id) >= 0 and int(vector_id) in by_vector_id
        ]

    def persist(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self._atomic_json(self.metadata_path, self.metadata)
        if self.index is None:
            self.index_path.unlink(missing_ok=True)
            return
        with NamedTemporaryFile(dir=self.root, suffix=".faiss", delete=False) as tmp:
            tmp_name = tmp.name
        try:
            faiss.write_index(self.index, tmp_name)
            os.replace(tmp_name, self.index_path)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)

    @staticmethod
    def _vector_id(document_id: str) -> int:
        return int.from_bytes(hashlib.sha256(document_id.encode()).digest()[:8], "big") & ((1 << 63) - 1)

    @staticmethod
    def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
        with NamedTemporaryFile(dir=path.parent, suffix=".json", mode="w", encoding="utf-8", delete=False) as tmp:
            json.dump(payload, tmp, sort_keys=True)
            tmp_name = tmp.name
        try:
            os.replace(tmp_name, path)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
