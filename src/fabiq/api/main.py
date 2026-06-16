from __future__ import annotations
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import structlog
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fabiq.api.models import HealthResponse, IndexStatusResponse
from fabiq.api.routes import ingest, query
from fabiq.config import get_settings
from fabiq.observability.tracing import configure_tracing

logger = structlog.get_logger(__name__)

def _configure_logging(log_level: str) -> None:
    structlog.configure(
        processors=[structlog.stdlib.add_log_level, structlog.processors.TimeStamper(fmt="iso"), structlog.processors.JSONRenderer()],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
    )
    logging.basicConfig(level=getattr(logging, log_level.upper(), logging.INFO))

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    cfg = get_settings()
    _configure_logging(cfg.log_level)
    configure_tracing(api_key=cfg.langsmith_api_key, project=cfg.langsmith_project, enabled=cfg.tracing_enabled)
    logger.info("fabiq_startup", version=cfg.app_version, app_mode=cfg.app_mode, index=cfg.azure_search_index_name, tracing=cfg.tracing_enabled)
    yield
    logger.info("fabiq_shutdown")

def create_app() -> FastAPI:
    cfg = get_settings()
    app = FastAPI(title=cfg.app_name, version=cfg.app_version, lifespan=lifespan, docs_url="/docs", redoc_url="/redoc")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST", "DELETE"], allow_headers=["*"])
    app.include_router(ingest.router)
    app.include_router(query.router)

    @app.get("/health", response_model=HealthResponse, tags=["ops"])
    async def health() -> HealthResponse:
        from fabiq.ingestion.embedder import build_openai_client
        from fabiq.retrieval.search import FabIQSearchClient
        s = get_settings()
        index_ok = False
        openai_ok = False
        messages: list[str] = []

        if s.app_mode == "local":
            try:
                from fabiq.retrieval.local_search import LocalSearchClient
                await LocalSearchClient(s).ensure_index_exists()
                index_ok = True
                openai_ok = True
                messages.append("Local mode active: Azure services are not required.")
            except Exception as exc:
                messages.append(f"Local index: {exc}")
        else:
            try:
                await FabIQSearchClient(s).ensure_index_exists()
                index_ok = True
            except Exception as exc:
                messages.append(f"Search: {exc}")
            try:
                await build_openai_client(s).models.list()
                openai_ok = True
            except Exception as exc:
                messages.append(f"OpenAI: {exc}")

        ok = index_ok and openai_ok
        return JSONResponse(
            status_code=200 if ok else 503,
            content=HealthResponse(
                status="ok" if ok else "degraded",
                version=s.app_version,
                app_mode=s.app_mode,
                index_reachable=index_ok,
                openai_reachable=openai_ok,
                message="; ".join(messages),
            ).model_dump(),
        )

    @app.get("/index/status", response_model=IndexStatusResponse, tags=["ops"])
    async def index_status() -> IndexStatusResponse:
        s = get_settings()
        if s.app_mode == "local":
            try:
                from fabiq.retrieval.local_search import LocalSearchClient
                count = await LocalSearchClient(s).get_document_count()
                return IndexStatusResponse(index_name=s.local_index_path, document_count=count, status="ready")
            except Exception:
                return IndexStatusResponse(index_name=s.local_index_path, document_count=0, status="not_found")

        from azure.core.credentials import AzureKeyCredential
        from azure.search.documents.aio import SearchClient
        try:
            async with SearchClient(endpoint=s.azure_search_endpoint, index_name=s.azure_search_index_name, credential=AzureKeyCredential(s.azure_search_api_key)) as client:
                count = await client.get_document_count()
                return IndexStatusResponse(index_name=s.azure_search_index_name, document_count=count, status="ready")
        except Exception:
            return IndexStatusResponse(index_name=s.azure_search_index_name, document_count=0, status="not_found")

    return app

app = create_app()

def run() -> None:
    uvicorn.run("fabiq.api.main:app", host="0.0.0.0", port=8000, reload=False, log_config=None)

if __name__ == "__main__":
    run()
