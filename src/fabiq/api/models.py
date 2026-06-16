from __future__ import annotations
from typing import Annotated, Literal
from pydantic import BaseModel, Field

Role = Literal["field_engineer", "process_engineer", "admin"]
ChunkStrategy = Literal["fixed", "recursive", "semantic"]
AccessLevel = Literal["public", "internal", "restricted"]

class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    version: str
    app_mode: Literal["azure", "local"] = "azure"
    index_reachable: bool
    openai_reachable: bool
    message: str = ""

class IngestRequest(BaseModel):
    access_level: AccessLevel = "public"
    chunk_strategy: ChunkStrategy = "recursive"
    chunk_size: Annotated[int, Field(ge=64, le=4096)] = 512
    chunk_overlap: Annotated[int, Field(ge=0, le=512)] = 64
    extra_metadata: dict[str, str] = Field(default_factory=dict)

class IngestResponse(BaseModel):
    doc_id: str
    filename: str
    chunks_indexed: int
    strategy_used: ChunkStrategy
    access_level: AccessLevel
    elapsed_ms: float

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=2000)
    role: Role = "field_engineer"
    top_k: Annotated[int, Field(ge=1, le=50)] = 5
    extra_filter: str | None = None

class SourceChunk(BaseModel):
    chunk_id: str
    doc_id: str
    content: str
    source: str
    page_number: int
    access_level: AccessLevel
    score: float

class QueryResponse(BaseModel):
    query: str
    answer: str
    sources: list[SourceChunk]
    retrieval_score: float
    latency_ms: float
    tokens_used: int = 0
    role: Role
    requires_review: bool = False

class IndexStatusResponse(BaseModel):
    index_name: str
    document_count: int
    status: Literal["ready", "not_found"]
