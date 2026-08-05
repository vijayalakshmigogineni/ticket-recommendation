"""Debug-only global (non-customer-scoped) nearest-neighbor query, used by the
debug dashboard's ANN Inspector / Embedding Explorer views. Mirrors
ann_search.py's query minus the customer_id filter -- NOT used by
run_pipeline/run_traced_pipeline, which always stay customer-scoped.
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
    score: float


_QUERY = text(
    """
    SELECT id, 1 - (embedding <=> :query_embedding) AS score
    FROM interactions
    WHERE interaction_type::text = ANY(:embeddable_types)
      AND embedding IS NOT NULL
      AND id != :exclude_id
    ORDER BY embedding <=> :query_embedding
    LIMIT :top_n
    """
)


def global_nearest_neighbors(
    session: Session,
    query_embedding: list[float],
    top_n: int,
    exclude_interaction_id: uuid.UUID | None = None,
) -> list[AnnHit]:
    rows = session.execute(
        _QUERY,
        {
            "query_embedding": str(query_embedding),
            "embeddable_types": [t.value for t in EMBEDDABLE_INTERACTION_TYPES],
            "top_n": top_n,
            "exclude_id": exclude_interaction_id or uuid.uuid4(),
        },
    ).all()
    return [AnnHit(interaction_id=row.id, score=float(row.score)) for row in rows]
