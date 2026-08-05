"""End-to-end smoke test on a minimal (1 customer, 1 ticket, 1 eval query)
config, per the Phase 6 plan's verification section. Uses a FakeClient in
place of the real Ollama server -- no network calls -- so this exercises the
pipeline's control flow (state transitions, QA gating, ingestion) against
real hand-crafted, schema-valid responses rather than real generated content.
A separate live smoke test against the actual local Ollama server is a
follow-up step (see tests/test_llm_client_live.py).

The Postgres ingest check runs against the same local rcm_tickets DB the
Alembic migration targeted -- confirmed empty before this test, and the rows
this test inserts are deleted at the end so the DB is left as it was found.
"""

from __future__ import annotations

import datetime

import pytest
from sqlalchemy import text

from app.database import engine
from app.enums import TicketCategory
from generation.config import DistributionsConfig, GenerationConfig, PathsConfig, RunConfig, ScaleConfig
from generation.ingest import ingest
from generation.pipeline import Pipeline
from generation.schemas import (
    ConversationBatchOutput,
    CustomerBatchOutput,
    CustomerContact,
    CustomerGenerationMetadata,
    CustomerItem,
    CustomerProductionFields,
    EvalQueryBatchOutput,
    EvalQueryScenarioItem,
    Judge1Output,
    LabelOutput,
    MessageGenerationMetadata,
    MessageItem,
    MessageProductionFields,
    TicketConversation,
    TicketGenerationMetadata,
    TicketProductionFields,
    TicketSeedBatchOutput,
    TicketSeedItem,
)


class FakeClient:
    """Stand-in for generation.llm_client.OllamaClient. Exactly one unit
    exists per stage in this minimal config, so call_sync just returns
    whatever canned response was armed via set_next() -- no need to inspect
    the request or disambiguate between concurrent units."""

    def __init__(self):
        self._next = None

    def set_next(self, response):
        self._next = response

    def call_sync(self, request):
        assert self._next is not None, "no canned response armed for this call"
        response, self._next = self._next, None
        return response


@pytest.fixture
def tiny_config(tmp_path):
    return GenerationConfig(
        run=RunConfig(name="smoke", model="qwen3:4b"),
        scale=ScaleConfig(
            customers=1,
            tickets_per_customer={"avg": 1, "min": 1, "max": 1},
            messages_per_ticket={"avg": 2, "min": 2, "max": 2},
            eval_queries=1,
        ),
        distributions=DistributionsConfig(
            category_weights={"claims": 1.0},
            category_floor=1,
            status_split={"non_terminal": 1.0, "terminal": 0.0},
            difficulty_tier_weights={"easy": 1.0},
            style={
                "tone": {"professional": 1.0},
                "length_bucket": {"short": 1.0},
                "noise_level": {"clean": 1.0},
            },
            disambiguation_customers_min=0,
        ),
        paths=PathsConfig(
            state_db=str(tmp_path / "state.sqlite3"),
            output_dir=str(tmp_path / "output"),
        ),
    )


