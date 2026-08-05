"""Milestone 2 -- Offline Interaction Indexing Pipeline.

New/updated Interaction -> Interaction Filter (embeddable types only) ->
Interaction Preprocessing -> Generate Interaction Embedding (Ollama) ->
Store in pgvector -> HNSW index (pgvector maintains this incrementally on
insert/update, so no separate rebuild step is needed here).

Runs incrementally: only rows with embedding IS NULL, or whose stored
embedding_model no longer matches the configured one (i.e. after switching
EMBEDDING_MODEL in config), get (re-)embedded.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import or_
from sqlalchemy.orm import Session

from recommender.config import settings
from recommender.models import EMBEDDABLE_INTERACTION_TYPES, Interaction
from recommender.ollama_client import embed_texts
from recommender.preprocessing import clean_text

DEFAULT_BATCH_SIZE = 16


@dataclass
class IndexingResult:
    scanned: int
    skipped_not_embeddable: int
    embedded: int


def _pending_interactions(session: Session) -> list[Interaction]:
    model = settings.ollama.embedding_model
    return (
        session.query(Interaction)
        .filter(
            Interaction.interaction_type.in_(list(EMBEDDABLE_INTERACTION_TYPES))
        )
        .filter(
            or_(
                Interaction.embedding.is_(None),
                Interaction.embedding_model != model,
            )
        )
        .all()
    )


def run_indexing(session: Session, batch_size: int = DEFAULT_BATCH_SIZE) -> IndexingResult:
    total_embeddable = (
        session.query(Interaction)
        .filter(Interaction.interaction_type.in_(list(EMBEDDABLE_INTERACTION_TYPES)))
        .count()
    )
    pending = _pending_interactions(session)

    model = settings.ollama.embedding_model
    host = settings.ollama.host

    for i in range(0, len(pending), batch_size):
        batch = pending[i : i + batch_size]
        for interaction in batch:
            interaction.clean_content = clean_text(interaction.raw_content)

        texts = [interaction.clean_content for interaction in batch]
        vectors = embed_texts(texts, model=model, host=host)

        for interaction, vector in zip(batch, vectors):
            interaction.embedding = vector
            interaction.embedding_model = model
        session.flush()

    session.commit()

    return IndexingResult(
        scanned=total_embeddable,
        skipped_not_embeddable=total_embeddable - len(pending),
        embedded=len(pending),
    )
