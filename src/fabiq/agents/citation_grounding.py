"""Agent 4 — Citation grounding + response generation."""
from __future__ import annotations
import json, re, time
import structlog
from openai import AsyncAzureOpenAI
from fabiq.agents.state import FabIQState
from fabiq.config import get_settings

log = structlog.get_logger(__name__)

SYSTEM_PROMPT = """You are a technical documentation assistant for semiconductor manufacturing.
Answer ONLY from the provided source documents.
Rules:
1. Cite sources inline using [SOURCE_1], [SOURCE_2] etc.
2. If not in sources, say: "This information is not available in the provided documents"
3. Never fabricate specifications or procedures.
Return JSON: {"answer":"answer with [SOURCE_N] inline","cited_sources":[1,2,3]}"""

def _assemble_context(chunks):
    parts, citations = [], []
    for i, c in enumerate(chunks, 1):
        parts.append(f"[SOURCE_{i}]\nFile: {c.get('source','unknown')} | Page: {c.get('page_number','N/A')}\nContent: {c['content']}")
        citations.append({"source_num":i,"chunk_id":c["chunk_id"],"source":c.get("source",""),"page_number":c.get("page_number",0),"score":c.get("score",0.0)})
    return "\n---\n".join(parts), citations


def _local_grounded_answer(question: str, chunks: list[dict]) -> tuple[str, list[int]]:
    """Extractive/template answer for APP_MODE=local.

    This avoids cloud LLM calls while still proving retrieval, RBAC, citations,
    and the end-to-end API/dashboard workflow.
    """
    question_terms = {t.lower().strip(".,?!:;()[]{}") for t in question.split() if len(t) > 3}
    lines: list[str] = []
    cited: list[int] = []
    for i, chunk in enumerate(chunks[:5], 1):
        content = " ".join((chunk.get("content") or "").split())
        if not content:
            continue
        sentences = re.split(r"(?<=[.!?])\s+", content)
        ranked = []
        for sentence in sentences:
            sentence_terms = {t.lower().strip(".,?!:;()[]{}") for t in sentence.split()}
            overlap = len(question_terms & sentence_terms)
            ranked.append((overlap, sentence))
        ranked.sort(key=lambda item: item[0], reverse=True)
        selected = ranked[0][1] if ranked else content
        selected = selected[:420].strip()
        if selected:
            lines.append(f"- {selected} [SOURCE_{i}]")
            cited.append(i)
    if not lines:
        return "This information is not available in the provided documents", []
    return "Based on the retrieved documents:\n" + "\n".join(lines), cited

def _ungrounded(response, cited_nums):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", response)
            if not re.search(r"\[SOURCE_\d+\]",s) and "not available" not in s.lower() and len(s.split())>5]

async def citation_grounding_agent(state: FabIQState) -> FabIQState:
    t0 = time.perf_counter()
    cfg = get_settings()
    chunks = state.get("retrieved_chunks",[])
    if not chunks:
        return {**state,"response":"No relevant documents found.","citations":[],"ungrounded_claims":[],"context_window":""}
    context, citation_meta = _assemble_context(chunks)
    if cfg.app_mode == "local":
        answer, cited = _local_grounded_answer(state["query"], chunks)
        elapsed = (time.perf_counter() - t0) * 1000
        log.info("generation_local_complete", citations=len(cited), latency_ms=round(elapsed, 1))
        return {**state, "context_window": context, "response": answer,
                "citations": [c for c in citation_meta if c["source_num"] in cited],
                "ungrounded_claims": _ungrounded(answer, cited),
                "latency_ms": {**(state.get("latency_ms") or {}), "agent_4_generation": elapsed}}

    client = AsyncAzureOpenAI(api_key=cfg.azure_openai_api_key, azure_endpoint=cfg.azure_openai_endpoint, api_version=cfg.azure_openai_api_version)
    try:
        comp = await client.chat.completions.create(
            model=cfg.azure_openai_chat_deployment,
            messages=[{"role":"system","content":SYSTEM_PROMPT},{"role":"user","content":f"Context:\n{context}\n\nQuestion: {state['query']}"}],
            response_format={"type":"json_object"}, temperature=0.1, max_tokens=1024)
        parsed = json.loads(comp.choices[0].message.content or "{}")
        answer = parsed.get("answer","")
        cited  = parsed.get("cited_sources",[])
        elapsed = (time.perf_counter()-t0)*1000
        log.info("generation_complete", citations=len([c for c in citation_meta if c["source_num"] in cited]), latency_ms=round(elapsed,1))
        return {**state,"context_window":context,"response":answer,
                "citations":[c for c in citation_meta if c["source_num"] in cited],
                "ungrounded_claims":_ungrounded(answer,cited),
                "latency_ms":{**(state.get("latency_ms") or {}),"agent_4_generation":elapsed}}
    except Exception as exc:
        log.error("generation_failed", error=str(exc))
        return {**state,"response":"Error generating response.","citations":[],"ungrounded_claims":[],"errors":[f"Agent 4 error: {exc}"]}
