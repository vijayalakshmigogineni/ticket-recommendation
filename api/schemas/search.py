from __future__ import annotations

import uuid

from pydantic import BaseModel

from api.schemas.common import TicketRef


class VectorSearchRequest(BaseModel):
    text: str
    customer_id: uuid.UUID | None = None
    top_n: int = 20


class VectorSearchHit(BaseModel):
    interaction_id: uuid.UUID
    ticket: TicketRef | None
    score: float
    clean_content_preview: str


class VectorSearchResponse(BaseModel):
    model: str
    dimension: int
    embedding_time_ms: float
    search_time_ms: float
    total_time_ms: float
    query_vector_preview: list[float]
    hits: list[VectorSearchHit]
