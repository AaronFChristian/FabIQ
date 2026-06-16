"""Agent 3 — Hybrid retrieval."""
from __future__ import annotations
import time
import structlog
from fabiq.agents.state import FabIQState
from fabiq.ingestion.embedder import aembed_texts
from fabiq.config import get_settings
from fabiq.retrieval.search import FabIQSearchClient

log = structlog.get_logger(__name__)

async def retrieval_agent(state: FabIQState) -> FabIQState:
    t0 = time.perf_counter()
    query = state.get("refined_query") or state["query"]
    user_role = state.get("user_role","field_engineer")
    try:
        cfg = get_settings()
        query_vector = (await aembed_texts([query], settings=cfg))[0]
        if cfg.app_mode == "local":
            from fabiq.retrieval.local_search import LocalSearchClient
            search_client = LocalSearchClient(cfg)
        else:
            search_client = FabIQSearchClient(cfg)
        results = await search_client.search(query=query, query_embedding=query_vector, role=user_role)
        chunks = [{"chunk_id":r.chunk_id,"doc_id":r.doc_id,"content":r.content,
                   "source":r.source,"page_number":r.page_number,
                   "access_level":r.access_level,"score":r.score,"strategy":r.strategy}
                  for r in results]
        top_score = results[0].score if results else 0.0
        elapsed = (time.perf_counter()-t0)*1000
        log.info("retrieval_complete", chunks=len(results), top_score=round(top_score,4), latency_ms=round(elapsed,1))
        return {**state, "query_vector": query_vector, "retrieved_chunks": chunks,
                "retrieval_precision": top_score,
                "latency_ms": {**(state.get("latency_ms") or {}), "agent_3_retrieval": elapsed}}
    except Exception as exc:
        log.error("retrieval_failed", error=str(exc))
        return {**state, "query_vector":[], "retrieved_chunks":[], "retrieval_precision":0.0,
                "errors":[f"Agent 3 error: {exc}"]}
