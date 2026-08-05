"""Reads QA-passed production_fields from the state store and writes them into
Postgres via the existing app.database / app.models ORM. generation_metadata is
dropped at this boundary -- never inserted (see docs/execution_roadmap.md
Phase 6). temp_id -> real serial ID mapping happens here since it's the first
point real IDs exist.
"""

from __future__ import annotations

import datetime

from app.database import SessionLocal
from app.enums import (
    DifficultyTier,
    LengthBucket,
    NoiseLevel,
    SenderType,
    TicketCategory,
    TicketStatus,
    Tone,
)
from app.models import Customer, EvalQuery, Message, Ticket
from generation.state import StateStore


def _offset_to_datetime(offset_days: int | None) -> datetime.datetime | None:
    if offset_days is None:
        return None
    return datetime.datetime.utcnow() + datetime.timedelta(days=offset_days)


def ingest(
    state: StateStore,
    customers: dict[str, dict],
    tickets: dict[str, dict],
    conversations: dict[str, dict],
    eval_query_emails: dict[str, str],
    labels: dict[str, dict],
    manifest: dict,
) -> dict[str, int]:
    """labels: {eval_query_temp_id: LabelOutput.model_dump()} as returned by
    Pipeline.run_labels (already keyed by the bare eval-query temp_id, not the
    "label_"-prefixed state unit_id used during generation)."""
    """Returns the temp_id -> real DB id mapping for customers and tickets
    (needed by EvalQuery's correct_ticket_id / distractor_ticket_ids FKs)."""
    id_map: dict[str, int] = {}
    session = SessionLocal()
    try:
        for cust_temp_id, item in customers.items():
            prod = item["production_fields"]
            customer = Customer(name=prod["name"], inbox_email=prod["inbox_email"])
            session.add(customer)
            session.flush()
            id_map[cust_temp_id] = customer.id
            state.mark_ingested(cust_temp_id)

        assignments_by_id = {a["temp_id"]: a for a in manifest["tickets"]}
        for tkt_temp_id, item in tickets.items():
            if tkt_temp_id not in conversations:
                continue
            prod = item["production_fields"]
            cust_temp_id = assignments_by_id[tkt_temp_id]["customer_temp_id"]
            if cust_temp_id not in id_map:
                continue
            ticket_created_at = (
                _offset_to_datetime(prod["created_at_offset_days"]) or datetime.datetime.utcnow()
            )
            ticket = Ticket(
                customer_id=id_map[cust_temp_id],
                subject=prod["subject"],
                category=TicketCategory(prod["category"]),
                status=TicketStatus(prod["status"]),
                created_at=ticket_created_at,
                closed_at=_offset_to_datetime(prod.get("closed_at_offset_days")),
            )
            session.add(ticket)
            session.flush()
            id_map[tkt_temp_id] = ticket.id
            state.mark_ingested(tkt_temp_id)

            for msg in conversations[tkt_temp_id]["messages"]:
                mprod = msg["production_fields"]
                # day_offset is days since ticket creation (0 = created_at), per
                # Template 3 -- not an absolute offset from today like the
                # ticket seed's own created_at_offset_days/closed_at_offset_days.
                session.add(
                    Message(
                        ticket_id=ticket.id,
                        sender_type=SenderType(mprod["sender_type"]),
                        sender_email=mprod["sender_email"],
                        body_text=mprod["body_text"],
                        created_at=ticket_created_at + datetime.timedelta(days=mprod["day_offset"]),
                    )
                )
            state.mark_ingested(f"conv_{tkt_temp_id}")

        scenarios_by_id = {s["temp_id"]: s for s in manifest["eval_queries"]}
        for eq_temp_id, label in labels.items():
            email_text = eval_query_emails.get(eq_temp_id)
            scenario = scenarios_by_id.get(eq_temp_id)
            if email_text is None or scenario is None:
                continue
            customer_id = id_map.get(scenario["customer_temp_id"])
            if customer_id is None:
                continue
            correct_ticket_id = id_map.get(label["matched_label"]) if label.get("matched_label") else None
            distractor_ids = [
                id_map[d] for d in label.get("distractor_labels", []) if d in id_map
            ]
            session.add(
                EvalQuery(
                    customer_id=customer_id,
                    email_text=email_text,
                    correct_ticket_id=correct_ticket_id,
                    should_match=label["should_match"],
                    difficulty_tier=DifficultyTier(label["difficulty_tier"]),
                    distractor_ticket_ids=distractor_ids,
                    reasoning=label["reasoning"],
                    tone=Tone(scenario["tone"]),
                    length_bucket=LengthBucket(scenario["length_bucket"]),
                    noise_level=NoiseLevel(scenario["noise_level"]),
                )
            )
            state.mark_ingested(f"label_{eq_temp_id}")

        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    return id_map
