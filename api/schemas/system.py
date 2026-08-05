from __future__ import annotations

from pydantic import BaseModel

from recommender.config import (
    AggregationConfig,
    ContextBuilderConfig,
    DecisionConfig,
    OllamaConfig,
    RerankerConfig,
    RetrievalConfig,
    ThreadDetectionConfig,
)


class DatabaseStatus(BaseModel):
    connected: bool
    error: str | None = None


class OllamaStatus(BaseModel):
    host: str
    reachable: bool
    error: str | None = None


class SystemCounts(BaseModel):
    customers: int
    tickets: int
    interactions: int
    indexed_embeddings: int


class SystemStatusResponse(BaseModel):
    embedding_model: str
    llm_model: str
    reranker_model: str
    reranker_device: str
    database: DatabaseStatus
    ollama: OllamaStatus
    counts: SystemCounts


class SystemSettingsResponse(BaseModel):
    ollama: OllamaConfig
    embedding_dimension: int
    retrieval: RetrievalConfig
    aggregation: AggregationConfig
    context_builder: ContextBuilderConfig
    reranker: RerankerConfig
    decision: DecisionConfig
    thread_detection: ThreadDetectionConfig
    database_url_display: str


class IndexInfoResponse(BaseModel):
    index_name: str
    table_name: str
    method: str
    distance_metric: str
    size_bytes: int
    size_pretty: str
    rows_indexed: int
    m: int | None = None
    ef_construction: int | None = None
    params_source: str  # "reloptions" | "assumed_pgvector_default"
