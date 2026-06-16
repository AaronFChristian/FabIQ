"""Agent 1 — Query understanding."""
from __future__ import annotations
import json, time
import structlog
from openai import AsyncAzureOpenAI
from fabiq.agents.state import FabIQState
from fabiq.config import get_settings

log = structlog.get_logger(__name__)

SYSTEM_PROMPT = """You are a query understanding module for a technical documentation retrieval system.
Given a user query, return a JSON object with exactly these fields:
{"refined_query":"optimised query","intent":"factual|procedural|comparative|multi_hop","entities":["key","terms"]}
Return ONLY the JSON object."""

async def query_understanding_agent(state: FabIQState) -> FabIQState:
    t0 = time.perf_counter()
    cfg = get_settings()
    if cfg.app_mode == "local":
        elapsed = (time.perf_counter() - t0) * 1000
        terms = [word.strip(".,?!:;()[]{}").lower() for word in state["query"].split()]
        entities = [word for word in terms if len(word) > 3][:8]
        log.info("query_understanding_local", latency_ms=round(elapsed, 1))
        return {**state, "refined_query": state["query"],
                "query_intent": "factual",
                "query_entities": entities,
                "latency_ms": {**(state.get("latency_ms") or {}), "agent_1_query_understanding": elapsed}}

    client = AsyncAzureOpenAI(api_key=cfg.azure_openai_api_key,
                               azure_endpoint=cfg.azure_openai_endpoint,
                               api_version=cfg.azure_openai_api_version)
    try:
        resp = await client.chat.completions.create(
            model=cfg.azure_openai_chat_deployment,
            messages=[{"role":"system","content":SYSTEM_PROMPT},{"role":"user","content":state["query"]}],
            response_format={"type":"json_object"}, temperature=0, max_tokens=256)
        parsed = json.loads(resp.choices[0].message.content or "{}")
        elapsed = (time.perf_counter()-t0)*1000
        log.info("query_understanding_complete", intent=parsed.get("intent"), latency_ms=round(elapsed,1))
        return {**state, "refined_query": parsed.get("refined_query", state["query"]),
                "query_intent": parsed.get("intent","factual"),
                "query_entities": parsed.get("entities",[]),
                "latency_ms": {**(state.get("latency_ms") or {}), "agent_1_query_understanding": elapsed}}
    except Exception as exc:
        log.error("query_understanding_failed", error=str(exc))
        return {**state, "refined_query": state["query"], "query_intent": "factual",
                "query_entities": [], "errors": [f"Agent 1 error: {exc}"]}
