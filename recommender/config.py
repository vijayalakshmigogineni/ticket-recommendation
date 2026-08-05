"""Central, config-file-driven settings for the recommendation pipeline.

Every stage reads its tunables from here rather than hardcoding them, so the
embedding model (and everything downstream of it) can be swapped by editing
config/recommender_config.yaml alone -- see EMBEDDING_MODEL_REGISTRY below.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "recommender_config.yaml"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


# Ollama embedding models this project is expected to compare later (per
# PROJECT_PLAN / user instruction). Each entry's dimension is what the model
# actually returns from Ollama's /api/embed -- required up front because a
# pgvector column has a fixed dimension at creation time. Switching models
# means re-running scripts/init_db.py + scripts/run_indexing.py to rebuild
# the embedding column/index at the new dimension; the rest of the pipeline
# (retrieval, grouping, context, rerank, decision) does not change.
EMBEDDING_MODEL_REGISTRY: dict[str, int] = {
    "nomic-embed-text": 768,
    "bge-m3": 1024,
    "mxbai-embed-large": 1024,
}


class OllamaConfig(StrictModel):
    host: str = "http://localhost:11434"
    embedding_model: str = "nomic-embed-text"
    llm_model: str = "qwen3:4b"
    request_timeout_s: float = 60.0

    @property
    def embedding_dim(self) -> int:
        try:
            return EMBEDDING_MODEL_REGISTRY[self.embedding_model]
        except KeyError as exc:
            raise ValueError(
                f"Unknown embedding_model {self.embedding_model!r}. "
                f"Add its output dimension to EMBEDDING_MODEL_REGISTRY in "
                f"recommender/config.py first."
            ) from exc


class RetrievalConfig(StrictModel):
    keyword_top_n: int = 50
    ann_top_n: int = 100
    fusion_top_n: int = 100  # size of the merged "Top N Matching Interactions" pool
    rrf_k: int = 60  # standard Reciprocal Rank Fusion damping constant


class AggregationConfig(StrictModel):
    """Weights for the per-ticket Final Score in step 6 (Group Interactions by Ticket)."""

    top_m_candidates: int = 20
    top_k_for_avg: int = 3  # "Top-K Avg" column in the architecture diagram
    weight_max: float = 0.5
    weight_topk_avg: float = 0.3
    weight_recency: float = 0.2
    recency_half_life_days: float = 14.0


class ContextBuilderConfig(StrictModel):
    neighbors_before: int = 1
    neighbors_after: int = 1
    max_matched_interactions_per_ticket: int = 2


class RerankerConfig(StrictModel):
    model_name: str = "BAAI/bge-reranker-base"
    device: str = "cpu"
    top_k: int = 3  # "Top K Candidate Tickets" after reranking


class DecisionConfig(StrictModel):
    model: str = "qwen3:4b"
    temperature: float = 0.0
    # Local generation with a "thinking" model over a multi-candidate prompt
    # can genuinely take a couple of minutes on modest hardware -- this is a
    # correctness-verification prototype, not a latency-tuned deployment.
    timeout_s: float = 180.0


class ThreadDetectionConfig(StrictModel):
    enabled: bool = True


class DatabaseConfig(StrictModel):
    url: str = "postgresql+psycopg2://postgres:postgres@localhost:5433/rcm_tickets"


class RecommenderConfig(StrictModel):
    database: DatabaseConfig = DatabaseConfig()
    ollama: OllamaConfig = OllamaConfig()
    retrieval: RetrievalConfig = RetrievalConfig()
    aggregation: AggregationConfig = AggregationConfig()
    context_builder: ContextBuilderConfig = ContextBuilderConfig()
    reranker: RerankerConfig = RerankerConfig()
    decision: DecisionConfig = DecisionConfig()
    thread_detection: ThreadDetectionConfig = ThreadDetectionConfig()


def load_config(path: Path | str | None = None) -> RecommenderConfig:
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    if not config_path.exists():
        return RecommenderConfig()
    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    cfg = RecommenderConfig(**raw)
    db_url_override = os.environ.get("RECOMMENDER_DATABASE_URL")
    if db_url_override:
        cfg.database.url = db_url_override
    ollama_host_override = os.environ.get("OLLAMA_HOST")
    if ollama_host_override:
        cfg.ollama.host = ollama_host_override
    return cfg


settings = load_config()
