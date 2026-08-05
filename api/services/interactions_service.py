from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from api.errors import NotFoundError
from api.schemas.common import TicketRef
from api.schemas.interactions import (
    EmbeddingStats,
    InteractionDetail,
    InteractionDetailResponse,
    InteractionListResponse,
    InteractionSummary,
    NeighborHit,
)
from recommender.models import Interaction, InteractionType, Ticket
from recommender.retrieval.debug_search import global_nearest_neighbors

DEFAULT_NEIGHBOR_TOP_N = 10


def _to_summary(i: Interaction) -> InteractionSummary:
    return InteractionSummary(
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


def _ticket_ref(ticket: Ticket | None) -> TicketRef | None:
    if ticket is None:
        return None
    return TicketRef(
        id=ticket.id,
        subject=ticket.subject,
        category=ticket.category,
        status=ticket.status.value,
        customer_name=ticket.customer.name,
    )


def list_interactions(
    session: Session,
    ticket_id: uuid.UUID | None,
    customer_id: uuid.UUID | None,
    interaction_type: InteractionType | None,
    has_embedding: bool | None,
    limit: int,
    offset: int,
) -> InteractionListResponse:
    query = session.query(Interaction)
    if ticket_id is not None:
        query = query.filter(Interaction.ticket_id == ticket_id)
    if customer_id is not None:
        query = query.filter(Interaction.customer_id == customer_id)
    if interaction_type is not None:
        query = query.filter(Interaction.interaction_type == interaction_type)
    if has_embedding is not None:
        query = query.filter(
            Interaction.embedding.isnot(None) if has_embedding else Interaction.embedding.is_(None)
        )

    total = query.count()
    rows = query.order_by(Interaction.created_at.desc()).limit(limit).offset(offset).all()
    return InteractionListResponse(items=[_to_summary(i) for i in rows], total=total)


def get_interaction(
    session: Session, interaction_id: uuid.UUID, top_n: int = DEFAULT_NEIGHBOR_TOP_N
) -> InteractionDetailResponse:
    interaction = session.get(Interaction, interaction_id)
    if interaction is None:
        raise NotFoundError(f"interaction {interaction_id} not found")

    embedding_stats: EmbeddingStats | None = None
    neighbors: list[NeighborHit] = []

    if interaction.embedding is not None:
        vector = list(interaction.embedding)
        norm = sum(x * x for x in vector) ** 0.5
        embedding_stats = EmbeddingStats(
            model=interaction.embedding_model,
            dimension=len(vector),
            norm=norm,
            min=min(vector),
            max=max(vector),
            preview_first_20=vector[:20],
        )

        hits = global_nearest_neighbors(
            session, vector, top_n=top_n, exclude_interaction_id=interaction.id
        )
        for hit in hits:
            neighbor = session.get(Interaction, hit.interaction_id)
            if neighbor is None:
                continue
            neighbors.append(
                NeighborHit(
                    interaction=_to_summary(neighbor),
                    ticket=_ticket_ref(neighbor.ticket),
                    score=hit.score,
                )
            )

    detail = InteractionDetail(
        id=interaction.id,
        ticket=_ticket_ref(interaction.ticket),
        customer_id=interaction.customer_id,
        interaction_type=interaction.interaction_type.value,
        sender_email=interaction.sender_email,
        raw_content=interaction.raw_content,
        clean_content=interaction.clean_content,
        message_id=interaction.message_id,
        conversation_id=interaction.conversation_id,
        in_reply_to=interaction.in_reply_to,
        reference_message_ids=interaction.reference_message_ids,
        extra_metadata=interaction.extra_metadata,
        created_at=interaction.created_at,
        embedding_stats=embedding_stats,
    )
    return InteractionDetailResponse(interaction=detail, nearest_neighbors=neighbors)
