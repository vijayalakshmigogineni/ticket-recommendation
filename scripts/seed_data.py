"""Load the manually-authored sample dataset (data/sample_dataset/seed_data.py)
into the recommender's Postgres tables. Leaves Interaction.embedding NULL --
that's populated by the offline indexing pipeline (Milestone 2), run
separately via scripts/run_indexing.py.

Deterministic UUIDs: every human-readable key in the fixture file ("C1",
"riverside_family_medicine", ...) maps to a stable uuid5 so the fixture data
itself never has to hardcode UUIDs, and re-running this script is idempotent
(upsert-by-natural-key, not insert-only).
"""

from __future__ import annotations

import datetime
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.sample_dataset.seed_data import (  # noqa: E402
    CUSTOMERS,
    INTERACTIONS,
    TICKETS,
    days_ago,
)
from recommender.db import SessionLocal  # noqa: E402
from recommender.models import Customer, Interaction, InteractionType, Ticket  # noqa: E402
from recommender.preprocessing import clean_text  # noqa: E402

NAMESPACE = uuid.UUID("a3f5e1b0-5a4e-4b8a-9c1e-2f6d8b1a7c00")


def stable_id(key: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, key)


RCM_DOMAIN = "rcmsupport.internal"

_SENDER_TO_TYPE = {
    "customer": InteractionType.CUSTOMER_EMAIL,
    "agent": InteractionType.AGENT_REPLY,
    "system": InteractionType.SYSTEM_EVENT,
}
_TYPE_OVERRIDE = {"internal_note": InteractionType.INTERNAL_NOTE}


def build_message_id(ticket_key: str, idx: int, sender: str, customer_domain: str) -> str:
    domain = customer_domain if sender == "customer" else RCM_DOMAIN
    return f"<{ticket_key.lower()}-msg{idx:02d}@{domain}>"


def main() -> None:
    session = SessionLocal()
    try:
        customers_by_key: dict[str, Customer] = {}
        for c in CUSTOMERS:
            cid = stable_id(c["key"])
            customer = session.get(Customer, cid)
            if customer is None:
                customer = Customer(id=cid, name=c["name"], inbox_email=c["inbox_email"])
                session.add(customer)
            else:
                customer.name = c["name"]
                customer.inbox_email = c["inbox_email"]
            customers_by_key[c["key"]] = customer
        session.flush()

        tickets_by_key: dict[str, Ticket] = {}
        for t in TICKETS:
            tid = stable_id(t["key"])
            ticket = session.get(Ticket, tid)
            created_at = days_ago(t["age_days"])
            closed_at = days_ago(t["closed_age_days"]) if "closed_age_days" in t else None
            if ticket is None:
                ticket = Ticket(
                    id=tid,
                    customer_id=customers_by_key[t["customer"]].id,
                    subject=t["subject"],
                    category=t["category"],
                    status=t["status"],
                    created_at=created_at,
                    closed_at=closed_at,
                )
                session.add(ticket)
            else:
                ticket.customer_id = customers_by_key[t["customer"]].id
                ticket.subject = t["subject"]
                ticket.category = t["category"]
                ticket.status = t["status"]
                ticket.created_at = created_at
                ticket.closed_at = closed_at
            tickets_by_key[t["key"]] = ticket
        session.flush()

        interaction_count = 0
        for ticket_key, thread in INTERACTIONS.items():
            ticket = tickets_by_key[ticket_key]
            customer = customers_by_key[TICKETS_BY_KEY[ticket_key]["customer"]]
            customer_domain = customer.inbox_email.split("@", 1)[1]
            prior_message_ids: list[str] = []
            conversation_id = f"<conv-{ticket_key.lower()}@{RCM_DOMAIN}>"
            base_created = ticket.created_at

            for idx, msg in enumerate(thread, start=1):
                message_id = build_message_id(ticket_key, idx, msg["sender"], customer_domain)
                interaction_id = stable_id(f"{ticket_key}-msg{idx:02d}")
                interaction_type = _TYPE_OVERRIDE.get(
                    msg["type"], _SENDER_TO_TYPE[msg["sender"]]
                )
                sender_email = (
                    customer.inbox_email if msg["sender"] == "customer" else f"agent@{RCM_DOMAIN}"
                )
                created_at = base_created + datetime.timedelta(hours=msg["offset_hours"])
                in_reply_to = prior_message_ids[-1] if prior_message_ids else None
                is_note = interaction_type == InteractionType.INTERNAL_NOTE

                interaction = session.get(Interaction, interaction_id)
                fields = dict(
                    ticket_id=ticket.id,
                    customer_id=customer.id,
                    interaction_type=interaction_type,
                    sender_email=sender_email,
                    raw_content=msg["content"],
                    clean_content=clean_text(msg["content"]),
                    message_id=message_id,
                    conversation_id=conversation_id,
                    in_reply_to=None if is_note else in_reply_to,
                    reference_message_ids=[] if is_note else list(prior_message_ids),
                    created_at=created_at,
                )
                if interaction is None:
                    session.add(Interaction(id=interaction_id, **fields))
                else:
                    for key, value in fields.items():
                        setattr(interaction, key, value)

                if not is_note:
                    prior_message_ids.append(message_id)
                interaction_count += 1

        session.commit()
        print(
            f"Seeded {len(CUSTOMERS)} customers, {len(TICKETS)} tickets, "
            f"{interaction_count} interactions."
        )
    finally:
        session.close()


TICKETS_BY_KEY = {t["key"]: t for t in TICKETS}


if __name__ == "__main__":
    main()
