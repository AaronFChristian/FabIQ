"""Tests for the LangGraph pipeline graph compilation and routing."""
from __future__ import annotations
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestPipelineCompilation:
    """Graph compiles without errors and has the expected structure."""

    def test_graph_compiles(self):
        from fabiq.pipeline.graph import compile_pipeline
        pipeline = compile_pipeline()
        assert pipeline is not None

    def test_graph_has_all_nodes(self):
        from fabiq.pipeline.graph import build_graph
        graph = build_graph()
        # Access internal nodes dict
        node_names = set(graph.nodes.keys())
        assert "agent_1_query_understanding" in node_names
        assert "agent_2_privilege_check"     in node_names
        assert "agent_3_retrieval"           in node_names
        assert "agent_4_citation_grounding"  in node_names
        assert "agent_5_eval_judge"          in node_names
        assert "human_review"                in node_names


class TestHITLRouting:
    """Conditional edge routes to human_review when confidence is low."""

    @pytest.mark.asyncio
    async def test_low_confidence_triggers_human_review(self):
        from fabiq.pipeline.graph import compile_pipeline

        async def mock_agent(state):
            return state

        async def mock_eval(state):
            return {**state, "requires_human_review": True, "eval_confidence": 0.3,
                    "eval_accuracy": 0.3, "eval_grounding": 0.3, "eval_completeness": 0.3}

        async def mock_retrieval(state):
            return {**state, "retrieved_chunks": [], "retrieval_precision": 0.0, "query_vector": []}

        async def mock_generation(state):
            return {**state, "response": "Low confidence answer.", "citations": [],
                    "ungrounded_claims": [], "context_window": ""}

        with patch("fabiq.pipeline.graph.query_understanding_agent", mock_agent),              patch("fabiq.pipeline.graph.privilege_check_agent", mock_agent),              patch("fabiq.pipeline.graph.retrieval_agent", mock_retrieval),              patch("fabiq.pipeline.graph.citation_grounding_agent", mock_generation),              patch("fabiq.pipeline.graph.eval_judge_agent", mock_eval):

            pipeline = compile_pipeline()
            result = await pipeline.ainvoke({
                "query": "test", "user_role": "field_engineer",
                "latency_ms": {}, "errors": [],
            })

        # HITL gate was triggered — response should carry the review flag
        assert result.get("requires_human_review") is True
        assert "[REVIEW REQUIRED" in result.get("response", "")

    @pytest.mark.asyncio
    async def test_high_confidence_skips_human_review(self):
        from fabiq.pipeline.graph import compile_pipeline

        async def mock_agent(state):
            return state

        async def mock_eval(state):
            return {**state, "requires_human_review": False, "eval_confidence": 0.92,
                    "eval_accuracy": 0.9, "eval_grounding": 0.95, "eval_completeness": 0.9}

        async def mock_retrieval(state):
            return {**state, "retrieved_chunks": [], "retrieval_precision": 0.9, "query_vector": []}

        async def mock_generation(state):
            return {**state, "response": "High confidence answer.", "citations": [],
                    "ungrounded_claims": [], "context_window": ""}

        with patch("fabiq.pipeline.graph.query_understanding_agent", mock_agent),              patch("fabiq.pipeline.graph.privilege_check_agent", mock_agent),              patch("fabiq.pipeline.graph.retrieval_agent", mock_retrieval),              patch("fabiq.pipeline.graph.citation_grounding_agent", mock_generation),              patch("fabiq.pipeline.graph.eval_judge_agent", mock_eval):

            pipeline = compile_pipeline()
            result = await pipeline.ainvoke({
                "query": "test", "user_role": "process_engineer",
                "latency_ms": {}, "errors": [],
            })

        assert result.get("requires_human_review") is False
        assert "[REVIEW REQUIRED" not in result.get("response", "")


class TestGoldenDataset:
    """Golden dataset loads and has the right shape."""

    def test_loads_thirty_questions(self):
        from eval.golden_dataset import GOLDEN_DATASET
        assert len(GOLDEN_DATASET) == 30

    def test_each_tier_has_ten_questions(self):
        from eval.golden_dataset import get_tier
        for tier in [1, 2, 3]:
            assert len(get_tier(tier)) == 10

    def test_all_questions_have_keywords(self):
        from eval.golden_dataset import GOLDEN_DATASET
        for item in GOLDEN_DATASET:
            assert len(item.expected_keywords) > 0, f"{item.id} has no keywords"

    def test_keyword_hit_rate_calculation(self):
        """Verify the eval runner keyword scoring logic directly."""
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent / "eval"))
        from run_eval import _keyword_hit_rate
        assert _keyword_hit_rate("EUV uses 13.5 nm wavelength", ["13.5", "nm", "wavelength"]) == 1.0
        assert _keyword_hit_rate("EUV uses 13.5 nm", ["13.5", "nm", "wavelength"]) == pytest.approx(2/3, abs=0.01)
        assert _keyword_hit_rate("something unrelated", ["13.5", "nm"]) == 0.0
        assert _keyword_hit_rate("anything", []) == 1.0
