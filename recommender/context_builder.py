"""Milestone 5 -- Context Builder (step 7). For each candidate ticket, build
a compact conversation context out of matched interaction(s) plus their
immediate neighbors, merged and ordered by timestamp, with a lightweight
metadata header. Deliberately NOT a summary -- literal interaction text only,
exactly as the architecture calls for.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from recommender.models import Interaction, Ticket

_SENDER_LABEL = {
    "customer_email": "Customer",
    "agent_reply": "Agent",
    "internal_note": "Internal Note",
    "system_event": "System",
}


@dataclass
class TicketContext:
    ticket_id: uuid.UUID
    text: str


def _ticket_interactions_chronological(session: Session, ticket_id: uuid.UUID) -> list[Interaction]:
    return (
        session.query(Interaction)
        .filter(Interaction.ticket_id == ticket_id)
        .order_by(Interaction.created_at.asc())
        .all()
    )


def build_ticket_context(
    session: Session,
    ticket_id: uuid.UUID,
    matched_interaction_ids: list[uuid.UUID],
    max_matched_interactions: int,
    neighbors_before: int,
    neighbors_after: int,
) -> TicketContext:
    ticket = session.get(Ticket, ticket_id)
    timeline = _ticket_interactions_chronological(session, ticket_id)
    index_by_id = {interaction.id: idx for idx, interaction in enumerate(timeline)}

    selected_indices: set[int] = set()
    for matched_id in matched_interaction_ids[:max_matched_interactions]:
        idx = index_by_id.get(matched_id)
        if idx is None:
            continue
        lo = max(0, idx - neighbors_before)
        hi = min(len(timeline) - 1, idx + neighbors_after)
        selected_indices.update(range(lo, hi + 1))

    selected = [timeline[i] for i in sorted(selected_indices)]

    header = (
        f"Ticket ID: {ticket.id} | Customer: {ticket.customer.name} | "
        f"Status: {ticket.status.value} | Subject: {ticket.subject}"
    )
    blocks = [header]
    for interaction in selected:
        label = _SENDER_LABEL.get(interaction.interaction_type.value, interaction.interaction_type.value)
        blocks.append(f"--- Interaction ({label}) ---\n{interaction.clean_content}")

    return TicketContext(ticket_id=ticket_id, text="\n".join(blocks))
