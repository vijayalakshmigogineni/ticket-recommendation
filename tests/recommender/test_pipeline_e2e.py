"""Milestone 8 -- automated end-to-end pipeline tests over the 4 hand-authored
scenarios in data/incoming_emails/test_emails.py, one per distinct path
through the online pipeline. Requires the seeded pgvector Postgres container,
local Ollama (embedding + qwen3:4b), and the cross-encoder reranker model --
slow (real local LLM/reranker inference), not a mocked unit test.
"""

from __future__ import annotations

import pytest

from data.incoming_emails.test_emails import TEST_EMAILS
from recommender.models import Ticket
from recommender.pipeline import IncomingEmail, run_pipeline
from scripts.seed_data import stable_id

pytestmark = pytest.mark.integration


def _fixture(key: str) -> dict:
    return next(e for e in TEST_EMAILS if e["key"] == key)


def _make_email(fixture: dict) -> IncomingEmail:
    return IncomingEmail(
        subject=fixture["subject"],
        body=fixture["body"],
        sender_email=fixture["sender_email"],
        message_id=fixture["message_id"],
        conversation_id=fixture["conversation_id"],
        in_reply_to=fixture["in_reply_to"],
        reference_message_ids=fixture["reference_message_ids"],
    )


def test_auto_attach_thread_reply(db_session):
    fixture = _fixture("auto_attach_thread_reply")
    result = run_pipeline(db_session, _make_email(fixture))

    assert result.path == "auto_attach"
    expected_ticket = db_session.get(Ticket, stable_id(fixture["expected"]["ticket_key"]))
    assert result.recommended_ticket_id == expected_ticket.id


def test_semantic_match_broken_thread(db_session):
    fixture = _fixture("semantic_match_broken_thread")
    result = run_pipeline(db_session, _make_email(fixture))

    assert result.path == "ai_decision"
    assert result.decision.should_attach is True
    expected_ticket = db_session.get(Ticket, stable_id(fixture["expected"]["ticket_key"]))
    assert result.recommended_ticket_id == expected_ticket.id


def test_hard_negative_new_issue(db_session):
    fixture = _fixture("hard_negative_new_issue")
    result = run_pipeline(db_session, _make_email(fixture))

    assert result.path == "ai_decision"
    assert result.decision.should_attach is False
    assert result.recommended_ticket_id is None


def test_same_customer_disambiguation(db_session):
    fixture = _fixture("same_customer_disambiguation")
    result = run_pipeline(db_session, _make_email(fixture))

    assert result.path == "ai_decision"
    assert result.decision.should_attach is True
    expected_ticket = db_session.get(Ticket, stable_id(fixture["expected"]["ticket_key"]))
    assert result.recommended_ticket_id == expected_ticket.id
