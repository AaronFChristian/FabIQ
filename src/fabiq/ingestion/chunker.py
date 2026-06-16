from __future__ import annotations
import hashlib, re
from dataclasses import dataclass, field
from typing import Callable, Literal
import structlog
from fabiq.ingestion.loader import RawDocument
logger = structlog.get_logger(__name__)
ChunkStrategy = Literal["fixed", "recursive", "semantic"]
@dataclass
class Chunk:
    chunk_id: str; doc_id: str; content: str; chunk_index: int
    strategy: ChunkStrategy; token_estimate: int; source: str
    page_number: int; access_level: str; metadata: dict[str, str] = field(default_factory=dict)
def _chunk_id(doc_id: str, content: str, index: int) -> str:
    return hashlib.sha256(f"{doc_id}::{index}::{content[:128]}".encode()).hexdigest()[:16]
def _make_chunks(doc: RawDocument, texts: list[str], strategy: ChunkStrategy) -> list[Chunk]:
    return [Chunk(chunk_id=_chunk_id(doc.doc_id, t.strip(), i), doc_id=doc.doc_id, content=t.strip(), chunk_index=i, strategy=strategy, token_estimate=max(1, len(t)//4), source=doc.source, page_number=doc.page_number, access_level=doc.access_level, metadata=doc.metadata) for i, t in enumerate(texts) if t.strip()]
def fixed_chunk(doc: RawDocument, *, chunk_size: int = 512, overlap: int = 64) -> list[Chunk]:
    if not doc.content: return []
    segs, start = [], 0
    while start < len(doc.content):
        end = min(start + chunk_size, len(doc.content))
        segs.append(doc.content[start:end])
        if end == len(doc.content): break
        start = end - overlap
    return _make_chunks(doc, segs, "fixed")
def recursive_chunk(doc: RawDocument, *, chunk_size: int = 512, overlap: int = 64) -> list[Chunk]:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    splitter = RecursiveCharacterTextSplitter(separators=["\n\n", "\n", ". ", " ", ""], chunk_size=chunk_size, chunk_overlap=overlap, length_function=len)
    return _make_chunks(doc, splitter.split_text(doc.content), "recursive")
def _cos(a: list[float], b: list[float]) -> float:
    import math
    dot = sum(x*y for x,y in zip(a,b)); ma=math.sqrt(sum(x*x for x in a)); mb=math.sqrt(sum(x*x for x in b))
    return dot/(ma*mb) if ma and mb else 0.0
def semantic_chunk(doc: RawDocument, embed_fn: Callable[[list[str]], list[list[float]]], *, chunk_size: int = 512, breakpoint_percentile: float = 85.0, min_sentences_per_chunk: int = 2) -> list[Chunk]:
    sents = [p.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z])", doc.content.strip()) for p in s.split("\n\n") if p.strip()]
    if len(sents) <= 1: return _make_chunks(doc, [doc.content], "semantic")
    embs = embed_fn(sents)
    sims = [_cos(embs[i], embs[i+1]) for i in range(len(embs)-1)]
    sorted_s = sorted(sims); n = len(sorted_s)
    threshold = sorted_s[max(0, min(int(n*(1-breakpoint_percentile/100)), n-1))]
    chunks_raw, current = [], [sents[0]]
    for i, sim in enumerate(sims):
        nxt = sents[i+1]; ct = " ".join(current)
        if sim < threshold or len(ct)+len(nxt) > chunk_size:
            if len(current) >= min_sentences_per_chunk: chunks_raw.append(ct); current = [nxt]
            else: current.append(nxt)
        else: current.append(nxt)
    if current: chunks_raw.append(" ".join(current))
    final = []
    for t in chunks_raw:
        if len(t) > chunk_size*1.5:
            td = RawDocument(doc_id=doc.doc_id, content=t, source=doc.source, doc_type=doc.doc_type, page_number=doc.page_number, access_level=doc.access_level, metadata=doc.metadata)
            final.extend(c.content for c in recursive_chunk(td, chunk_size=chunk_size, overlap=32))
        else: final.append(t)
    return _make_chunks(doc, final, "semantic")
def chunk_document(doc: RawDocument, strategy: ChunkStrategy = "recursive", *, chunk_size: int = 512, overlap: int = 64, embed_fn: Callable[[list[str]], list[list[float]]] | None = None) -> list[Chunk]:
    match strategy:
        case "fixed": return fixed_chunk(doc, chunk_size=chunk_size, overlap=overlap)
        case "recursive": return recursive_chunk(doc, chunk_size=chunk_size, overlap=overlap)
        case "semantic":
            if embed_fn is None: raise ValueError("embed_fn is required for semantic chunking.")
            return semantic_chunk(doc, embed_fn, chunk_size=chunk_size)
        case _: raise ValueError(f"Unknown strategy: {strategy!r}. Choose: fixed, recursive, semantic")
