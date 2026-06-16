"""POST /query — runs the user query through the 5-agent LangGraph pipeline."""
from __future__ import annotations
import time
import structlog
from fastapi import APIRouter, HTTPException, status
from fabiq.api.models import QueryRequest, QueryResponse, SourceChunk

router = APIRouter(prefix="/query", tags=["retrieval"])
logger = structlog.get_logger(__name__)

@router.post("/", response_model=QueryResponse, summary="Query via 5-agent pipeline")
async def query(req: QueryRequest) -> QueryResponse:
    from fabiq.pipeline.graph import compile_pipeline
    t0 = time.perf_counter()
    initial_state = {"query": req.query, "user_role": req.role,
                     "session_id": f"api-{int(t0)}", "latency_ms": {}, "errors": []}
    try:
        final_state = await compile_pipeline().ainvoke(initial_state)
        chunks = final_state.get("retrieved_chunks", [])
        source_chunks = [SourceChunk(chunk_id=c.get("chunk_id",""), doc_id=c.get("doc_id",""),
                                     content=c.get("content",""), source=c.get("source",""),
                                     page_number=c.get("page_number",0),
                                     access_level=c.get("access_level","public"),
                                     score=round(c.get("score",0.0),4)) for c in chunks]
        return QueryResponse(
            query=req.query, answer=final_state.get("response",""),
            sources=source_chunks,
            retrieval_score=round(float(final_state.get("retrieval_precision",0.0)),4),
            latency_ms=round((time.perf_counter()-t0)*1000,1),
            tokens_used=final_state.get("tokens_used",0),
            role=req.role, requires_review=final_state.get("requires_human_review",False))
    except Exception as exc:
        logger.error("pipeline_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {exc}") from exc
