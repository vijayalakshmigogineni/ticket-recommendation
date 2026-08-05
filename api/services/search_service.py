from __future__ import annotations

import time

from sqlalchemy.orm import Session

from api.schemas.search import VectorSearchHit, VectorSearchRequest, VectorSearchResponse
from recommender.config import settings
from recommender.models import Interaction
from recommender.ollama_client import embed_text
from recommender.retrieval.ann_search import ann_search
from recommender.retrieval.debug_search import global_nearest_neighbors

PREVIEW_CHARS = 200


def vector_search(session: Session, request: VectorSearchRequest) -> VectorSearchResponse:
    total_start = time.perf_counter()

    embed_start = time.perf_counter()
    query_embedding = embed_text(
        request.text, model=settings.ollama.embedding_model, host=settings.ollama.host
    )
    embedding_time_ms = (time.perf_counter() - embed_start) * 1000.0

    search_start = time.perf_counter()
    if request.customer_id is not None:
        # Customer-scoped: reuses the real production ann_search verbatim, so
        # this reproduces exactly what the online pipeline would retrieve.
        hits = ann_search(session, query_embedding, request.customer_id, request.top_n)
    else:
        # Global: debug-only exploration across the whole embedding space.
        hits = global_nearest_neighbors(session, query_embedding, request.top_n)
    search_time_ms = (time.perf_counter() - search_start) * 1000.0

    out_hits: list[VectorSearchHit] = []
    for hit in hits:
        interaction = session.get(Interaction, hit.interaction_id)
        if interaction is None:
            continue
        ticket = interaction.ticket
        out_hits.append(
            VectorSearchHit(
                interaction_id=hit.interaction_id,
                ticket=(
                    None
                    if ticket is None
                    else {
                        "id": ticket.id,
                        "subject": ticket.subject,
                        "category": ticket.category,
                        "status": ticket.status.value,
                        "customer_name": ticket.customer.name,
                    }
                ),
                score=hit.score,
                clean_content_preview=interaction.clean_content[:PREVIEW_CHARS],
            )
        )

    return VectorSearchResponse(
        model=settings.ollama.embedding_model,
        dimension=len(query_embedding),
        embedding_time_ms=embedding_time_ms,
        search_time_ms=search_time_ms,
        total_time_ms=(time.perf_counter() - total_start) * 1000.0,
        query_vector_preview=query_embedding[:20],
        hits=out_hits,
    )
