"""Tests for all three chunking strategies."""
from __future__ import annotations
import pytest
from fabiq.ingestion.chunker import Chunk, ChunkStrategy, chunk_document, fixed_chunk, recursive_chunk, semantic_chunk
from fabiq.ingestion.loader import RawDocument


def make_doc(content: str, doc_id: str = "test-doc-001") -> RawDocument:
    return RawDocument(
        doc_id=doc_id, content=content, source="tests/sample.pdf",
        doc_type="text", page_number=1, access_level="public",
        metadata={"filename": "sample.pdf"},
    )


class TestFixedChunk:
    def test_basic_split(self, sample_text: str) -> None:
        chunks = fixed_chunk(make_doc(sample_text), chunk_size=100, overlap=10)
        assert len(chunks) >= 2
        assert all(isinstance(c, Chunk) for c in chunks)

    def test_each_chunk_has_content(self, sample_text: str) -> None:
        chunks = fixed_chunk(make_doc(sample_text), chunk_size=150, overlap=20)
        assert all(c.content.strip() for c in chunks)

    def test_chunk_ids_are_unique(self, sample_text: str) -> None:
        chunks = fixed_chunk(make_doc(sample_text), chunk_size=100, overlap=0)
        ids = [c.chunk_id for c in chunks]
        assert len(ids) == len(set(ids))

    def test_strategy_tag(self, sample_text: str) -> None:
        chunks = fixed_chunk(make_doc(sample_text), chunk_size=200, overlap=0)
        assert all(c.strategy == "fixed" for c in chunks)

    def test_empty_document_returns_no_chunks(self) -> None:
        assert fixed_chunk(make_doc("")) == []

    def test_short_document_single_chunk(self) -> None:
        chunks = fixed_chunk(make_doc("Short text."), chunk_size=512, overlap=64)
        assert len(chunks) == 1
        assert chunks[0].content == "Short text."

    def test_doc_id_propagated(self, sample_text: str) -> None:
        chunks = fixed_chunk(make_doc(sample_text, doc_id="my-custom-id"))
        assert all(c.doc_id == "my-custom-id" for c in chunks)

    def test_access_level_propagated(self, sample_text: str) -> None:
        doc = RawDocument(doc_id="x", content=sample_text, source="s",
                          doc_type="text", access_level="restricted")
        chunks = fixed_chunk(doc)
        assert all(c.access_level == "restricted" for c in chunks)

    def test_token_estimate_nonzero(self, sample_text: str) -> None:
        chunks = fixed_chunk(make_doc(sample_text))
        assert all(c.token_estimate > 0 for c in chunks)


class TestRecursiveChunk:
    def test_basic_split(self, sample_text: str) -> None:
        chunks = recursive_chunk(make_doc(sample_text), chunk_size=150, overlap=20)
        assert len(chunks) >= 1
        assert all(c.content.strip() for c in chunks)

    def test_strategy_tag(self, sample_text: str) -> None:
        chunks = recursive_chunk(make_doc(sample_text))
        assert all(c.strategy == "recursive" for c in chunks)

    def test_chunk_size_respected(self, sample_text: str) -> None:
        chunks = recursive_chunk(make_doc(sample_text), chunk_size=200, overlap=0)
        for c in chunks:
            assert len(c.content) <= 220

    def test_paragraph_split(self) -> None:
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph with more content."
        chunks = recursive_chunk(make_doc(text), chunk_size=40, overlap=0)
        assert len(chunks) >= 2

    def test_empty_produces_no_chunks(self) -> None:
        assert recursive_chunk(make_doc("")) == []


@pytest.fixture
def fake_embed_fn():
    def _embed(texts):
        return [[float(hash(t) % 1000) / 1000.0] * 16 for t in texts]
    return _embed


class TestSemanticChunk:
    def test_produces_chunks(self, sample_text: str, fake_embed_fn) -> None:
        chunks = semantic_chunk(make_doc(sample_text), embed_fn=fake_embed_fn, chunk_size=400)
        assert len(chunks) >= 1

    def test_no_empty_chunks(self, sample_text: str, fake_embed_fn) -> None:
        chunks = semantic_chunk(make_doc(sample_text), embed_fn=fake_embed_fn)
        assert all(c.content.strip() for c in chunks)

    def test_single_sentence_document(self, fake_embed_fn) -> None:
        chunks = semantic_chunk(make_doc("Single sentence only."), embed_fn=fake_embed_fn)
        assert len(chunks) == 1

    def test_requires_embed_fn(self, sample_text: str) -> None:
        with pytest.raises(ValueError, match="embed_fn"):
            chunk_document(make_doc(sample_text), strategy="semantic")


class TestChunkDocumentDispatcher:
    @pytest.mark.parametrize("strategy", ["fixed", "recursive"])
    def test_strategies_without_embed(self, sample_text: str, strategy: ChunkStrategy) -> None:
        chunks = chunk_document(make_doc(sample_text), strategy=strategy, chunk_size=200)
        assert len(chunks) >= 1

    def test_unknown_strategy_raises(self, sample_text: str) -> None:
        with pytest.raises(ValueError, match="Unknown strategy"):
            chunk_document(make_doc(sample_text), strategy="unknown")  # type: ignore
