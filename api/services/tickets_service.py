from __future__ import annotations

import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session

from api.errors import NotFoundError
from api.schemas.interactions import InteractionSummary, TicketDetailResponse
from api.schemas.tickets import TicketListResponse, TicketSummary
from recommender.models import Customer, Interaction, Ticket, TicketStatus


def _to_summary(ticket: Ticket, customer_name: str, interaction_count: int) -> TicketSummary:
    return TicketSummary(
        id=ticket.id,
        customer_id=ticket.customer_id,
        customer_name=customer_name,
        subject=ticket.subject,
        category=ticket.category,
        status=ticket.status.value,
        created_at=ticket.created_at,
        closed_at=ticket.closed_at,
        interaction_count=interaction_count,
    )


def list_tickets(
    session: Session,
    customer_id: uuid.UUID | None,
    status: TicketStatus | None,
    limit: int,
    offset: int,
) -> TicketListResponse:
    base_query = session.query(
        Ticket, Customer.name, func.count(Interaction.id)
    ).join(Customer, Customer.id == Ticket.customer_id).outerjoin(
        Interaction, Interaction.ticket_id == Ticket.id
    ).group_by(Ticket.id, Customer.name)

    if customer_id is not None:
        base_query = base_query.filter(Ticket.customer_id == customer_id)
    if status is not None:
        base_query = base_query.filter(Ticket.status == status)

    total = base_query.order_by(None).count()
    rows = base_query.order_by(Ticket.created_at.desc()).limit(limit).offset(offset).all()

    items = [_to_summary(ticket, customer_name, count) for ticket, customer_name, count in rows]
    return TicketListResponse(items=items, total=total)


def get_ticket(session: Session, ticket_id: uuid.UUID) -> TicketDetailResponse:
    ticket = session.get(Ticket, ticket_id)
    if ticket is None:
        raise NotFoundError(f"ticket {ticket_id} not found")

    interactions = (
        session.query(Interaction)
        .filter(Interaction.ticket_id == ticket_id)
        .order_by(Interaction.created_at.asc())
        .all()
    )
    interaction_count = len(interactions)
    summary = _to_summary(ticket, ticket.customer.name, interaction_count)

    interaction_items = [
        InteractionSummary(
            id=i.id,
            ticket_id=i.ticket_id,
            customer_id=i.customer_id,
            interaction_type=i.interaction_type.value,
            sender_email=i.sender_email,
            clean_content_preview=i.clean_content[:200],
            message_id=i.message_id,
            conversation_id=i.conversation_id,
            created_at=i.created_at,
            has_embedding=i.embedding is not None,
            embedding_model=i.embedding_model,
        )
        for i in interactions
    ]
    return TicketDetailResponse(ticket=summary, interactions=interaction_items)
