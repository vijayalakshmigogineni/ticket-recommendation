"""SQLAlchemy models for the recommendation pipeline prototype.

Deliberately separate from app/models.py (the earlier, now-superseded
Customer/Ticket/Message schema tied to a different Alembic chain). This
package's Ticket/Interaction shape follows the locked architecture diagram's
vocabulary directly -- Interaction is the single timeline row an offline
indexing job embeds and an online query retrieves against; Ticket is the
grouping unit interactions are aggregated into.

Bootstrapped via scripts/init_db.py (Base.metadata.create_all), not Alembic --
this is a throwaway-verification prototype over a small manual dataset, not a
production migration target.
"""

from __future__ import annotations

import datetime
import enum
import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    ARRAY,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from recommender.config import settings
from recommender.db import Base

EMBEDDING_DIM = settings.ollama.embedding_dim


class InteractionType(str, enum.Enum):
    CUSTOMER_EMAIL = "customer_email"
    AGENT_REPLY = "agent_reply"
    INTERNAL_NOTE = "internal_note"
    SYSTEM_EVENT = "system_event"


# Only these types carry business content worth embedding/retrieving on --
# matches the "What Gets Embedded?" box in the architecture diagram (internal
# notes and system events are explicitly excluded).
EMBEDDABLE_INTERACTION_TYPES = frozenset(
    {InteractionType.CUSTOMER_EMAIL, InteractionType.AGENT_REPLY}
)


class TicketStatus(str, enum.Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    PENDING = "PENDING"
    WAITING_FOR_CLIENT = "WAITING_FOR_CLIENT"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


TERMINAL_TICKET_STATUSES = frozenset({TicketStatus.RESOLVED, TicketStatus.CLOSED})


class ManagerDecision(str, enum.Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (UniqueConstraint("inbox_email"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(nullable=False)
    inbox_email: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

    tickets: Mapped[list["Ticket"]] = relationship(back_populates="customer")


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (Index("ix_tickets_customer_status", "customer_id", "status"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id"), index=True, nullable=False
    )
    subject: Mapped[str] = mapped_column(nullable=False)
    # Free string, not an FK/enum -- production has no schema-level constraint
    # tying ticket_type to a category taxonomy (confirmed against the real
    # application's behavior); only a frontend dropdown enforces it there.
    category: Mapped[str] = mapped_column(nullable=False)
    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus, name="ticket_status", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=TicketStatus.OPEN,
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    closed_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    customer: Mapped["Customer"] = relationship(back_populates="tickets")
    interactions: Mapped[list["Interaction"]] = relationship(back_populates="ticket")


class Interaction(Base):
    """The single polymorphic timeline row (email / reply / note / attachment
    event) an offline job embeds and the online pipeline retrieves against.
    ticket_id is nullable to mirror production's pre-ticket "pool" state, but
    this prototype's manual dataset only ever populates already-ticketed rows.
    """

    __tablename__ = "interactions"
    __table_args__ = (
        Index("ix_interactions_ticket_created", "ticket_id", "created_at"),
        Index("ix_interactions_conversation_id", "conversation_id"),
        Index("ix_interactions_message_id", "message_id", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    ticket_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tickets.id"), nullable=True
    )
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("customers.id"), nullable=True
    )
    interaction_type: Mapped[InteractionType] = mapped_column(
        Enum(InteractionType, name="interaction_type", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    sender_email: Mapped[str] = mapped_column(nullable=False)

    raw_content: Mapped[str] = mapped_column(Text, nullable=False)
    clean_content: Mapped[str] = mapped_column(Text, nullable=False)

    # Thread-detection fields (step 4 of the online pipeline) -- deterministic
    # conversation_id -> in_reply_to -> references walk, independent of the
    # embedding-based retrieval path entirely.
    message_id: Mapped[str] = mapped_column(nullable=False)
    conversation_id: Mapped[str | None] = mapped_column(nullable=True)
    in_reply_to: Mapped[str | None] = mapped_column(nullable=True)
    reference_message_ids: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)

    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(nullable=True)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

    ticket: Mapped["Ticket"] = relationship(back_populates="interactions")

    @property
    def is_embeddable(self) -> bool:
        return self.interaction_type in EMBEDDABLE_INTERACTION_TYPES


class RecommendationFeedback(Base):
    """Manager accept/reject verdict on an ai_decision-path recommendation --
    this is the ground-truth label the deferred Evaluation page's Recall@K/MRR
    would eventually score against. Denormalized (stores the email text
    inline) rather than pointing at a persisted run record, since no run log
    exists yet -- this table only ever captures the final decision, not a
    full stage-by-stage trace.
    """

    __tablename__ = "recommendation_feedback"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id"), index=True, nullable=False
    )
    sender_email: Mapped[str] = mapped_column(nullable=False)
    subject: Mapped[str] = mapped_column(nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    should_attach: Mapped[bool] = mapped_column(Boolean, nullable=False)
    recommended_ticket_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tickets.id"), nullable=True
    )
    confidence: Mapped[float] = mapped_column(nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)

    manager_decision: Mapped[ManagerDecision] = mapped_column(
        Enum(ManagerDecision, name="manager_decision", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    # Only meaningful on a REJECTED verdict -- lets the manager say which
    # ticket the email actually belonged to (or leave null for "none of
    # these"), which is far more useful ground truth than a bare reject.
    corrected_ticket_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tickets.id"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

    customer: Mapped["Customer"] = relationship()
    recommended_ticket: Mapped["Ticket | None"] = relationship(foreign_keys=[recommended_ticket_id])
    corrected_ticket: Mapped["Ticket | None"] = relationship(foreign_keys=[corrected_ticket_id])
