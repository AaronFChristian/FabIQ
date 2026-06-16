"""Tests for the Azure AI Search integration (RBAC and data models)."""

from __future__ import annotations

import pytest

from fabiq.retrieval.search import SearchResult, get_access_filter


class TestGetAccessFilter:
    """RBAC filter logic — no Azure credentials needed."""

    def test_field_engineer_gets_public_only(self) -> None:
        f = get_access_filter("field_engineer")
        assert "access_level eq 'public'" in f
        assert "internal" not in f
        assert "restricted" not in f

    def test_process_engineer_gets_public_and_internal(self) -> None:
        f = get_access_filter("process_engineer")
        assert "public" in f
        assert "internal" in f
        assert "restricted" not in f

    def test_admin_gets_all_levels(self) -> None:
        f = get_access_filter("admin")
        assert "public" in f
        assert "internal" in f
        assert "restricted" in f

    def test_unknown_role_defaults_to_public(self) -> None:
        f = get_access_filter("unknown_role")
        assert "public" in f
        assert "internal" not in f

    def test_filter_is_valid_odata(self) -> None:
        """Filter must use 'eq' and 'or' — OData standard used by Azure AI Search."""
        for role in ["field_engineer", "process_engineer", "admin"]:
            f = get_access_filter(role)
            assert "eq '" in f
            assert "'" in f


class TestSearchResult:
    """SearchResult dataclass construction and typing."""

    def test_construction(self) -> None:
        r = SearchResult(
            chunk_id="abc123",
            doc_id="doc001",
            content="EUV focus tolerance is ±2 nm.",
            source="manuals/euv-3400.pdf",
            page_number=42,
            access_level="internal",
            score=0.87,
            strategy="recursive",
            metadata={"version": "3.2"},
        )
        assert r.chunk_id == "abc123"
        assert r.score == pytest.approx(0.87)
        assert r.page_number == 42

    def test_metadata_is_accessible(self) -> None:
        r = SearchResult(
            chunk_id="x",
            doc_id="d",
            content="c",
            source="s",
            page_number=0,
            access_level="public",
            score=0.5,
            strategy="fixed",
            metadata={"dept": "fab"},
        )
        assert r.metadata["dept"] == "fab"
