from __future__ import annotations

import datetime
import uuid

from pydantic import BaseModel


class TicketSummary(BaseModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    customer_name: str
    subject: str
    category: str
    status: str
    created_at: datetime.datetime
    closed_at: datetime.datetime | None
    interaction_count: int


class CustomerListItem(BaseModel):
    id: uuid.UUID
    name: str
    inbox_email: str
    ticket_count: int


class CustomerListResponse(BaseModel):
    items: list[CustomerListItem]


class CreateCustomerRequest(BaseModel):
    name: str
    inbox_email: str


class TicketListResponse(BaseModel):
    items: list[TicketSummary]
    total: int
