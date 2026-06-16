from __future__ import annotations
import tempfile, time
from pathlib import Path
from typing import Annotated
import structlog
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from fabiq.api.models import AccessLevel, ChunkStrategy, IngestRequest, IngestResponse
from fabiq.ingestion.chunker import chunk_document
from fabiq.ingestion.embedder import aembed_texts
from fabiq.ingestion.loader import load_document
from fabiq.config import get_settings
from fabiq.retrieval.search import FabIQSearchClient

router = APIRouter(prefix="/ingest", tags=["ingestion"])
logger = structlog.get_logger(__name__)
_ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".mdx", ".rst"}

async def _run_ingestion(file_path: Path, filename: str, req: IngestRequest, search) -> IngestResponse:
    t0 = time.perf_counter()
    raw_docs = await run_in_threadpool(load_document, file_path, access_level=req.access_level, extra_metadata={**req.extra_metadata, "filename": filename})
    if not raw_docs:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Document produced no extractable text.")
    doc_id = raw_docs[0].doc_id
    all_chunks = []
    for raw_doc in raw_docs:
        if req.chunk_strategy == "semantic":
            from fabiq.ingestion.embedder import embed_texts
            chunks = await run_in_threadpool(chunk_document, raw_doc, req.chunk_strategy, chunk_size=req.chunk_size, overlap=req.chunk_overlap, embed_fn=embed_texts)
        else:
            chunks = await run_in_threadpool(chunk_document, raw_doc, req.chunk_strategy, chunk_size=req.chunk_size, overlap=req.chunk_overlap)
        all_chunks.extend(chunks)
    if not all_chunks:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Chunking produced zero chunks.")
    embeddings = await aembed_texts([c.content for c in all_chunks])
    await search.ensure_index_exists()
    indexed = await search.ingest_chunks(all_chunks, embeddings)
    elapsed = (time.perf_counter() - t0) * 1000
    return IngestResponse(doc_id=doc_id, filename=filename, chunks_indexed=indexed, strategy_used=req.chunk_strategy, access_level=req.access_level, elapsed_ms=round(elapsed, 1))

@router.post("/", response_model=IngestResponse, status_code=status.HTTP_201_CREATED, summary="Upload and index a document")
async def ingest_document(
    file: Annotated[UploadFile, File()],
    access_level: Annotated[AccessLevel, Form()] = "public",
    chunk_strategy: Annotated[ChunkStrategy, Form()] = "recursive",
    chunk_size: Annotated[int, Form(ge=64, le=4096)] = 512,
    chunk_overlap: Annotated[int, Form(ge=0, le=512)] = 64,
) -> IngestResponse:
    filename = file.filename or "unknown"
    if Path(filename).suffix.lower() not in _ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=f"Unsupported file type.")
    req = IngestRequest(access_level=access_level, chunk_strategy=chunk_strategy, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    with tempfile.NamedTemporaryFile(suffix=Path(filename).suffix.lower(), delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)
    try:
        cfg = get_settings()
        if cfg.app_mode == "local":
            from fabiq.retrieval.local_search import LocalSearchClient
            search_client = LocalSearchClient(cfg)
        else:
            search_client = FabIQSearchClient(cfg)
        return await _run_ingestion(tmp_path, filename, req, search_client)
    finally:
        tmp_path.unlink(missing_ok=True)
