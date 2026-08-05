import pytest

from data.sample_dataset.seed_data import TICKETS
from recommender.customer_identification import identify_customer
from recommender.models import Customer, Ticket
from recommender.thread_detection import detect_thread
from scripts.seed_data import stable_id

pytestmark = pytest.mark.integration


def _ticket_by_key(key: str) -> dict:
    return next(t for t in TICKETS if t["key"] == key)


def test_identify_customer_matches_on_inbox_email(db_session):
    customer = identify_customer(db_session, "billing@riversidefamilymed.com")
    assert customer is not None
    assert customer.name == "Riverside Family Medicine"


def test_identify_customer_returns_none_for_unknown_sender(db_session):
    assert identify_customer(db_session, "someone@not-a-client.com") is None


def test_identify_customer_matches_mixed_case_stored_inbox_email(db_session):
    # Inserted with mixed case on purpose -- this is what func.lower() on the
    # column side protects against, as opposed to only lowercasing the
    # incoming sender_email.
    customer = Customer(name="Mixed Case Test Clinic", inbox_email="Billing@ExampleClinic.com")
    db_session.add(customer)
    db_session.commit()
    try:
        found = identify_customer(db_session, "billing@exampleclinic.com")
        assert found is not None
        assert found.id == customer.id
    finally:
        db_session.delete(customer)
        db_session.commit()


def test_detect_thread_matches_open_ticket_by_conversation_id(db_session):
    # C4 is OPEN in the seed data -- its conversation_id should auto-attach.
    match = detect_thread(
        db_session,
        conversation_id="<conv-c4@rcmsupport.internal>",
        in_reply_to=None,
        reference_message_ids=[],
    )
    assert match is not None
    assert match.matched_on == "conversation_id"
    expected_ticket = db_session.get(Ticket, stable_id("C4"))
    assert match.ticket.id == expected_ticket.id


def test_detect_thread_ignores_terminal_ticket_thread(db_session):
    # C2 is CLOSED in the seed data -- a reply into that thread should NOT
    # auto-attach; it must fall through to the AI pipeline instead.
    match = detect_thread(
        db_session,
        conversation_id="<conv-c2@rcmsupport.internal>",
        in_reply_to=None,
        reference_message_ids=[],
    )
    assert match is None


def test_detect_thread_returns_none_when_nothing_matches(db_session):
    match = detect_thread(
        db_session,
        conversation_id="<conv-does-not-exist@rcmsupport.internal>",
        in_reply_to="<also-does-not-exist@rcmsupport.internal>",
        reference_message_ids=[],
    )
    assert match is None
