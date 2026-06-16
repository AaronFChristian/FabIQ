"""
Embedding pipeline with Azure production mode and local reviewer/demo mode.

APP_MODE=azure uses Azure OpenAI.
APP_MODE=local uses sentence-transformers when available, with a deterministic
hash fallback so the app can still run without cloud credentials.
"""
from __future__ import annotations

import asyncio
import hashlib
import math
from functools import lru_cache
from typing import Any

import structlog
from openai import AsyncAzureOpenAI, RateLimitError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from fabiq.config import Settings, get_settings
from fabiq.observability.tracing import traceable

logger = structlog.get_logger(__name__)


def build_openai_client(settings: Settings | None = None) -> AsyncAzureOpenAI:
    cfg = settings or get_settings()
    return AsyncAzureOpenAI(
        api_key=cfg.azure_openai_api_key,
        azure_endpoint=cfg.azure_openai_endpoint,
        api_version=cfg.azure_openai_api_version,
    )


@lru_cache(maxsize=2)
def _load_sentence_transformer(model_name: str) -> Any | None:
    try:
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(model_name)
    except Exception as exc:  # pragma: no cover - fallback is environment-dependent
        logger.warning("local_embedding_model_unavailable_using_hash_fallback", error=str(exc))
        return None


def _hash_embedding(text: str, dimensions: int) -> list[float]:
    """Deterministic fallback embedding for local demo mode."""
    values = [0.0] * dimensions
    tokens = [t.lower() for t in text.split() if t.strip()]
    if not tokens:
        tokens = [" "]
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        for i, byte in enumerate(digest):
            idx = (byte + i * 17) % dimensions
            values[idx] += 1.0 if byte % 2 == 0 else -1.0
    norm = math.sqrt(sum(v * v for v in values)) or 1.0
    return [v / norm for v in values]


def _local_embed_texts(texts: list[str], cfg: Settings) -> list[list[float]]:
    safe_texts = [t if t.strip() else " " for t in texts]
    model = None if cfg.local_embedding_model.lower() == "hash" else _load_sentence_transformer(cfg.local_embedding_model)
    if model is not None:
        vectors = model.encode(safe_texts, normalize_embeddings=True)
        return [list(map(float, vector)) for vector in vectors]
    return [_hash_embedding(text, cfg.local_embedding_dimensions) for text in safe_texts]


@traceable(name="embed-batch", run_type="embedding")
@retry(
    retry=retry_if_exception_type(RateLimitError),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(5),
    reraise=True,
)
async def _embed_batch(texts: list[str], client: AsyncAzureOpenAI, deployment: str) -> list[list[float]]:
    response = await client.embeddings.create(input=texts, model=deployment)
    return [item.embedding for item in sorted(response.data, key=lambda x: x.index)]


@traceable(name="embed-documents", run_type="embedding")
async def aembed_texts(
    texts: list[str],
    *,
    settings: Settings | None = None,
    client: AsyncAzureOpenAI | None = None,
) -> list[list[float]]:
    """Embed a list of texts asynchronously, processing in batches."""
    cfg = settings or get_settings()

    if not texts:
        return []

    if cfg.app_mode == "local":
        logger.info("local_embedding_start", total_texts=len(texts), model=cfg.local_embedding_model)
        return await asyncio.to_thread(_local_embed_texts, texts, cfg)

    _client = client or build_openai_client(cfg)
    deployment = cfg.azure_openai_embedding_deployment
    batch_size = cfg.embedding_batch_size

    safe_texts = [t if t.strip() else " " for t in texts]
    batches = [safe_texts[i:i + batch_size] for i in range(0, len(safe_texts), batch_size)]

    logger.info("embedding_start", total_texts=len(texts), batches=len(batches))
    all_embeddings: list[list[float]] = []
    for batch in batches:
        embeddings = await _embed_batch(batch, _client, deployment)
        all_embeddings.extend(embeddings)
    return all_embeddings


def embed_texts(texts: list[str], *, settings: Settings | None = None) -> list[list[float]]:
    """Synchronous wrapper for the async embedder. Used by the semantic chunker."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(asyncio.run, aembed_texts(texts, settings=settings)).result()
        return loop.run_until_complete(aembed_texts(texts, settings=settings))
    except RuntimeError:
        return asyncio.run(aembed_texts(texts, settings=settings))
