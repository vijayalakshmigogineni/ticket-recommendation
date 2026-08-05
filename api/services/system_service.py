from __future__ import annotations

import requests
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.errors import NotFoundError
from api.schemas.system import (
    DatabaseStatus,
    IndexInfoResponse,
    OllamaStatus,
    SystemCounts,
    SystemSettingsResponse,
    SystemStatusResponse,
)
from recommender.config import settings
from recommender.models import Customer, Interaction, Ticket

HNSW_INDEX_NAME = "ix_interactions_embedding_hnsw"
DEFAULT_HNSW_M = 16
DEFAULT_HNSW_EF_CONSTRUCTION = 64


def _mask_database_url(url: str) -> str:
    # postgresql+psycopg2://user:password@host:port/db -> postgresql+psycopg2://user:***@host:port/db
    if "@" not in url or "://" not in url:
        return url
    scheme, rest = url.split("://", 1)
    creds, host_part = rest.split("@", 1)
    user = creds.split(":", 1)[0] if ":" in creds else creds
    return f"{scheme}://{user}:***@{host_part}"


def get_system_status(session: Session) -> SystemStatusResponse:
    try:
        session.execute(text("SELECT 1"))
        database = DatabaseStatus(connected=True)
    except Exception as exc:  # noqa: BLE001 -- deliberately broad, this is a health probe
        database = DatabaseStatus(connected=False, error=str(exc))

    try:
        response = requests.get(f"{settings.ollama.host.rstrip('/')}/api/tags", timeout=3)
        response.raise_for_status()
        ollama = OllamaStatus(host=settings.ollama.host, reachable=True)
    except Exception as exc:  # noqa: BLE001
        ollama = OllamaStatus(host=settings.ollama.host, reachable=False, error=str(exc))

    if database.connected:
        counts = SystemCounts(
            customers=session.query(Customer).count(),
            tickets=session.query(Ticket).count(),
            interactions=session.query(Interaction).count(),
            indexed_embeddings=session.query(Interaction)
            .filter(Interaction.embedding.isnot(None))
            .count(),
        )
    else:
        counts = SystemCounts(customers=0, tickets=0, interactions=0, indexed_embeddings=0)

    return SystemStatusResponse(
        embedding_model=settings.ollama.embedding_model,
        llm_model=settings.decision.model,
        reranker_model=settings.reranker.model_name,
        reranker_device=settings.reranker.device,
        database=database,
        ollama=ollama,
        counts=counts,
    )


def get_system_settings() -> SystemSettingsResponse:
    return SystemSettingsResponse(
        ollama=settings.ollama,
        embedding_dimension=settings.ollama.embedding_dim,
        retrieval=settings.retrieval,
        aggregation=settings.aggregation,
        context_builder=settings.context_builder,
        reranker=settings.reranker,
        decision=settings.decision,
        thread_detection=settings.thread_detection,
        database_url_display=_mask_database_url(settings.database.url),
    )


def _parse_reloption_int(reloptions: list[str] | None, key: str) -> int | None:
    if not reloptions:
        return None
    for opt in reloptions:
        if opt.startswith(f"{key}="):
            return int(opt.split("=", 1)[1])
    return None


def get_index_info(session: Session) -> IndexInfoResponse:
    row = session.execute(
        text(
            """
            SELECT
                c.relname AS index_name,
                t.relname AS table_name,
                am.amname AS method,
                c.reloptions AS reloptions,
                pg_relation_size(c.oid) AS size_bytes,
                pg_size_pretty(pg_relation_size(c.oid)) AS size_pretty
            FROM pg_class c
            JOIN pg_index i ON i.indexrelid = c.oid
            JOIN pg_class t ON t.oid = i.indrelid
            JOIN pg_am am ON am.oid = c.relam
            WHERE c.relname = :index_name
            """
        ),
        {"index_name": HNSW_INDEX_NAME},
    ).mappings().first()

    if row is None:
        raise NotFoundError(f"index {HNSW_INDEX_NAME!r} does not exist -- has scripts/init_db.py been run?")

    rows_indexed = session.query(Interaction).filter(Interaction.embedding.isnot(None)).count()

    m = _parse_reloption_int(row["reloptions"], "m")
    ef_construction = _parse_reloption_int(row["reloptions"], "ef_construction")
    params_source = "reloptions"
    if m is None:
        m = DEFAULT_HNSW_M
        params_source = "assumed_pgvector_default"
    if ef_construction is None:
        ef_construction = DEFAULT_HNSW_EF_CONSTRUCTION
        params_source = "assumed_pgvector_default"

    return IndexInfoResponse(
        index_name=row["index_name"],
        table_name=row["table_name"],
        method=row["method"],
        distance_metric="cosine",
        size_bytes=row["size_bytes"],
        size_pretty=row["size_pretty"],
        rows_indexed=rows_indexed,
        m=m,
        ef_construction=ef_construction,
        params_source=params_source,
    )
