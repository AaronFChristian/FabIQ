from __future__ import annotations
import logging, os
import structlog

logger = structlog.get_logger(__name__)

def configure_tracing(api_key: str, project: str, *, enabled: bool = True) -> None:
    if not enabled or not api_key:
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
        logger.info("langsmith_tracing_disabled")
        return
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = api_key
    os.environ["LANGCHAIN_PROJECT"] = project
    logger.info("langsmith_tracing_enabled", project=project)

try:
    from langsmith import traceable as _traceable
    traceable = _traceable
except ImportError:
    def _noop(func=None, *, name=None, run_type="chain", **kwargs):
        if func is None: return lambda f: f
        return func
    traceable = _noop

__all__ = ["configure_tracing", "traceable"]
