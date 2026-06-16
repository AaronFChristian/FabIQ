"""LangGraph orchestrator — 5-agent state machine with HITL gate."""
from __future__ import annotations
import structlog
from langgraph.graph import END, START, StateGraph
from fabiq.agents.state import FabIQState
from fabiq.agents.query_understanding import query_understanding_agent
from fabiq.agents.privilege_check import privilege_check_agent
from fabiq.agents.retrieval_agent import retrieval_agent
from fabiq.agents.citation_grounding import citation_grounding_agent
from fabiq.agents.eval_judge import eval_judge_agent

log = structlog.get_logger(__name__)

async def human_review_node(state: FabIQState) -> FabIQState:
    log.warning("human_review_required", confidence=state.get("eval_confidence"))
    return {**state, "response": f"[REVIEW REQUIRED — confidence: {state.get('eval_confidence',0):.2f}]\n\n" + state.get("response","")}

def _route_after_eval(state: FabIQState) -> str:
    return "human_review" if state.get("requires_human_review", False) else END

def build_graph() -> StateGraph:
    graph = StateGraph(FabIQState)
    graph.add_node("agent_1_query_understanding", query_understanding_agent)
    graph.add_node("agent_2_privilege_check",     privilege_check_agent)
    graph.add_node("agent_3_retrieval",           retrieval_agent)
    graph.add_node("agent_4_citation_grounding",  citation_grounding_agent)
    graph.add_node("agent_5_eval_judge",          eval_judge_agent)
    graph.add_node("human_review",                human_review_node)
    graph.add_edge(START,                         "agent_1_query_understanding")
    graph.add_edge("agent_1_query_understanding", "agent_2_privilege_check")
    graph.add_edge("agent_2_privilege_check",     "agent_3_retrieval")
    graph.add_edge("agent_3_retrieval",           "agent_4_citation_grounding")
    graph.add_edge("agent_4_citation_grounding",  "agent_5_eval_judge")
    graph.add_conditional_edges("agent_5_eval_judge", _route_after_eval, {"human_review":"human_review", END:END})
    graph.add_edge("human_review", END)
    return graph

def compile_pipeline():
    return build_graph().compile()
