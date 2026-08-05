"""Step 4 of the online pipeline: deterministic thread detection.

conversation_id -> in_reply_to -> references, in that order, exactly as the
architecture diagram specifies. A hit against a thread already attached to a
NON-terminal (open) ticket means auto-attach with no AI decision at all --
the rest of the pipeline (embedding, retrieval, rerank, LLM decision) is
skipped entirely. A hit against a terminal (closed/resolved) ticket's thread
is treated as no match here -- it falls through to the AI pipeline like any
other unthreaded email, since production doesn't silently reopen a finished
ticket.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from recommender.models import TERMINAL_TICKET_STATUSES, Interaction, Ticket


@dataclass
class ThreadMatch:
    ticket: Ticket
    matched_on: str  # "conversation_id" | "in_reply_to" | "references"
    matched_interaction: Interaction


def _non_terminal_ticket_for_interaction(
    session: Session, interaction: Interaction
) -> Ticket | None:
    if interaction.ticket_id is None:
        return None
    ticket = session.get(Ticket, interaction.ticket_id)
    if ticket is None or ticket.status in TERMINAL_TICKET_STATUSES:
        return None
    return ticket


def detect_thread(
    session: Session,
    conversation_id: str | None,
    in_reply_to: str | None,
    reference_message_ids: list[str] | None,
) -> ThreadMatch | None:
    reference_message_ids = reference_message_ids or []

    if conversation_id:
        hit = (
            session.query(Interaction)
            .filter(Interaction.conversation_id == conversation_id)
            .order_by(Interaction.created_at.desc())
            .first()
        )
        if hit is not None:
            ticket = _non_terminal_ticket_for_interaction(session, hit)
            if ticket is not None:
                return ThreadMatch(ticket=ticket, matched_on="conversation_id", matched_interaction=hit)

    if in_reply_to:
        hit = (
            session.query(Interaction)
            .filter(Interaction.message_id == in_reply_to)
            .one_or_none()
        )
        if hit is not None:
            ticket = _non_terminal_ticket_for_interaction(session, hit)
            if ticket is not None:
                return ThreadMatch(ticket=ticket, matched_on="in_reply_to", matched_interaction=hit)

    for ref in reference_message_ids:
        hit = session.query(Interaction).filter(Interaction.message_id == ref).one_or_none()
        if hit is not None:
            ticket = _non_terminal_ticket_for_interaction(session, hit)
            if ticket is not None:
                return ThreadMatch(ticket=ticket, matched_on="references", matched_interaction=hit)

    return None
