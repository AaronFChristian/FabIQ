"""Tests for all 5 FabIQ agents — all run without Azure credentials."""
from __future__ import annotations
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fabiq.agents.state import FabIQState
from fabiq.agents.privilege_check import privilege_check_agent


# ── Agent 2: Privilege check (pure logic — no mocks needed) ──────────────────

class TestPrivilegeCheckAgent:
    """Agent 2 is pure logic — no LLM calls, no Azure — runs instantly."""

    @pytest.fixture
    def base_state(self) -> FabIQState:
        return {"query": "What is the EUV wavelength?", "user_role": "field_engineer",
                "latency_ms": {}, "errors": []}

    @pytest.mark.asyncio
    async def test_field_engineer_gets_public_only(self, base_state):
        state = {**base_state, "user_role": "field_engineer"}
        result = await privilege_check_agent(state)
        assert result["allowed_privilege_levels"] == ["public"]
        assert "access_level eq 'public'" in result["privilege_filter"]
        assert "internal" not in result["privilege_filter"]

    @pytest.mark.asyncio
    async def test_process_engineer_gets_internal(self, base_state):
        state = {**base_state, "user_role": "process_engineer"}
        result = await privilege_check_agent(state)
        assert "public" in result["allowed_privilege_levels"]
        assert "internal" in result["allowed_privilege_levels"]
        assert "access_level eq 'internal'" in result["privilege_filter"]

    @pytest.mark.asyncio
    async def test_admin_gets_all_levels(self, base_state):
        state = {**base_state, "user_role": "admin"}
        result = await privilege_check_agent(state)
        assert "public" in result["allowed_privilege_levels"]
        assert "internal" in result["allowed_privilege_levels"]
        assert "restricted" in result["allowed_privilege_levels"]

    @pytest.mark.asyncio
    async def test_unknown_role_defaults_to_public(self, base_state):
        state = {**base_state, "user_role": "unknown_role"}
        result = await privilege_check_agent(state)
        assert result["allowed_privilege_levels"] == ["public"]

    @pytest.mark.asyncio
    async def test_filter_is_valid_odata(self, base_state):
        for role in ["field_engineer", "process_engineer", "admin"]:
            state = {**base_state, "user_role": role}
            result = await privilege_check_agent(state)
            # OData filter uses eq and or operators
            assert "eq '" in result["privilege_filter"]
            assert "access_level" in result["privilege_filter"]

    @pytest.mark.asyncio
    async def test_latency_logged_to_state(self, base_state):
        result = await privilege_check_agent(base_state)
        assert "agent_2_privilege_check" in result.get("latency_ms", {})


# ── Agent 1: Query understanding (mocked OpenAI call) ────────────────────────

class TestQueryUnderstandingAgent:
    @pytest.fixture
    def base_state(self) -> FabIQState:
        return {"query": "How does EUV focus calibration work?",
                "user_role": "process_engineer", "latency_ms": {}, "errors": []}

    @pytest.mark.asyncio
    async def test_parses_valid_response(self, base_state):
        import json
        from fabiq.agents.query_understanding import query_understanding_agent

        mock_content = json.dumps({
            "refined_query": "EUV scanner focus calibration procedure",
            "intent": "procedural",
            "entities": ["focus calibration", "EUV scanner"]
        })
        mock_response = MagicMock()
        mock_response.choices[0].message.content = mock_content

        with patch("fabiq.agents.query_understanding.AsyncAzureOpenAI") as MockClient:
            MockClient.return_value.chat.completions.create = AsyncMock(return_value=mock_response)
            result = await query_understanding_agent(base_state)

        assert result["query_intent"] == "procedural"
        assert "focus calibration" in result["query_entities"]
        assert result["refined_query"] == "EUV scanner focus calibration procedure"

    @pytest.mark.asyncio
    async def test_falls_back_gracefully_on_error(self, base_state):
        from fabiq.agents.query_understanding import query_understanding_agent

        with patch("fabiq.agents.query_understanding.AsyncAzureOpenAI") as MockClient:
            MockClient.return_value.chat.completions.create = AsyncMock(
                side_effect=Exception("API timeout")
            )
            result = await query_understanding_agent(base_state)

        # Falls back to original query with defaults
        assert result["refined_query"] == base_state["query"]
        assert result["query_intent"] == "factual"
        assert len(result.get("errors", [])) > 0


# ── Agent 3: Retrieval (mocked FabIQSearchClient) ────────────────────────────

