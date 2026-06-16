"""
Azure AI Search integration for FabIQ.

Provides:
  1. Index management    — create the fabiq-docs index
  2. Document ingestion  — upload Chunks with embedding vectors
  3. Hybrid retrieval    — vector + BM25 with RBAC filter
  4. RBAC filtering      — role-based access via OData filter expressions

Role → access level mapping:
  field_engineer    → public
  process_engineer  → public, internal
  admin             → public, internal, restricted
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass

import structlog

logger = structlog.get_logger(__name__)

# ── RBAC ──────────────────────────────────────────────────────────────────────

_ROLE_ACCESS_LEVELS: dict[str, list[str]] = {
    "field_engineer": ["public"],
    "process_engineer": ["public", "internal"],
    "admin": ["public", "internal", "restricted"],
}


def get_access_filter(role: str) -> str:
    """
    Build an OData filter expression for Azure AI Search based on user role.

    Example for 'process_engineer':
        "access_level eq 'public' or access_level eq 'internal'"
    """
    allowed = _ROLE_ACCESS_LEVELS.get(role, ["public"])
    clauses = [f"access_level eq '{level}'" for level in allowed]
    return " or ".join(clauses)


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class SearchResult:
    """A single retrieved chunk with provenance and relevance metadata."""
    chunk_id: str
    doc_id: str
    content: str
    source: str
    page_number: int
    access_level: str
    score: float
    strategy: str
    metadata: dict[str, str]


# ── Client ────────────────────────────────────────────────────────────────────

class FabIQSearchClient:
    """
    Async client wrapping Azure AI Search for FabIQ.

    All heavy Azure imports are deferred to method bodies so the module
    can be imported in tests without Azure credentials installed.
    """

    def __init__(self, settings=None) -> None:
        from fabiq.config import get_settings
        self._cfg = settings or get_settings()

    def _credential(self):
        from azure.core.credentials import AzureKeyCredential
        return AzureKeyCredential(self._cfg.azure_search_api_key)

    def _index_client(self):
        from azure.search.documents.indexes.aio import SearchIndexClient
        return SearchIndexClient(
            endpoint=self._cfg.azure_search_endpoint,
            credential=self._credential(),
        )

    def _search_client(self):
        from azure.search.documents.aio import SearchClient
        return SearchClient(
            endpoint=self._cfg.azure_search_endpoint,
            index_name=self._cfg.azure_search_index_name,
            credential=self._credential(),
        )

    async def ensure_index_exists(self) -> bool:
        """Create the index if it doesn't exist. Returns True if created."""
        from azure.core.exceptions import ResourceNotFoundError
        from azure.search.documents.indexes.models import (
            HnswAlgorithmConfiguration, SearchField, SearchFieldDataType,
            SearchIndex, SemanticConfiguration, SemanticField,
            SemanticPrioritizedFields, SemanticSearch, SimpleField,
            VectorSearch, VectorSearchProfile,
        )

        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
            SimpleField(name="chunk_id", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="doc_id", type=SearchFieldDataType.String, filterable=True),
            SearchField(name="content", type=SearchFieldDataType.String,
                        searchable=True, analyzer_name="en.microsoft"),
            SimpleField(name="source", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="page_number", type=SearchFieldDataType.Int32, filterable=True),
            SimpleField(name="access_level", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="chunk_strategy", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="token_estimate", type=SearchFieldDataType.Int32, filterable=True),
            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=self._cfg.embedding_dimensions,
                vector_search_profile_name="fabiq-vector-profile",
            ),
        ]
        vector_search = VectorSearch(
            algorithms=[HnswAlgorithmConfiguration(name="fabiq-hnsw")],
            profiles=[VectorSearchProfile(
                name="fabiq-vector-profile",
                algorithm_configuration_name="fabiq-hnsw",
            )],
        )
        semantic_config = SemanticConfiguration(
            name="fabiq-semantic",
            prioritized_fields=SemanticPrioritizedFields(
                content_fields=[SemanticField(field_name="content")]
            ),
        )
        index = SearchIndex(
            name=self._cfg.azure_search_index_name,
            fields=fields,
            vector_search=vector_search,
            semantic_search=SemanticSearch(configurations=[semantic_config]),
        )

        async with self._index_client() as idx_client:
            try:
                await idx_client.get_index(self._cfg.azure_search_index_name)
                logger.info("index_exists", index=self._cfg.azure_search_index_name)
                return False
            except ResourceNotFoundError:
                await idx_client.create_index(index)
                logger.info("index_created", index=self._cfg.azure_search_index_name)
                return True

    async def ingest_chunks(self, chunks, embeddings: list[list[float]]) -> int:
        """Upload chunks + embedding vectors to the search index."""
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must have same length")
        documents = [
            {
                "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk.chunk_id)),
                "chunk_id": chunk.chunk_id,
                "doc_id": chunk.doc_id,
                "content": chunk.content,
                "source": chunk.source,
                "page_number": chunk.page_number,
                "access_level": chunk.access_level,
                "chunk_strategy": chunk.strategy,
                "token_estimate": chunk.token_estimate,
                "content_vector": embedding,
            }
            for chunk, embedding in zip(chunks, embeddings)
        ]
        async with self._search_client() as client:
            result = await client.upload_documents(documents=documents)
        succeeded = sum(1 for r in result if r.succeeded)
        logger.info("chunks_ingested", total=len(documents), succeeded=succeeded)
        return succeeded

    async def search(
        self,
        query: str,
        query_embedding: list[float],
        *,
        role: str = "field_engineer",
        top_k: int | None = None,
        extra_filter: str | None = None,
    ) -> list[SearchResult]:
        """Hybrid search with RBAC filter."""
        k = top_k or self._cfg.retrieval_top_k
        access_filter = get_access_filter(role)
        odata_filter = (
            f"({access_filter}) and ({extra_filter})" if extra_filter else f"({access_filter})"
        )
        from azure.search.documents.models import VectorizableTextQuery
        vector_query = VectorizableTextQuery(
            text=query, k_nearest_neighbors=k, fields="content_vector",
            weight=self._cfg.hybrid_vector_weight,
        )
        async with self._search_client() as client:
            raw_results = await client.search(
                search_text=query,
                vector_queries=[vector_query],
                filter=odata_filter,
                top=k,
                select=["chunk_id", "doc_id", "content", "source",
                        "page_number", "access_level", "chunk_strategy"],
                query_type="semantic",
                semantic_configuration_name="fabiq-semantic",
            )
            results: list[SearchResult] = []
            async for r in raw_results:
                results.append(SearchResult(
                    chunk_id=r["chunk_id"], doc_id=r["doc_id"], content=r["content"],
                    source=r["source"], page_number=r.get("page_number", 0),
                    access_level=r["access_level"], score=r.get("@search.score", 0.0),
                    strategy=r.get("chunk_strategy", "unknown"), metadata={},
                ))
        logger.info("hybrid_search_done", results=len(results), role=role)
        return results

    async def delete_document(self, doc_id: str) -> int:
        """Delete all chunks associated with a doc_id."""
        async with self._search_client() as client:
            found = await client.search(
                search_text="*", filter=f"doc_id eq '{doc_id}'",
                select=["id"], top=1000,
            )
            ids_to_delete: list[dict[str, str]] = []
            async for r in found:
                ids_to_delete.append({"id": r["id"]})
            if not ids_to_delete:
                return 0
            result = await client.delete_documents(documents=ids_to_delete)
            return sum(1 for r in result if r.succeeded)
