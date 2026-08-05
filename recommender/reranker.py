"""Milestone 6 -- Cross-Encoder Reranker (step 8). Re-ranks the Top M
candidate tickets by running (incoming email, ticket context) through a real
cross-encoder, not a bi-encoder similarity -- this is what lets the pipeline
correct cases where embedding similarity alone over- or under-ranks a
candidate. Model is configurable (default BAAI/bge-reranker-base rather than
-large: same architecture family, smaller footprint for a correctness-
verification prototype on limited local hardware; swap to -large later for
the accuracy pass this project explicitly defers).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from functools import lru_cache

from sentence_transformers import CrossEncoder

from recommender.context_builder import TicketContext


@dataclass
class RerankedCandidate:
    ticket_id: uuid.UUID
    rerank_score: float


@lru_cache(maxsize=4)
def _load_model(model_name: str, device: str) -> CrossEncoder:
    return CrossEncoder(model_name, device=device)


def rerank(
    query_text: str,
    contexts: list[TicketContext],
    model_name: str,
    device: str,
    top_k: int,
) -> list[RerankedCandidate]:
    if not contexts:
        return []
    model = _load_model(model_name, device)
    pairs = [(query_text, context.text) for context in contexts]
    raw_scores = model.predict(pairs)

    scored = [
        RerankedCandidate(ticket_id=context.ticket_id, rerank_score=float(score))
        for context, score in zip(contexts, raw_scores)
    ]
    scored.sort(key=lambda c: c.rerank_score, reverse=True)
    return scored[:top_k]
