"""Load the Phase 1 pilot benchmark corpus (data/benchmark_pilot/) into the
recommender's Postgres tables. Mirrors scripts/seed_data.py's conventions
exactly (deterministic uuid5 IDs from human-readable keys, auto-derived
message_id/conversation_id/in_reply_to/reference_message_ids, idempotent
upsert-by-key) but uses a distinct UUID namespace so this pilot benchmark
coexists in the same database alongside the small hand-authored harness-
validation fixture in data/sample_dataset/ without any ID collision.

Leaves Interaction.embedding NULL -- populated separately by
scripts/run_indexing.py.
"""

from __future__ import annotations

import datetime
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.benchmark_pilot.customers import CUSTOMERS  # noqa: E402
from data.benchmark_pilot.tickets_interactions import INTERACTIONS, TICKETS  # noqa: E402
from recommender.db import SessionLocal  # noqa: E402
from recommender.models import Customer, Interaction, InteractionType, Ticket  # noqa: E402
from recommender.preprocessing import clean_text  # noqa: E402

# Distinct from scripts/seed_data.py's NAMESPACE (a3f5e1b0-...) so both
# datasets' deterministic UUIDs never collide in the same database.
NAMESPACE = uuid.UUID("b7e2c4d1-8f3a-4e6b-9d2c-1a5f8e3b7c40")

ANCHOR_DATE = datetime.datetime(2026, 8, 2, 9, 0, tzinfo=datetime.timezone.utc)
RCM_DOMAIN = "rcmsupport.internal"

_SENDER_TO_TYPE = {
    "customer": InteractionType.CUSTOMER_EMAIL,
    "agent": InteractionType.AGENT_REPLY,
}
_TYPE_OVERRIDE = {"internal_note": InteractionType.INTERNAL_NOTE}


def stable_id(key: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, key)


def days_ago(n: float, hour: int = 9, minute: int = 0) -> datetime.datetime:
    dt = ANCHOR_DATE - datetime.timedelta(days=n)
    return dt.replace(hour=hour, minute=minute, second=0, microsecond=0)


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
            closed_at = days_ago(t["closed_age_days"]) if t.get("closed_age_days") is not None else None
            if ticket is None:
                ticket = Ticket(
                    id=tid,
                    customer_id=customers_by_key[t["customer_key"]].id,
                    subject=t["subject"],
                    category=t["category"],
                    status=t["status"],
                    created_at=created_at,
                    closed_at=closed_at,
                )
                session.add(ticket)
            else:
                ticket.customer_id = customers_by_key[t["customer_key"]].id
                ticket.subject = t["subject"]
                ticket.category = t["category"]
                ticket.status = t["status"]
                ticket.created_at = created_at
                ticket.closed_at = closed_at
            tickets_by_key[t["key"]] = ticket
        session.flush()

        ticket_customer_key = {t["key"]: t["customer_key"] for t in TICKETS}
        interaction_count = 0

        for ticket_key, thread in INTERACTIONS.items():
            ticket = tickets_by_key[ticket_key]
            customer = customers_by_key[ticket_customer_key[ticket_key]]
            customer_domain = customer.inbox_email.split("@", 1)[1]
            prior_message_ids: list[str] = []
            conversation_id = f"<conv-{ticket_key.lower()}@{RCM_DOMAIN}>"
            base_created = ticket.created_at

            for idx, msg in enumerate(thread, start=1):
                message_id = build_message_id(ticket_key, idx, msg["sender"], customer_domain)
                interaction_id = stable_id(f"{ticket_key}-msg{idx:02d}")
                interaction_type = _TYPE_OVERRIDE.get(msg["type"], _SENDER_TO_TYPE[msg["sender"]])
                # sender_email: use the alternate contact address if the ticket
                # data explicitly requested it for this interaction, else the
                # customer's registered inbox_email / the shared agent alias.
                sender_email = msg.get("sender_email_override") or (
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
            f"Loaded {len(CUSTOMERS)} customers, {len(TICKETS)} tickets, "
            f"{interaction_count} interactions (namespace={NAMESPACE})."
        )
    finally:
        session.close()


if __name__ == "__main__":
    main()
