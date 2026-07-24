from __future__ import annotations

import datetime

from sqlalchemy import ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.enums import (
    DifficultyTier,
    LengthBucket,
    MessageIntent,
    NoiseLevel,
    SenderType,
    TicketCategory,
    TicketStatus,
    Tone,
)


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        default=datetime.datetime.utcnow
    )

    emails: Mapped[list["CustomerEmail"]] = relationship(back_populates="customer")
    tickets: Mapped[list["Ticket"]] = relationship(back_populates="customer")


class CustomerEmail(Base):
    """Known sender addresses for a customer. This is the lookup table the
    retrieval pipeline uses to identify which customer an incoming email
    belongs to, before any embedding/search happens."""

    __tablename__ = "customer_emails"
    __table_args__ = (UniqueConstraint("email_address"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    email_address: Mapped[str] = mapped_column(nullable=False)

    customer: Mapped["Customer"] = relationship(back_populates="emails")


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (
        # The retrieval pipeline's first real query is always "this
        # customer's open tickets" -- this composite index is what makes
        # that filter cheap.
        Index("ix_tickets_customer_status", "customer_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    subject: Mapped[str] = mapped_column(nullable=False)
    category: Mapped[TicketCategory] = mapped_column(nullable=False)
    status: Mapped[TicketStatus] = mapped_column(
        nullable=False, default=TicketStatus.OPEN
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        default=datetime.datetime.utcnow
    )
    closed_at: Mapped[datetime.datetime | None] = mapped_column(nullable=True)

    customer: Mapped["Customer"] = relationship(back_populates="tickets")
    messages: Mapped[list["Message"]] = relationship(back_populates="ticket")


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        # Backs the "most recent N interactions per ticket" query
        # (MAX_RECENT_INTERACTIONS) that the baseline retrieval scope relies on.
        Index("ix_messages_ticket_created", "ticket_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"), index=True)
    sender_type: Mapped[SenderType] = mapped_column(nullable=False)
    sender_email: Mapped[str] = mapped_column(nullable=False)
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    intent_type: Mapped[MessageIntent] = mapped_column(nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        default=datetime.datetime.utcnow
    )

    # Structured RCM identifiers, reserved for future hybrid (exact-match +
    # semantic) retrieval. Not used by the baseline embedding pipeline.
    claim_number: Mapped[str | None] = mapped_column(nullable=True)
    patient_id: Mapped[str | None] = mapped_column(nullable=True)
    payer: Mapped[str | None] = mapped_column(nullable=True)
    date_of_service: Mapped[datetime.date | None] = mapped_column(nullable=True)

    # No embedding column yet -- deliberately deferred until Phase 3/4 once
    # an embedding model (and therefore vector dimension) is chosen.

    ticket: Mapped["Ticket"] = relationship(back_populates="messages")


class EvalQuery(Base):
    """Benchmark ground truth: a synthetically generated incoming email plus
    its correct label. Used to evaluate retrieval/scoring strategies
    (Phase 6+) -- not part of the production data model."""

    __tablename__ = "eval_queries"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    email_text: Mapped[str] = mapped_column(Text, nullable=False)
    correct_ticket_id: Mapped[int | None] = mapped_column(
        ForeignKey("tickets.id"), nullable=True
    )
    should_match: Mapped[bool] = mapped_column(nullable=False)
    difficulty_tier: Mapped[DifficultyTier] = mapped_column(nullable=False)
    distractor_ticket_ids: Mapped[list[int]] = mapped_column(
        ARRAY(Integer), default=list
    )
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    tone: Mapped[Tone] = mapped_column(nullable=False)
    length_bucket: Mapped[LengthBucket] = mapped_column(nullable=False)
    noise_level: Mapped[NoiseLevel] = mapped_column(nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        default=datetime.datetime.utcnow
    )
