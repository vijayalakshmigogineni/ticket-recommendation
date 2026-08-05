from __future__ import annotations

import datetime

from sqlalchemy import ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.enums import (
    DifficultyTier,
    LengthBucket,
    NoiseLevel,
    SenderType,
    TicketCategory,
    TicketStatus,
    Tone,
)


class Customer(Base):
    """Maps to the real production system's `clients` table: name +
    inbox_email are real, persisted fields. There is no separate
    "known contacts" table in production -- individual staff addresses
    vary per message (see Message.sender_email) but aren't tracked as a
    first-class roster; only the client's own inbox_email is a real,
    unique, persisted anchor.

    Lookup direction (confirmed): every client sends TO the same shared
    RCM mailbox (our Graph-monitored intake address -- the same one
    Message.sender_email uses for account_manager replies), so the
    recipient address carries no distinguishing information at all.
    Customer identification is performed on the SENDER side instead --
    matching an incoming email's From address against this customer's
    inbox_email. inbox_email is the client's own recognizable address,
    not a per-client mailbox we host for them to send into.

    See docs/generation_prompts.md Template 1 for the generation-only
    customer profile fields (specialty, practice_size, primary_payers,
    pm_ehr_system, contacts) that never reach this table.
    """

    __tablename__ = "customers"
    __table_args__ = (UniqueConstraint("inbox_email"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    inbox_email: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        default=datetime.datetime.utcnow
    )

    tickets: Mapped[list["Ticket"]] = relationship(back_populates="customer")


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (
        # The retrieval pipeline's first real query is always "this
        # customer's open tickets" -- this composite index is what makes
        # that filter cheap. "Open" means non-terminal status (see
        # TERMINAL_TICKET_STATUSES in app/enums.py), not literally
        # status == OPEN -- IN_PROGRESS/PENDING/WAITING_FOR_CLIENT tickets
        # are still live and re-matchable.
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
    created_at: Mapped[datetime.datetime] = mapped_column(
        default=datetime.datetime.utcnow
    )

    # No embedding column yet -- deliberately deferred until Phase 3/4 once
    # an embedding model (and therefore vector dimension) is chosen.
    #
    # No intent_type / claim_number / patient_id / payer / date_of_service
    # columns: the real production system has no matching fields (message
    # intent isn't tracked at all; structured claim/patient facts, if
    # captured, live inside an unstructured payload blob, not typed
    # columns). These remain generation-time-only concerns -- used to keep
    # synthetic threads realistic and internally consistent while writing
    # body_text -- not persisted here.

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
