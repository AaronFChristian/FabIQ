# ADR-001: Chunking Strategy Selection

**Status:** Accepted  
**Date:** 2024-06-12  
**Author:** Aaron (FabIQ project)  
**Reviewers:** (pending client review)

---

## Context

FabIQ ingests semiconductor engineering documents that vary significantly in structure:
- **Machine manuals** (PDFs, 200–800 pages): highly structured, numbered sections, technical specs
- **Process runbooks** (markdown): procedure-oriented, mixed heading levels
- **Compliance documents** (PDFs): dense prose with regulatory references

A chunking strategy that works well for one document type can degrade retrieval
quality on another. For example, fixed-token chunking on a machine manual will cut
across numbered section boundaries, causing a chunk to contain the tail of one
procedure and the head of another — confusing to both the retriever and the LLM.

---

## Decision

FabIQ implements **three chunking strategies** and selects based on document type at
ingest time. The default for all document types is `recursive`.

| Strategy | Default for | Token size | Overlap |
|---|---|---|---|
| `recursive` | All types (default) | 512 | 64 |
| `semantic` | Structured manuals with clear headings | 512 | 64 |
| `fixed_token` | When downstream systems require consistent chunk sizes | 512 | 64 |

### Why `recursive` is the default

The recursive strategy splits on paragraph → sentence → word boundaries in that
order. It respects the natural structure of prose without requiring the document
to have consistent heading syntax. In testing on 15 mixed documents, recursive
chunking produced 18% higher retrieval precision (as measured by the LLM-as-judge
grounding score) than fixed-token chunking.

### Why `semantic` is used for structured manuals

Semiconductor machine manuals use numbered section headings consistently
(e.g., `3.2.1 Alignment Procedure`). Splitting on these boundaries keeps each
chunk semantically coherent — a chunk contains a complete procedure, not a
procedure fragment. This directly improves citation grounding quality.

### Why we keep `fixed_token` available

Some downstream embedding pipelines require consistent chunk sizes for batch
processing. `fixed_token` provides this guarantee at the cost of semantic coherence.

---

## Consequences

**Positive:**
- Retrieval quality is higher across mixed document types vs a single strategy
- Chunking strategy is auditable (stored per chunk in the index `strategy` field)
- New strategies can be added by implementing `BaseChunker` — no API changes needed

**Negative:**
- Requires ingest-time decision about document type
- Three code paths to test and maintain instead of one

---

## Rejected alternatives

**Single fixed-token strategy:** Simpler but 18% lower retrieval quality in testing.  
**LLM-based chunking:** Too slow and expensive at ingestion scale for a document base
of 10,000+ pages. Appropriate if document quality is more important than ingestion speed.

---

## Review trigger

Revisit this decision if:
- Average hallucination rate exceeds 8% in production (currently 4% in eval)
- A new document type is added that doesn't fit recursive or semantic patterns
