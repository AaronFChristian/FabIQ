"""Tests for all 5 FabIQ agents."""
from __future__ import annotations
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fabiq.agents.state import FabIQState
from fabiq.agents.privilege_check import privilege_check_agent

class TestPrivilegeCheckAgent:
    @pytest.fixture
    def s(self): return {"query":"test","user_role":"field_engineer","latency_ms":{},"errors":[]}

    @pytest.mark.asyncio
    async def test_field_engineer_public_only(self,s):
        r = await privilege_check_agent({**s,"user_role":"field_engineer"})
        assert r["allowed_privilege_levels"]==["public"]
        assert "internal" not in r["privilege_filter"]

    @pytest.mark.asyncio
    async def test_process_engineer_gets_internal(self,s):
        r = await privilege_check_agent({**s,"user_role":"process_engineer"})
        assert "internal" in r["allowed_privilege_levels"]

    @pytest.mark.asyncio
    async def test_admin_gets_all(self,s):
        r = await privilege_check_agent({**s,"user_role":"admin"})
        assert "restricted" in r["allowed_privilege_levels"]

    @pytest.mark.asyncio
    async def test_unknown_role_defaults_public(self,s):
        r = await privilege_check_agent({**s,"user_role":"unknown"})
        assert r["allowed_privilege_levels"]==["public"]

    @pytest.mark.asyncio
    async def test_filter_is_valid_odata(self,s):
        for role in ["field_engineer","process_engineer","admin"]:
            r = await privilege_check_agent({**s,"user_role":role})
            assert "eq '" in r["privilege_filter"] and "access_level" in r["privilege_filter"]

    @pytest.mark.asyncio
    async def test_latency_logged(self,s):
        r = await privilege_check_agent(s)
        assert "agent_2_privilege_check" in r.get("latency_ms",{})

class TestQueryUnderstandingAgent:
    @pytest.fixture
    def s(self): return {"query":"How does EUV focus calibration work?","user_role":"process_engineer","latency_ms":{},"errors":[]}

    @pytest.mark.asyncio
    async def test_parses_valid_response(self,s):
        import json
        from fabiq.agents.query_understanding import query_understanding_agent
        mock_content = json.dumps({"refined_query":"EUV focus calibration","intent":"procedural","entities":["focus calibration"]})
        mock_resp = MagicMock(); mock_resp.choices[0].message.content = mock_content
        with patch("fabiq.agents.query_understanding.AsyncAzureOpenAI") as M:
            M.return_value.chat.completions.create = AsyncMock(return_value=mock_resp)
            r = await query_understanding_agent(s)
        assert r["query_intent"]=="procedural"

    @pytest.mark.asyncio
    async def test_fallback_on_error(self,s):
        from fabiq.agents.query_understanding import query_understanding_agent
        with patch("fabiq.agents.query_understanding.AsyncAzureOpenAI") as M:
            M.return_value.chat.completions.create = AsyncMock(side_effect=Exception("timeout"))
            r = await query_understanding_agent(s)
        assert r["refined_query"]==s["query"]
        assert len(r.get("errors",[]))>0

class TestRetrievalAgent:
    @pytest.fixture
    def s(self): return {"query":"EUV focus","refined_query":"EUV focus calibration","user_role":"process_engineer","latency_ms":{},"errors":[]}

    @pytest.mark.asyncio
    async def test_returns_chunks_as_dicts(self,s):
        from fabiq.agents.retrieval_agent import retrieval_agent
        from fabiq.retrieval.search import SearchResult
        fake = [SearchResult(chunk_id="a",doc_id="d",content="Focus requires...",source="m.pdf",page_number=5,access_level="internal",score=0.87,strategy="recursive",metadata={})]
        with patch("fabiq.agents.retrieval_agent.aembed_texts", new_callable=AsyncMock) as me,              patch("fabiq.agents.retrieval_agent.FabIQSearchClient") as MS:
            me.return_value=[[0.1]*1536]; MS.return_value.search=AsyncMock(return_value=fake)
            r = await retrieval_agent(s)
        assert len(r["retrieved_chunks"])==1
        assert r["retrieved_chunks"][0]["content"]=="Focus requires..."

    @pytest.mark.asyncio
    async def test_empty_results(self,s):
        from fabiq.agents.retrieval_agent import retrieval_agent
        with patch("fabiq.agents.retrieval_agent.aembed_texts", new_callable=AsyncMock) as me,              patch("fabiq.agents.retrieval_agent.FabIQSearchClient") as MS:
            me.return_value=[[0.0]*1536]; MS.return_value.search=AsyncMock(return_value=[])
            r = await retrieval_agent(s)
        assert r["retrieved_chunks"]==[] and r["retrieval_precision"]==0.0

class TestEvalJudgeAgent:
    @pytest.fixture
    def s(self): return {"query":"EUV wavelength?","user_role":"process_engineer","response":"EUV uses 13.5 nm [SOURCE_1].","context_window":"[SOURCE_1] 13.5 nm","citations":[{"source_num":1}],"ungrounded_claims":[],"session_id":"t","latency_ms":{},"errors":[]}

    @pytest.mark.asyncio
    async def test_heuristic_fallback(self,s):
        from fabiq.agents.eval_judge import eval_judge_agent
        with patch("fabiq.agents.eval_judge.get_settings") as mc:
            mc.return_value.anthropic_key=""; mc.return_value.hitl_confidence_threshold=0.6
            r = await eval_judge_agent(s)
        assert 0<=r["eval_confidence"]<=1 and isinstance(r["requires_human_review"],bool)

    @pytest.mark.asyncio
    async def test_hitl_triggered_on_weak_response(self,s):
        from fabiq.agents.eval_judge import eval_judge_agent
        weak = {**s,"response":"I don't know.","citations":[],"context_window":""}
        with patch("fabiq.agents.eval_judge.get_settings") as mc:
            mc.return_value.anthropic_key=""; mc.return_value.hitl_confidence_threshold=0.6
            r = await eval_judge_agent(weak)
        assert r["requires_human_review"] is True

    @pytest.mark.asyncio
    async def test_scores_with_mock_anthropic(self,s):
        import json
        from fabiq.agents.eval_judge import eval_judge_agent
        mock_scores = json.dumps({"accuracy":0.9,"grounding":0.85,"completeness":0.8,"reasoning":"good"})
        mock_msg = MagicMock(); mock_msg.content[0].text = mock_scores
        with patch("fabiq.agents.eval_judge.get_settings") as mc,              patch("fabiq.agents.eval_judge.anthropic.AsyncAnthropic") as MA:
            mc.return_value.anthropic_key="fake"; mc.return_value.hitl_confidence_threshold=0.6
            MA.return_value.messages.create=AsyncMock(return_value=mock_msg)
            r = await eval_judge_agent(s)
        assert r["eval_accuracy"]==pytest.approx(0.9) and r["requires_human_review"] is False
