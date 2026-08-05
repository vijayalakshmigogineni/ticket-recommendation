from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.deps import get_db
from api.schemas.interactions import InteractionDetailResponse, InteractionListResponse
from api.services import interactions_service
from recommender.models import InteractionType

router = APIRouter(prefix="/api/interactions", tags=["interactions"])


@router.get("", response_model=InteractionListResponse)
def list_interactions(
    ticket_id: uuid.UUID | None = None,
    customer_id: uuid.UUID | None = None,
    interaction_type: InteractionType | None = None,
    has_embedding: bool | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db),
) -> InteractionListResponse:
    return interactions_service.list_interactions(
        session, ticket_id, customer_id, interaction_type, has_embedding, limit, offset
    )


@router.get("/{interaction_id}", response_model=InteractionDetailResponse)
def get_interaction(
    interaction_id: uuid.UUID,
    top_n: int = Query(default=10, le=50),
    session: Session = Depends(get_db),
) -> InteractionDetailResponse:
    return interactions_service.get_interaction(session, interaction_id, top_n)
