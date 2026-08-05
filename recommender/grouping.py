"""Milestone 4 -- steps 6/7 lead-in: Group Interactions by Ticket, Aggregate
Ticket Scores, Top M Candidate Tickets.

Per-interaction "match score" used for aggregation is the ANN cosine
similarity when available, falling back to the keyword ts_rank score --
both roughly 0-1, matching the diagram's own example values (0.88-0.95),
unlike the RRF fused score (which is on a tiny 1/(k+rank) scale and is only
used earlier to decide which interactions make the merged pool at all, not
as the number carried into scoring here).
"""

from __future__ import annotations

import datetime
import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from recommender.models import Interaction
from recommender.retrieval.hybrid import FusedHit


@dataclass
class TicketCandidate:
    ticket_id: uuid.UUID
    max_score: float
    topk_avg: float
    recency_score: float
    final_score: float
    matched_interaction_ids: list[uuid.UUID]  # sorted by match_score desc


def _match_score(hit: FusedHit) -> float:
    if hit.ann_score is not None:
        return hit.ann_score
    if hit.keyword_score is not None:
        return hit.keyword_score
    return 0.0


def group_and_aggregate(
    session: Session,
    fused_hits: list[FusedHit],
    top_m: int,
    top_k_for_avg: int,
    weight_max: float,
    weight_topk_avg: float,
    weight_recency: float,
    recency_half_life_days: float,
    now: datetime.datetime,
) -> list[TicketCandidate]:
    by_ticket: dict[uuid.UUID, list[tuple[float, datetime.datetime, uuid.UUID]]] = {}

    for hit in fused_hits:
        interaction = session.get(Interaction, hit.interaction_id)
        if interaction is None or interaction.ticket_id is None:
            continue
        by_ticket.setdefault(interaction.ticket_id, []).append(
            (_match_score(hit), interaction.created_at, interaction.id)
        )

    candidates: list[TicketCandidate] = []
    for ticket_id, rows in by_ticket.items():
        rows.sort(key=lambda r: r[0], reverse=True)
        scores = [r[0] for r in rows]
        max_score = scores[0]
        topk_avg = sum(scores[:top_k_for_avg]) / min(len(scores), top_k_for_avg)

        most_recent = max(r[1] for r in rows)
        if most_recent.tzinfo is None:
            most_recent = most_recent.replace(tzinfo=datetime.timezone.utc)
        age_days = max((now - most_recent).total_seconds() / 86400.0, 0.0)
        recency_score = 0.5 ** (age_days / recency_half_life_days)

        final_score = (
            weight_max * max_score
            + weight_topk_avg * topk_avg
            + weight_recency * recency_score
        )

        candidates.append(
            TicketCandidate(
                ticket_id=ticket_id,
                max_score=max_score,
                topk_avg=topk_avg,
                recency_score=recency_score,
                final_score=final_score,
                matched_interaction_ids=[r[2] for r in rows],
            )
        )

    candidates.sort(key=lambda c: c.final_score, reverse=True)
    return candidates[:top_m]
