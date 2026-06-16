"""Tests for the LangGraph pipeline."""
from __future__ import annotations
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

class TestPipelineCompilation:
    def test_graph_compiles(self):
        from fabiq.pipeline.graph import compile_pipeline
        assert compile_pipeline() is not None

    def test_graph_has_all_nodes(self):
        from fabiq.pipeline.graph import build_graph
        nodes = set(build_graph().nodes.keys())
        for n in ["agent_1_query_understanding","agent_2_privilege_check","agent_3_retrieval",
                  "agent_4_citation_grounding","agent_5_eval_judge","human_review"]:
            assert n in nodes

class TestHITLRouting:
    @pytest.mark.asyncio
    async def test_low_confidence_triggers_review(self):
        from fabiq.pipeline.graph import compile_pipeline
        async def noop(s): return s
        async def mock_eval(s): return {**s,"requires_human_review":True,"eval_confidence":0.3,"eval_accuracy":0.3,"eval_grounding":0.3,"eval_completeness":0.3}
        async def mock_ret(s): return {**s,"retrieved_chunks":[],"retrieval_precision":0.0,"query_vector":[]}
        async def mock_gen(s): return {**s,"response":"Low confidence.","citations":[],"ungrounded_claims":[],"context_window":""}
        with patch("fabiq.pipeline.graph.query_understanding_agent",noop),              patch("fabiq.pipeline.graph.privilege_check_agent",noop),              patch("fabiq.pipeline.graph.retrieval_agent",mock_ret),              patch("fabiq.pipeline.graph.citation_grounding_agent",mock_gen),              patch("fabiq.pipeline.graph.eval_judge_agent",mock_eval):
            r = await compile_pipeline().ainvoke({"query":"test","user_role":"field_engineer","latency_ms":{},"errors":[]})
        assert r.get("requires_human_review") is True
        assert "[REVIEW REQUIRED" in r.get("response","")

    @pytest.mark.asyncio
    async def test_high_confidence_skips_review(self):
        from fabiq.pipeline.graph import compile_pipeline
        async def noop(s): return s
        async def mock_eval(s): return {**s,"requires_human_review":False,"eval_confidence":0.92,"eval_accuracy":0.9,"eval_grounding":0.95,"eval_completeness":0.9}
        async def mock_ret(s): return {**s,"retrieved_chunks":[],"retrieval_precision":0.9,"query_vector":[]}
        async def mock_gen(s): return {**s,"response":"High confidence.","citations":[],"ungrounded_claims":[],"context_window":""}
        with patch("fabiq.pipeline.graph.query_understanding_agent",noop),              patch("fabiq.pipeline.graph.privilege_check_agent",noop),              patch("fabiq.pipeline.graph.retrieval_agent",mock_ret),              patch("fabiq.pipeline.graph.citation_grounding_agent",mock_gen),              patch("fabiq.pipeline.graph.eval_judge_agent",mock_eval):
            r = await compile_pipeline().ainvoke({"query":"test","user_role":"process_engineer","latency_ms":{},"errors":[]})
        assert r.get("requires_human_review") is False

class TestGoldenDataset:
    def test_loads_thirty_questions(self):
        from eval.golden_dataset import GOLDEN_DATASET
        assert len(GOLDEN_DATASET)==30

    def test_each_tier_has_ten(self):
        from eval.golden_dataset import get_tier
        for t in [1,2,3]: assert len(get_tier(t))==10

    def test_all_have_keywords(self):
        from eval.golden_dataset import GOLDEN_DATASET
        for item in GOLDEN_DATASET:
            assert len(item.expected_keywords)>0

    def test_keyword_hit_rate(self):
        import sys; from pathlib import Path
        sys.path.insert(0,str(Path(__file__).parent.parent/"eval"))
        from run_eval import _keyword_hit_rate
        assert _keyword_hit_rate("EUV uses 13.5 nm wavelength",["13.5","nm","wavelength"])==1.0
        assert _keyword_hit_rate("something else",["13.5","nm"])==0.0
