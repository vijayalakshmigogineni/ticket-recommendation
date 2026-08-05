"""Shared response shapes referenced by multiple routers."""

from __future__ import annotations

import uuid

from pydantic import BaseModel


class TicketRef(BaseModel):
    id: uuid.UUID
    subject: str
    category: str
    status: str
    customer_name: str


class CustomerRef(BaseModel):
    id: uuid.UUID
    name: str
    inbox_email: str
