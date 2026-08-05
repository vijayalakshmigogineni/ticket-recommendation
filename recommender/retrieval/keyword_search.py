"""Hybrid Retrieval, branch A: PostgreSQL full-text search over interaction
content, scoped to the identified customer (a recommendation must only ever
point at that same customer's own tickets). ts_rank stands in for the
diagram's "BM25 Ranking" -- Postgres has no native BM25, ts_rank/tsvector is
the standard equivalent when the search index lives in Postgres itself.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from recommender.models import EMBEDDABLE_INTERACTION_TYPES


@dataclass
class KeywordHit:
    interaction_id: uuid.UUID
    score: float


_QUERY = text(
    """
    SELECT id, ts_rank(to_tsvector('english', clean_content), plainto_tsquery('english', :query_text)) AS score
    FROM interactions
    WHERE customer_id = :customer_id
      AND interaction_type::text = ANY(:embeddable_types)
      AND to_tsvector('english', clean_content) @@ plainto_tsquery('english', :query_text)
    ORDER BY score DESC
    LIMIT :top_n
    """
)


def keyword_search(
    session: Session, query_text: str, customer_id: uuid.UUID, top_n: int
) -> list[KeywordHit]:
    if not query_text.strip():
        return []
    rows = session.execute(
        _QUERY,
        {
            "query_text": query_text,
            "customer_id": customer_id,
            "embeddable_types": [t.value for t in EMBEDDABLE_INTERACTION_TYPES],
            "top_n": top_n,
        },
    ).all()
    return [KeywordHit(interaction_id=row.id, score=float(row.score)) for row in rows]
