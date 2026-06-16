"""
Document loader for FabIQ ingestion pipeline.
Supports PDF, markdown (.md/.mdx), and plain text.
"""
from __future__ import annotations

import hashlib
import mimetypes
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import structlog

logger = structlog.get_logger(__name__)

AccessLevel = Literal["public", "internal", "restricted"]


@dataclass(frozen=True)
class RawDocument:
    """A single unit of extracted text before chunking."""
    doc_id: str
    content: str
    source: str
    doc_type: Literal["pdf", "markdown", "text"]
    page_number: int = 0
    access_level: AccessLevel = "public"
    metadata: dict[str, str] = field(default_factory=dict)


def _make_doc_id(source: str, content_sample: str) -> str:
    raw = f"{source}::{content_sample[:256]}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def load_pdf(
    path: Path,
    *,
    access_level: AccessLevel = "public",
    extra_metadata: dict[str, str] | None = None,
) -> list[RawDocument]:
    """Extract text page-by-page from a PDF file."""
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("pypdf is required: pip install pypdf") from exc

    reader = PdfReader(str(path))
    docs: list[RawDocument] = []
    source = str(path)
    meta = extra_metadata or {}

    for page_idx, page in enumerate(reader.pages):
        text = (page.extract_text() or "").strip()
        if not text:
            continue
        doc = RawDocument(
            doc_id=_make_doc_id(source, text),
            content=text,
            source=source,
            doc_type="pdf",
            page_number=page_idx + 1,
            access_level=access_level,
            metadata={"filename": path.name, "total_pages": str(len(reader.pages)), **meta},
        )
        docs.append(doc)
    logger.info("pdf_loaded", source=source, pages_extracted=len(docs))
    return docs


def load_text(
    path: Path,
    *,
    access_level: AccessLevel = "public",
    extra_metadata: dict[str, str] | None = None,
) -> list[RawDocument]:
    """Load a plain text or markdown file as a single RawDocument."""
    source = str(path)
    content = path.read_text(encoding="utf-8", errors="replace").strip()
    if not content:
        logger.warning("text_file_empty", source=source)
        return []
    suffix = path.suffix.lower()
    doc_type: Literal["markdown", "text"] = "markdown" if suffix in {".md", ".mdx"} else "text"
    doc = RawDocument(
        doc_id=_make_doc_id(source, content),
        content=content,
        source=source,
        doc_type=doc_type,
        page_number=0,
        access_level=access_level,
        metadata={"filename": path.name, **(extra_metadata or {})},
    )
    logger.info("text_loaded", source=source, char_count=len(content))
    return [doc]


_EXTENSION_MAP: dict[str, str] = {
    ".pdf": "pdf", ".md": "markdown", ".mdx": "markdown",
    ".txt": "text", ".rst": "text",
}


def load_document(
    path: Path | str,
    *,
    access_level: AccessLevel = "public",
    extra_metadata: dict[str, str] | None = None,
) -> list[RawDocument]:
    """Auto-detect file type and load accordingly."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Document not found: {p}")
    ext = p.suffix.lower()
    doc_type = _EXTENSION_MAP.get(ext)
    if doc_type is None:
        mime, _ = mimetypes.guess_type(str(p))
        if mime == "application/pdf":
            doc_type = "pdf"
        elif mime and mime.startswith("text/"):
            doc_type = "text"
        else:
            raise ValueError(
                f"Unsupported file type: {ext!r}. Supported: {', '.join(_EXTENSION_MAP.keys())}"
            )
    if doc_type == "pdf":
        return load_pdf(p, access_level=access_level, extra_metadata=extra_metadata)
    return load_text(p, access_level=access_level, extra_metadata=extra_metadata)


def load_directory(
    directory: Path | str,
    *,
    access_level: AccessLevel = "public",
    recursive: bool = True,
    extra_metadata: dict[str, str] | None = None,
) -> list[RawDocument]:
    """Load all supported documents from a directory."""
    d = Path(directory)
    if not d.is_dir():
        raise NotADirectoryError(f"Not a directory: {d}")
    pattern = "**/*" if recursive else "*"
    docs: list[RawDocument] = []
    for p in sorted(d.glob(pattern)):
        if not p.is_file() or p.suffix.lower() not in _EXTENSION_MAP:
            continue
        try:
            docs.extend(load_document(p, access_level=access_level, extra_metadata=extra_metadata))
        except Exception as exc:
            logger.warning("document_load_error", path=str(p), error=str(exc))
    logger.info("directory_loaded", directory=str(d), documents=len(docs))
    return docs