class TestRetrievalAgent:
    @pytest.fixture
    def state_after_understanding(self) -> FabIQState:
        return {
            "query": "EUV focus calibration",
            "refined_query": "EUV scanner focus calibration procedure",
            "user_role": "process_engineer",
            "query_intent": "procedural",
            "query_entities": ["focus"],
            "latency_ms": {}, "errors": [],
        }

    @pytest.mark.asyncio
    async def test_returns_chunks_as_dicts(self, state_after_understanding):
        from fabiq.agents.retrieval_agent import retrieval_agent
        from fabiq.retrieval.search import SearchResult

        fake_results = [
            SearchResult(
                chunk_id="abc", doc_id="d1", content="Focus calibration requires...",
                source="manual.pdf", page_number=5, access_level="internal",
                score=0.87, strategy="recursive", metadata={}
            )
        ]

        with patch("fabiq.agents.retrieval_agent.aembed_texts", new_callable=AsyncMock) as mock_embed,              patch("fabiq.agents.retrieval_agent.FabIQSearchClient") as MockSearch:
            mock_embed.return_value = [[0.1] * 1536]
            MockSearch.return_value.search = AsyncMock(return_value=fake_results)
            result = await retrieval_agent(state_after_understanding)

        assert len(result["retrieved_chunks"]) == 1
        chunk = result["retrieved_chunks"][0]
        assert chunk["content"] == "Focus calibration requires..."
        assert chunk["source"] == "manual.pdf"
        assert isinstance(chunk["score"], float)

    @pytest.mark.asyncio
    async def test_empty_results_handled(self, state_after_understanding):
        from fabiq.agents.retrieval_agent import retrieval_agent

        with patch("fabiq.agents.retrieval_agent.aembed_texts", new_callable=AsyncMock) as mock_embed,              patch("fabiq.agents.retrieval_agent.FabIQSearchClient") as MockSearch:
            mock_embed.return_value = [[0.0] * 1536]
            MockSearch.return_value.search = AsyncMock(return_value=[])
            result = await retrieval_agent(state_after_understanding)

        assert result["retrieved_chunks"] == []
        assert result["retrieval_precision"] == 0.0


# ── Agent 5: Eval judge (fallback path — no Anthropic key) ───────────────────

class TestEvalJudgeAgent:
    @pytest.fixture
    def state_after_generation(self) -> FabIQState:
        return {
            "query": "What is EUV wavelength?",
            "user_role": "process_engineer",
            "response": "EUV uses 13.5 nm wavelength [SOURCE_1].",
            "context_window": "[SOURCE_1] Content: EUV operates at 13.5 nm.",
            "citations": [{"source_num": 1, "chunk_id": "x", "source": "spec.pdf", "page_number": 1, "score": 0.9}],
            "ungrounded_claims": [],
            "session_id": "test-001",
            "latency_ms": {}, "errors": [],
        }

    @pytest.mark.asyncio
    async def test_heuristic_fallback_when_no_anthropic_key(self, state_after_generation):
        """Without an Anthropic key, agent uses heuristic scoring — still returns valid state."""
        from fabiq.agents.eval_judge import eval_judge_agent

        with patch("fabiq.agents.eval_judge.get_settings") as mock_cfg:
            mock_cfg.return_value.anthropic_key = ""
            mock_cfg.return_value.hitl_confidence_threshold = 0.6
            result = await eval_judge_agent(state_after_generation)

        assert 0.0 <= result["eval_accuracy"] <= 1.0
        assert 0.0 <= result["eval_grounding"] <= 1.0
        assert 0.0 <= result["eval_completeness"] <= 1.0
        assert 0.0 <= result["eval_confidence"] <= 1.0
        assert isinstance(result["requires_human_review"], bool)

    @pytest.mark.asyncio
    async def test_hitl_triggered_below_threshold(self, state_after_generation):
        from fabiq.agents.eval_judge import eval_judge_agent

        # Low-confidence response: empty answer, no citations
        weak_state = {**state_after_generation,
                      "response": "I don't know.",
                      "citations": [],
                      "context_window": ""}

        with patch("fabiq.agents.eval_judge.get_settings") as mock_cfg:
            mock_cfg.return_value.anthropic_key = ""
            mock_cfg.return_value.hitl_confidence_threshold = 0.6
            result = await eval_judge_agent(weak_state)

        assert result["requires_human_review"] is True

    @pytest.mark.asyncio
    async def test_scores_with_mock_anthropic(self, state_after_generation):
        """Test with mocked Anthropic call returns correct parsed scores."""
        import json
        from fabiq.agents.eval_judge import eval_judge_agent

        mock_scores = json.dumps({
            "accuracy": 0.9, "grounding": 0.85, "completeness": 0.8,
            "reasoning": "Answer is accurate and well-grounded."
        })
        mock_msg = MagicMock()
        mock_msg.content[0].text = mock_scores

        with patch("fabiq.agents.eval_judge.get_settings") as mock_cfg,              patch("fabiq.agents.eval_judge.anthropic.AsyncAnthropic") as MockAnthropic:
            mock_cfg.return_value.anthropic_key = "fake-key"
            mock_cfg.return_value.hitl_confidence_threshold = 0.6
            MockAnthropic.return_value.messages.create = AsyncMock(return_value=mock_msg)
            result = await eval_judge_agent(state_after_generation)

        assert result["eval_accuracy"] == pytest.approx(0.9)
        assert result["eval_grounding"] == pytest.approx(0.85)
        assert result["eval_confidence"] == pytest.approx((0.9 + 0.85 + 0.8) / 3, abs=0.01)
        assert result["requires_human_review"] is False
