"""Tests for the document loader module."""
from __future__ import annotations
from pathlib import Path
import pytest
from fabiq.ingestion.loader import RawDocument, load_directory, load_document, load_text


class TestLoadText:
    def test_markdown_file(self, tmp_path: Path) -> None:
        md = tmp_path / "spec.md"
        md.write_text("# EUV Spec\n\nAlignment tolerance: ±2 nm.")
        docs = load_text(md)
        assert len(docs) == 1
        assert docs[0].doc_type == "markdown"
        assert "±2 nm" in docs[0].content

    def test_plain_text_file(self, tmp_path: Path) -> None:
        txt = tmp_path / "notes.txt"
        txt.write_text("Wafer throughput: 125 wph.")
        docs = load_text(txt)
        assert len(docs) == 1
        assert docs[0].doc_type == "text"

    def test_access_level_propagated(self, tmp_path: Path) -> None:
        f = tmp_path / "internal.md"
        f.write_text("Internal process parameters.")
        docs = load_text(f, access_level="internal")
        assert docs[0].access_level == "internal"

    def test_extra_metadata(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.txt"
        f.write_text("Content here.")
        docs = load_text(f, extra_metadata={"department": "fab-ops"})
        assert docs[0].metadata.get("department") == "fab-ops"

    def test_empty_file_returns_empty(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.md"
        f.write_text("")
        docs = load_text(f)
        assert docs == []

    def test_doc_id_is_deterministic(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("Same content for both calls.")
        docs_1 = load_text(f)
        docs_2 = load_text(f)
        assert docs_1[0].doc_id == docs_2[0].doc_id

    def test_filename_in_metadata(self, tmp_path: Path) -> None:
        f = tmp_path / "spec-sheet.md"
        f.write_text("Content.")
        docs = load_text(f)
        assert docs[0].metadata.get("filename") == "spec-sheet.md"


class TestLoadDocument:
    def test_dispatch_markdown(self, tmp_path: Path) -> None:
        f = tmp_path / "readme.md"
        f.write_text("# Title\n\nBody text here.")
        docs = load_document(f)
        assert docs[0].doc_type == "markdown"

    def test_dispatch_text(self, tmp_path: Path) -> None:
        f = tmp_path / "log.txt"
        f.write_text("Log entry 001.")
        docs = load_document(str(f))
        assert docs[0].doc_type == "text"

    def test_unsupported_extension_raises(self, tmp_path: Path) -> None:
        f = tmp_path / "archive.zip"
        f.write_bytes(b"PK\x03\x04")
        with pytest.raises(ValueError, match="Unsupported file type"):
            load_document(f)

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_document(tmp_path / "does_not_exist.md")


class TestLoadDirectory:
    def test_loads_mixed_types(self, tmp_path: Path) -> None:
        (tmp_path / "a.md").write_text("Markdown content.")
        (tmp_path / "b.txt").write_text("Text content.")
        (tmp_path / "ignored.zip").write_bytes(b"PK")
        docs = load_directory(tmp_path)
        assert len(docs) == 2

    def test_recursive_search(self, tmp_path: Path) -> None:
        sub = tmp_path / "subdir"
        sub.mkdir()
        (sub / "deep.md").write_text("Deep content.")
        (tmp_path / "top.md").write_text("Top content.")
        docs = load_directory(tmp_path, recursive=True)
        assert len(docs) == 2

    def test_non_recursive(self, tmp_path: Path) -> None:
        sub = tmp_path / "subdir"
        sub.mkdir()
        (sub / "deep.md").write_text("Deep content.")
        (tmp_path / "top.md").write_text("Top content.")
        docs = load_directory(tmp_path, recursive=False)
        assert len(docs) == 1

    def test_not_a_directory_raises(self, tmp_path: Path) -> None:
        f = tmp_path / "file.txt"
        f.write_text("x")
        with pytest.raises(NotADirectoryError):
            load_directory(f)

    def test_access_level_applied_to_all(self, tmp_path: Path) -> None:
        (tmp_path / "a.md").write_text("Doc A.")
        (tmp_path / "b.md").write_text("Doc B.")
        docs = load_directory(tmp_path, access_level="restricted")
        assert all(d.access_level == "restricted" for d in docs)