def test_pipeline_end_to_end_with_fake_client(tiny_config):
    pipeline = Pipeline(tiny_config)
    fake = FakeClient()
    pipeline.client = fake

    try:
        manifest = pipeline.build_manifest(seed=0)
        assert manifest["customers"] == ["cust_1"]
        assert len(manifest["tickets"]) == 1
        assert len(manifest["eval_queries"]) == 1
        ticket_temp_id = manifest["tickets"][0]["temp_id"]
        eq_temp_id = manifest["eval_queries"][0]["temp_id"]
        # category is deterministic (single-key weight dict), but the specific
        # non-terminal status is still an rng.choice among 4 values -- read it
        # back rather than assuming "OPEN", or the ticket QA gate's
        # status-matches-assignment check fails.
        ticket_category = manifest["tickets"][0]["category"]
        ticket_status = manifest["tickets"][0]["status"]

        # --- customers ---
        fake.set_next(CustomerBatchOutput(customers=[
            CustomerItem(
                temp_id="placeholder",
                production_fields=CustomerProductionFields(name="Sunrise Family Medicine", inbox_email="billing@sunrise.com"),
                generation_metadata=CustomerGenerationMetadata(
                    specialty="family medicine", practice_size="small_group",
                    primary_payers=["Aetna"], pm_ehr_system="Athenahealth",
                    contacts=[CustomerContact(name="Jane Doe", role="billing coordinator", email="jane@sunrise.com")],
                ),
            )
        ]))
        customers = pipeline.run_customers()
        assert set(customers) == {"cust_1"}
        assert pipeline.state.get("cust_1").status == "qa_pass"

        # --- tickets ---
        fake.set_next(TicketSeedBatchOutput(tickets=[
            TicketSeedItem(
                temp_id=ticket_temp_id,
                production_fields=TicketProductionFields(
                    subject="Claim denied for recent visit", category=ticket_category, status=ticket_status,
                    created_at_offset_days=-5, closed_at_offset_days=None,
                ),
                generation_metadata=TicketGenerationMetadata(
                    core_issue_summary="Claim denied for missing modifier",
                    distinguishing_details="only open claims ticket for this customer",
                    claim_number="CLM-100", patient_id="PT-100", payer="Aetna",
                    date_of_service="2026-01-01", procedure_description="CPT 99214 office visit",
                ),
            )
        ]))
        tickets = pipeline.run_tickets(customers)
        assert set(tickets) == {ticket_temp_id}
        assert pipeline.state.get(ticket_temp_id).status == "qa_pass"

        # --- conversations ---
        fake.set_next(ConversationBatchOutput(conversations=[
            TicketConversation(
                ticket_temp_id=ticket_temp_id,
                messages=[
                    MessageItem(
                        production_fields=MessageProductionFields(
                            sender_type="client", sender_email="jane@sunrise.com",
                            day_offset=0, body_text="Claim CLM-100 for patient PT-100 was denied, can you check?",
                        ),
                        generation_metadata=MessageGenerationMetadata(
                            intent_type="initial_request", tone="professional",
                            length_bucket="short", noise_level="clean",
                        ),
                    ),
                    MessageItem(
                        production_fields=MessageProductionFields(
                            sender_type="account_manager", sender_email="support@rcm-vendor.com",
                            day_offset=1, body_text="Looking into CLM-100 for PT-100 now, will follow up shortly.",
                        ),
                        generation_metadata=MessageGenerationMetadata(
                            intent_type="follow_up", tone="professional",
                            length_bucket="short", noise_level="clean",
                        ),
                    ),
                ],
            )
        ]))
        conversations = pipeline.run_conversations(customers, tickets)
        assert set(conversations) == {ticket_temp_id}
        assert pipeline.state.get(ticket_temp_id).status == "qa_pass"  # ticket stage unaffected by conversation QA

        # --- judge 1 ---
        fake.set_next(Judge1Output(
            category_consistent=True, suggested_category=None, sibling_pairing_plausible=None,
            flow_issues=[], intent_mismatches=[], verdict="pass", reasoning="thread is coherent",
        ))
        pipeline.run_judge1(tickets, conversations)
        assert pipeline.state.get(f"judge1_{ticket_temp_id}").status == "qa_pass"

        # --- eval queries ---
        fake.set_next(EvalQueryBatchOutput(eval_queries=[
            EvalQueryScenarioItem(
                scenario_temp_id=eq_temp_id,
                email_text=(
                    "Hello, could you please check on the status of claim CLM-100 "
                    "for patient PT-100? It was denied again and we would like an update."
                ),
            )
        ]))
        emails = pipeline.run_eval_queries(customers, tickets, conversations)
        assert set(emails) == {eq_temp_id}
        assert pipeline.state.get(eq_temp_id).status == "qa_pass"

        # --- labels (blind judge) --- only one open ticket exists, so the
        # candidate pool has exactly one entry (label "A") regardless of shuffle.
        fake.set_next(LabelOutput(
            matched_label="A", should_match=True, difficulty_tier="easy",
            distractor_labels=[], reasoning="the email explicitly names CLM-100 and PT-100",
        ))
        labels = pipeline.run_labels(customers, tickets, emails)
        assert set(labels) == {eq_temp_id}
        assert labels[eq_temp_id].matched_label == ticket_temp_id
        assert pipeline.state.get(f"label_{eq_temp_id}").status == "qa_pass"

        # --- judge 2: no distractors exist (only one open ticket), so this
        # should be a no-op -- confirms that path doesn't error.
        pipeline.run_judge2(tickets, emails, labels)

        # --- ingest into the real local Postgres DB, then verify + clean up ---
        label_dumps = {k: v.model_dump(mode="json") for k, v in labels.items()}
        id_map = ingest(pipeline.state, customers, tickets, conversations, emails, label_dumps, manifest)

        with engine.connect() as conn:
            customer_row = conn.execute(
                text("SELECT name, inbox_email FROM customers WHERE id = :id"),
                {"id": id_map["cust_1"]},
            ).fetchone()
            assert customer_row.name == "Sunrise Family Medicine"
            assert customer_row.inbox_email == "billing@sunrise.com"

            ticket_row = conn.execute(
                text("SELECT subject, category, status FROM tickets WHERE id = :id"),
                {"id": id_map[ticket_temp_id]},
            ).fetchone()
            # Postgres's native enum column stores the Python Enum member NAME
            # (SQLAlchemy's sa.Enum default), not TicketCategory's lowercase
            # .value -- e.g. "CLAIMS" in the DB for TicketCategory.CLAIMS = "claims".
            # Reading through the ORM (app.models.Ticket) instead of raw SQL
            # deserializes this back to the correct member automatically.
            assert ticket_row.category == TicketCategory(ticket_category).name
            assert ticket_row.status == ticket_status

            message_count = conn.execute(
                text("SELECT COUNT(*) AS n FROM messages WHERE ticket_id = :id"),
                {"id": id_map[ticket_temp_id]},
            ).fetchone()
            assert message_count.n == 2

            eval_query_row = conn.execute(
                text("SELECT email_text, should_match, correct_ticket_id FROM eval_queries WHERE customer_id = :id"),
                {"id": id_map["cust_1"]},
            ).fetchone()
            assert eval_query_row.should_match is True
            assert eval_query_row.correct_ticket_id == id_map[ticket_temp_id]

        assert pipeline.state.get(ticket_temp_id).status == "ingested"
        assert pipeline.state.get(f"label_{eq_temp_id}").status == "ingested"
    finally:
        # Smoke-test cleanup: this reuses the real dev Postgres DB (confirmed
        # empty before this test ran), so the rows this test inserted are
        # removed rather than left in place for the user's first real run.
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM messages"))
            conn.execute(text("DELETE FROM eval_queries"))
            conn.execute(text("DELETE FROM tickets"))
            conn.execute(text("DELETE FROM customers"))
            conn.commit()
        pipeline.close()
