"""Step 2 of the online pipeline: deterministic customer identification.

Matches the incoming email's sender (From) address against Customer.inbox_email
-- case-insensitive equality, no ML involved. This mirrors the real production
lookup direction: every client sends TO the same shared RCM mailbox, so only
the sender side carries distinguishing information.
"""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from recommender.models import Customer


def identify_customer(session: Session, sender_email: str) -> Customer | None:
    normalized = sender_email.strip().lower()
    return (
        session.query(Customer)
        .filter(func.lower(Customer.inbox_email) == normalized)
        .one_or_none()
    )
