from __future__ import annotations

import datetime
import uuid
from typing import Literal

from pydantic import BaseModel

from api.schemas.common import CustomerRef, TicketRef


class RecordFeedbackRequest(BaseModel):
    customer_id: uuid.UUID
    sender_email: str
    subject: str
    body: str
    should_attach: bool
    recommended_ticket_id: uuid.UUID | None = None
    confidence: float
    explanation: str
    manager_decision: Literal["accepted", "rejected"]
    corrected_ticket_id: uuid.UUID | None = None
    notes: str | None = None


class FeedbackRecord(BaseModel):
    id: uuid.UUID
    customer: CustomerRef
    sender_email: str
    subject: str
    body: str
    should_attach: bool
    recommended_ticket: TicketRef | None
    confidence: float
    explanation: str
    manager_decision: Literal["accepted", "rejected"]
    corrected_ticket: TicketRef | None
    notes: str | None
    created_at: datetime.datetime


class FeedbackListResponse(BaseModel):
    items: list[FeedbackRecord]
    total: int
