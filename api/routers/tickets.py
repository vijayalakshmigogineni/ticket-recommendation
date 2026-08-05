from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.deps import get_db
from api.schemas.interactions import TicketDetailResponse
from api.schemas.tickets import TicketListResponse
from api.services import tickets_service
from recommender.models import TicketStatus

router = APIRouter(prefix="/api/tickets", tags=["tickets"])


@router.get("", response_model=TicketListResponse)
def list_tickets(
    customer_id: uuid.UUID | None = None,
    status: TicketStatus | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db),
) -> TicketListResponse:
    return tickets_service.list_tickets(session, customer_id, status, limit, offset)


@router.get("/{ticket_id}", response_model=TicketDetailResponse)
def get_ticket(ticket_id: uuid.UUID, session: Session = Depends(get_db)) -> TicketDetailResponse:
    return tickets_service.get_ticket(session, ticket_id)
