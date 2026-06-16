"""Agent 5 — LLM-as-judge + HITL gate."""
from __future__ import annotations
import json, time
import structlog
import anthropic
from fabiq.agents.state import FabIQState
from fabiq.config import get_settings

log = structlog.get_logger(__name__)

JUDGE_PROMPT = """You are a quality evaluation judge for a technical documentation RAG system.
Score each dimension 0.0-1.0. Be strict — inaccurate answers cause production failures.
Return ONLY JSON: {"accuracy":0.0,"grounding":0.0,"completeness":0.0,"reasoning":"brief explanation"}"""

async def eval_judge_agent(state: FabIQState) -> FabIQState:
    t0 = time.perf_counter()
    cfg = get_settings()
    if not cfg.anthropic_key:
        log.warning("eval_judge_skipped_no_anthropic_key")
        has_r = bool(state.get("response") and len(state.get("response",""))>20)
        has_c = bool(state.get("citations"))
        acc,grd,comp = (0.7 if has_r else 0.3),(0.8 if has_c else 0.4),(0.7 if has_r else 0.3)
        conf = round((acc+grd+comp)/3,4)
        return {**state,"eval_accuracy":acc,"eval_grounding":grd,"eval_completeness":comp,
                "eval_confidence":conf,"requires_human_review":conf<cfg.hitl_confidence_threshold,
                "latency_ms":{**(state.get("latency_ms") or {}),"agent_5_eval_judge":0}}
    client = anthropic.AsyncAnthropic(api_key=cfg.anthropic_key)
    payload = json.dumps({"question":state.get("query",""),"answer":state.get("response",""),
                          "sources_provided":state.get("context_window","")[:3000],
                          "ungrounded_claims":state.get("ungrounded_claims",[])},indent=2)
    try:
        msg = await client.messages.create(model="claude-sonnet-4-6", max_tokens=512,
                                           system=JUDGE_PROMPT,
                                           messages=[{"role":"user","content":payload}])
        raw = msg.content[0].text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        scores = json.loads(raw)
        acc=float(scores.get("accuracy",0.5)); grd=float(scores.get("grounding",0.5)); comp=float(scores.get("completeness",0.5))
        conf=round((acc+grd+comp)/3,4); req=conf<cfg.hitl_confidence_threshold
        elapsed=(time.perf_counter()-t0)*1000
        log.info("eval_complete",accuracy=acc,grounding=grd,completeness=comp,confidence=conf,requires_human_review=req,latency_ms=round(elapsed,1))
        if req: log.warning("hitl_gate_triggered",confidence=conf,threshold=cfg.hitl_confidence_threshold)
        return {**state,"eval_accuracy":acc,"eval_grounding":grd,"eval_completeness":comp,
                "eval_confidence":conf,"requires_human_review":req,
                "latency_ms":{**(state.get("latency_ms") or {}),"agent_5_eval_judge":elapsed}}
    except Exception as exc:
        log.error("eval_judge_failed",error=str(exc))
        return {**state,"eval_accuracy":0.5,"eval_grounding":0.5,"eval_completeness":0.5,
                "eval_confidence":0.5,"requires_human_review":False,"errors":[f"Agent 5 error: {exc}"]}
