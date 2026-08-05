"""Milestone 8 -- manual/CLI runner for the end-to-end pipeline. Prints every
stage's output (not just the final recommendation) against one of the
hand-authored test emails in data/incoming_emails/test_emails.py, or a
completely ad hoc email passed via --sender/--subject/--body.

Usage:
  python scripts/recommend.py --key semantic_match_broken_thread
  python scripts/recommend.py --list
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.incoming_emails.test_emails import TEST_EMAILS  # noqa: E402
from recommender.db import SessionLocal  # noqa: E402
from recommender.models import Ticket  # noqa: E402
from recommender.pipeline import IncomingEmail, run_pipeline  # noqa: E402


def _print_result(session, result) -> None:
    print(f"\n=== path: {result.path} ===")
    if result.customer is not None:
        print(f"customer: {result.customer.name} ({result.customer.inbox_email})")

    if result.path == "auto_attach":
        tm = result.thread_match
        print(f"auto-attached via {tm.matched_on} -> ticket {tm.ticket.id} "
              f"({tm.ticket.subject!r}, status={tm.ticket.status.value})")
        return

    if result.path == "unknown_customer":
        print("sender email did not match any known customer inbox_email")
        return

    print(f"\n-- top {len(result.candidates)} candidates after grouping/aggregation --")
    for c in result.candidates:
        t = session.get(Ticket, c.ticket_id)
        print(f"  final={c.final_score:.3f} max={c.max_score:.3f} topk_avg={c.topk_avg:.3f} "
              f"recency={c.recency_score:.3f}  {t.subject!r} [{t.status.value}]")

    print(f"\n-- top {len(result.reranked)} after cross-encoder rerank --")
    for r in result.reranked:
        t = session.get(Ticket, r.ticket_id)
        print(f"  rerank_score={r.rerank_score:.3f}  {t.subject!r}")

    d = result.decision
    print("\n-- LLM decision --")
    print(f"  should_attach={d.should_attach} confidence={d.confidence:.2f}")
    if d.ticket_id:
        t = session.get(Ticket, d.ticket_id)
        print(f"  ticket={t.subject!r} [{t.status.value}]")
    print(f"  explanation: {d.explanation}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--key", help="key from data/incoming_emails/test_emails.py")
    parser.add_argument("--list", action="store_true", help="list available test email keys")
    args = parser.parse_args()

    if args.list or not args.key:
        for e in TEST_EMAILS:
            print(f"{e['key']}: {e['description']}")
        return

    fixture = next((e for e in TEST_EMAILS if e["key"] == args.key), None)
    if fixture is None:
        raise SystemExit(f"no test email with key {args.key!r}")

    email = IncomingEmail(
        subject=fixture["subject"],
        body=fixture["body"],
        sender_email=fixture["sender_email"],
        message_id=fixture["message_id"],
        conversation_id=fixture["conversation_id"],
        in_reply_to=fixture["in_reply_to"],
        reference_message_ids=fixture["reference_message_ids"],
    )

    session = SessionLocal()
    try:
        print(f"--- {fixture['key']} ---\n{fixture['description']}")
        result = run_pipeline(session, email)
        _print_result(session, result)
        print(f"\nexpected: {fixture['expected']}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
