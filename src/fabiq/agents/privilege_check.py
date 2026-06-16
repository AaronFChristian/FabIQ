"""Agent 2 — Privilege-aware retrieval gate."""
from __future__ import annotations
import time
import structlog
from fabiq.agents.state import FabIQState
from fabiq.retrieval.search import get_access_filter

log = structlog.get_logger(__name__)

_LEVEL_MAP = {
    "field_engineer":    ["public"],
    "process_engineer":  ["public", "internal"],
    "admin":             ["public", "internal", "restricted"],
}

async def privilege_check_agent(state: FabIQState) -> FabIQState:
    t0 = time.perf_counter()
    user_role = state.get("user_role", "field_engineer")
    filter_expr = get_access_filter(user_role)
    allowed = _LEVEL_MAP.get(user_role, ["public"])
    elapsed = (time.perf_counter()-t0)*1000
    log.info("privilege_check_complete", user_role=user_role, allowed_levels=allowed, latency_ms=round(elapsed,1))
    return {**state, "allowed_privilege_levels": allowed, "privilege_filter": filter_expr,
            "latency_ms": {**(state.get("latency_ms") or {}), "agent_2_privilege_check": elapsed}}
