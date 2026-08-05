"""Hybrid Retrieval: merge keyword + ANN ranked lists via Reciprocal Rank
Fusion into the "Top N Matching Interactions" pool the diagram hands off to
step 6 (Group Interactions by Ticket).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from recommender.retrieval.ann_search import ann_search
from recommender.retrieval.keyword_search import keyword_search


@dataclass
class FusedHit:
    interaction_id: uuid.UUID
    fused_score: float
    keyword_score: float | None
    ann_score: float | None


def reciprocal_rank_fusion(
    keyword_ids: list[uuid.UUID],
    ann_ids: list[uuid.UUID],
    keyword_scores: dict[uuid.UUID, float],
    ann_scores: dict[uuid.UUID, float],
    k: int,
    top_n: int,
) -> list[FusedHit]:
    fused: dict[uuid.UUID, float] = {}
    for rank, iid in enumerate(keyword_ids, start=1):
        fused[iid] = fused.get(iid, 0.0) + 1.0 / (k + rank)
    for rank, iid in enumerate(ann_ids, start=1):
        fused[iid] = fused.get(iid, 0.0) + 1.0 / (k + rank)

    ordered = sorted(fused.items(), key=lambda kv: kv[1], reverse=True)[:top_n]
    return [
        FusedHit(
            interaction_id=iid,
            fused_score=score,
            keyword_score=keyword_scores.get(iid),
            ann_score=ann_scores.get(iid),
        )
        for iid, score in ordered
    ]


def hybrid_retrieve(
    session: Session,
    query_text: str,
    query_embedding: list[float],
    customer_id: uuid.UUID,
    keyword_top_n: int,
    ann_top_n: int,
    rrf_k: int,
    fusion_top_n: int,
) -> list[FusedHit]:
    keyword_hits = keyword_search(session, query_text, customer_id, keyword_top_n)
    ann_hits = ann_search(session, query_embedding, customer_id, ann_top_n)

    keyword_ids = [h.interaction_id for h in keyword_hits]
    ann_ids = [h.interaction_id for h in ann_hits]
    keyword_scores = {h.interaction_id: h.score for h in keyword_hits}
    ann_scores = {h.interaction_id: h.score for h in ann_hits}

    return reciprocal_rank_fusion(
        keyword_ids, ann_ids, keyword_scores, ann_scores, k=rrf_k, top_n=fusion_top_n
    )
