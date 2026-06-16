from __future__ import annotations
from functools import lru_cache
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_mode: Literal["azure", "local"] = "azure"
    local_index_path: str = "data/local_index.json"
    local_embedding_model: str = "hash"
    local_embedding_dimensions: int = 384
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True, case_sensitive=False)
    azure_openai_endpoint: str = "https://fake.openai.azure.com/"
    azure_openai_api_key: str = "fake-key"
    azure_openai_api_version: str = "2024-02-01"
    azure_openai_embedding_deployment: str = "text-embedding-3-small"
    azure_openai_chat_deployment: str = "gpt-4o-mini"
    embedding_dimensions: int = 1536
    azure_search_endpoint: str = "https://fake.search.windows.net"
    azure_search_api_key: str = "fake-key"
    azure_search_index_name: str = "fabiq-docs"
    anthropic_key: str = ""
    langsmith_api_key: str = ""
    langsmith_project: str = "fabiq"
    langsmith_tracing: bool = False
    app_name: str = "FabIQ"
    app_version: str = "0.1.0"
    log_level: Literal["DEBUG","INFO","WARNING","ERROR"] = "INFO"
    chunk_size: int = Field(512, ge=64, le=4096)
    chunk_overlap: int = Field(64, ge=0, le=512)
    embedding_batch_size: int = Field(16, ge=1, le=128)
    retrieval_top_k: int = Field(20, ge=1, le=100)
    rerank_top_k: int = Field(5, ge=1, le=20)
    hybrid_vector_weight: float = Field(0.5, ge=0.0, le=1.0)
    min_confidence_score: float = Field(0.6, ge=0.0, le=1.0)

    @property
    def hitl_confidence_threshold(self) -> float:
        return self.min_confidence_score

    @property
    def tracing_enabled(self) -> bool:
        return self.langsmith_tracing and bool(self.langsmith_api_key)

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
