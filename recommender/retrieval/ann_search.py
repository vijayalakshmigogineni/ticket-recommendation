"""Hybrid Retrieval, branch B: pgvector HNSW ANN search over interaction
embeddings, scoped to the identified customer, using cosine distance
(matches the HNSW index built with vector_cosine_ops in scripts/init_db.py).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from recommender.models import EMBEDDABLE_INTERACTION_TYPES


@dataclass
class AnnHit:
    interaction_id: uuid.UUID
    score: float  # cosine similarity, 1.0 = identical direction


_QUERY = text(
    """
    SELECT id, 1 - (embedding <=> :query_embedding) AS score
    FROM interactions
    WHERE customer_id = :customer_id
      AND interaction_type::text = ANY(:embeddable_types)
      AND embedding IS NOT NULL
    ORDER BY embedding <=> :query_embedding
    LIMIT :top_n
    """
)


def ann_search(
    session: Session,
    query_embedding: list[float],
    customer_id: uuid.UUID,
    top_n: int,
) -> list[AnnHit]:
    rows = session.execute(
        _QUERY,
        {
            "query_embedding": str(query_embedding),
            "customer_id": customer_id,
            "embeddable_types": [t.value for t in EMBEDDABLE_INTERACTION_TYPES],
            "top_n": top_n,
        },
    ).all()
    return [AnnHit(interaction_id=row.id, score=float(row.score)) for row in rows]
