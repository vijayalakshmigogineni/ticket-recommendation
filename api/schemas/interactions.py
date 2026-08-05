from __future__ import annotations

import datetime
import uuid

from pydantic import BaseModel

from api.schemas.common import TicketRef
from api.schemas.tickets import TicketSummary

PREVIEW_CHARS = 200


class InteractionSummary(BaseModel):
    id: uuid.UUID
    ticket_id: uuid.UUID | None
    customer_id: uuid.UUID | None
    interaction_type: str
    sender_email: str
    clean_content_preview: str
    message_id: str
    conversation_id: str | None
    created_at: datetime.datetime
    has_embedding: bool
    embedding_model: str | None


class TicketDetailResponse(BaseModel):
    ticket: TicketSummary
    interactions: list[InteractionSummary]


class InteractionListResponse(BaseModel):
    items: list[InteractionSummary]
    total: int


class EmbeddingStats(BaseModel):
    model: str | None
    dimension: int
    norm: float
    min: float
    max: float
    preview_first_20: list[float]


class InteractionDetail(BaseModel):
    id: uuid.UUID
    ticket: TicketRef | None
    customer_id: uuid.UUID | None
    interaction_type: str
    sender_email: str
    raw_content: str
    clean_content: str
    message_id: str
    conversation_id: str | None
    in_reply_to: str | None
    reference_message_ids: list[str]
    extra_metadata: dict
    created_at: datetime.datetime
    embedding_stats: EmbeddingStats | None


class NeighborHit(BaseModel):
    interaction: InteractionSummary
    ticket: TicketRef | None
    score: float


class InteractionDetailResponse(BaseModel):
    interaction: InteractionDetail
    nearest_neighbors: list[NeighborHit]
