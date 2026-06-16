"""
Local JSON-backed vector search for FabIQ reviewer/demo mode.

This intentionally mirrors the Azure Search client surface used by the app:
  - ensure_index_exists()
  - ingest_chunks(chunks, embeddings)
  - search(query, query_embedding, role, top_k, extra_filter)
  - delete_document(doc_id)

It does not replace the Azure production path. It is only selected when
APP_MODE=local, so reviewers can run ingestion, retrieval, RBAC filtering,
and citations without Azure credentials or quota.
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any

import structlog

from fabiq.retrieval.search import SearchResult, _ROLE_ACCESS_LEVELS

logger = structlog.get_logger(__name__)


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    dot = sum(a[i] * b[i] for i in range(n))
    mag_a = math.sqrt(sum(x * x for x in a[:n]))
    mag_b = math.sqrt(sum(x * x for x in b[:n]))
    if not mag_a or not mag_b:
        return 0.0
    return dot / (mag_a * mag_b)


class LocalSearchClient:
    """Small local vector store that persists chunks and embeddings to JSON."""

    def __init__(self, settings=None) -> None:
        from fabiq.config import get_settings

        self._cfg = settings or get_settings()
        self.path = Path(self._cfg.local_index_path)

    async def ensure_index_exists(self) -> bool:
        """Create the local index file if it does not exist."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            return False
        self._write({"version": 1, "created_at": time.time(), "documents": []})
        logger.info("local_index_created", path=str(self.path))
        return True

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"version": 1, "created_at": time.time(), "documents": []}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.warning("local_index_corrupt_reinitializing", path=str(self.path))
            return {"version": 1, "created_at": time.time(), "documents": []}

    def _write(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    async def ingest_chunks(self, chunks, embeddings: list[list[float]]) -> int:
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must have same length")
        await self.ensure_index_exists()
        payload = self._read()
        existing = [d for d in payload.get("documents", []) if d.get("doc_id") != chunks[0].doc_id]
        new_docs = []
        for chunk, embedding in zip(chunks, embeddings):
            new_docs.append({
                "chunk_id": chunk.chunk_id,
                "doc_id": chunk.doc_id,
                "content": chunk.content,
                "source": (chunk.metadata or {}).get("filename") or Path(chunk.source).name or chunk.source,
                "page_number": chunk.page_number,
                "access_level": chunk.access_level,
                "chunk_strategy": chunk.strategy,
                "token_estimate": chunk.token_estimate,
                "metadata": chunk.metadata or {},
                "content_vector": embedding,
            })
        payload["documents"] = existing + new_docs
        payload["updated_at"] = time.time()
        self._write(payload)
        logger.info("local_chunks_ingested", total=len(new_docs), path=str(self.path))
        return len(new_docs)

    async def search(
        self,
        query: str,
        query_embedding: list[float],
        *,
        role: str = "field_engineer",
        top_k: int | None = None,
        extra_filter: str | None = None,
    ) -> list[SearchResult]:
        await self.ensure_index_exists()
        k = top_k or self._cfg.retrieval_top_k
        allowed = set(_ROLE_ACCESS_LEVELS.get(role, ["public"]))
        payload = self._read()
        docs = [d for d in payload.get("documents", []) if d.get("access_level", "public") in allowed]

        # Minimal optional filter support for local demo mode. Azure still owns full OData.
        if extra_filter and "source" in extra_filter and "eq" in extra_filter:
            target = extra_filter.split("eq", 1)[1].strip().strip("'\"")
            docs = [d for d in docs if d.get("source") == target]

        scored = []
        terms = {t.lower() for t in query.split() if len(t) > 2}
        for doc in docs:
            vector_score = _cosine(query_embedding, doc.get("content_vector", []))
            content_l = doc.get("content", "").lower()
            keyword_hits = sum(1 for term in terms if term in content_l)
            keyword_score = keyword_hits / max(len(terms), 1)
            score = 0.85 * vector_score + 0.15 * keyword_score
            scored.append((score, doc))

        scored.sort(key=lambda item: item[0], reverse=True)
        results = [
            SearchResult(
                chunk_id=d.get("chunk_id", ""),
                doc_id=d.get("doc_id", ""),
                content=d.get("content", ""),
                source=d.get("source", ""),
                page_number=int(d.get("page_number") or 0),
                access_level=d.get("access_level", "public"),
                score=float(score),
                strategy=d.get("chunk_strategy", "local"),
                metadata=d.get("metadata") or {},
            )
            for score, d in scored[:k]
        ]
        logger.info("local_search_done", results=len(results), role=role, path=str(self.path))
        return results

    async def delete_document(self, doc_id: str) -> int:
        await self.ensure_index_exists()
        payload = self._read()
        before = len(payload.get("documents", []))
        payload["documents"] = [d for d in payload.get("documents", []) if d.get("doc_id") != doc_id]
        removed = before - len(payload["documents"])
        if removed:
            payload["updated_at"] = time.time()
            self._write(payload)
        return removed

    async def get_document_count(self) -> int:
        await self.ensure_index_exists()
        return len(self._read().get("documents", []))
