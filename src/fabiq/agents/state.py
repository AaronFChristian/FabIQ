"""LangGraph pipeline state — typed dict flowing through all 5 agents."""
from __future__ import annotations
from typing import Annotated, TypedDict
import operator

class FabIQState(TypedDict, total=False):
    query: str
    user_role: str
    session_id: str
    refined_query: str
    query_intent: str
    query_entities: list[str]
    allowed_privilege_levels: list[str]
    privilege_filter: str
    query_vector: list[float]
    retrieved_chunks: list[dict]
    retrieval_precision: float
    context_window: str
    response: str
    citations: list[dict]
    ungrounded_claims: list[str]
    eval_accuracy: float
    eval_grounding: float
    eval_completeness: float
    eval_confidence: float
    requires_human_review: bool
    errors: Annotated[list[str], operator.add]
    latency_ms: dict[str, float]
