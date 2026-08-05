import pytest

from generation.state import (
    ERRORED,
    INGESTED,
    PENDING,
    QA_FAIL,
    QA_PASS,
    StateStore,
    SUBMITTED,
    SUCCEEDED,
)


@pytest.fixture
def store(tmp_path):
    db_path = tmp_path / "state.sqlite3"
    s = StateStore(db_path)
    yield s
    s.close()


def test_register_pending_is_idempotent(store):
    store.register_pending("cust_1", "customers")
    store.register_pending("cust_1", "customers")  # should not error or reset
    record = store.get("cust_1")
    assert record.status == PENDING
    assert record.stage == "customers"


def test_full_lifecycle_submit_succeed_qa_pass_ingest(store):
    store.register_pending("cust_1", "customers")
    store.mark_submitted("cust_1", batch_id="batch_abc")
    assert store.get("cust_1").status == SUBMITTED
    assert store.get("cust_1").batch_id == "batch_abc"

    store.mark_succeeded("cust_1", {"name": "Acme"})
    record = store.get("cust_1")
    assert record.status == SUCCEEDED
    assert record.raw_result == {"name": "Acme"}

    store.mark_qa_verdict("cust_1", QA_PASS, {"verdict": "pass"})
    record = store.get("cust_1")
    assert record.status == QA_PASS
    assert record.qa_verdict == {"verdict": "pass"}
    assert record.retry_count == 0  # qa_pass must not increment retry_count

    store.mark_ingested("cust_1")
    assert store.get("cust_1").status == INGESTED


def test_qa_fail_increments_retry_and_requeue_resets_to_pending(store):
    store.register_pending("tkt_1_1", "tickets")
    store.mark_submitted("tkt_1_1", batch_id="batch_x")
    store.mark_succeeded("tkt_1_1", {"category": "bogus"})
    store.mark_qa_verdict("tkt_1_1", QA_FAIL, {"reason": "invalid category"})

    record = store.get("tkt_1_1")
    assert record.status == QA_FAIL
    assert record.retry_count == 1

    store.requeue_pending("tkt_1_1")
    record = store.get("tkt_1_1")
    assert record.status == PENDING
    assert record.batch_id is None
    assert record.retry_count == 1  # requeue preserves the attempt count


def test_errored_units_increment_retry_and_are_retryable(store):
    store.register_pending("q_1", "eval_queries")
    store.mark_submitted("q_1", batch_id="batch_y")
    store.mark_errored("q_1")

    assert store.get("q_1").status == ERRORED
    assert store.get("q_1").retry_count == 1

    retryable = store.retryable_units("eval_queries", max_attempts=3)
    assert [r.unit_id for r in retryable] == ["q_1"]

    permanently_failed = store.permanently_failed_units("eval_queries", max_attempts=1)
    assert [r.unit_id for r in permanently_failed] == ["q_1"]


def test_pending_and_submitted_queries_scope_by_stage(store):
    store.register_pending("cust_1", "customers")
    store.register_pending("cust_2", "customers")
    store.register_pending("tkt_1_1", "tickets")
    store.mark_submitted("cust_2", batch_id="b1")

    pending_customers = store.pending_units("customers")
    assert [r.unit_id for r in pending_customers] == ["cust_1"]

    submitted = store.submitted_units("customers")
    assert [r.unit_id for r in submitted] == ["cust_2"]

    # cross-stage submitted_units(None) should include units from any stage
    all_submitted = store.submitted_units()
    assert [r.unit_id for r in all_submitted] == ["cust_2"]


def test_stage_complete_true_only_when_all_units_terminal(store):
    store.register_pending("cust_1", "customers")
    assert store.stage_complete("customers") is False

    store.mark_submitted("cust_1", "b1")
    store.mark_succeeded("cust_1", {"name": "Acme"})
    store.mark_qa_verdict("cust_1", QA_PASS, {"verdict": "pass"})
    assert store.stage_complete("customers") is True


def test_resume_after_interruption_state_persists_across_store_instances(tmp_path):
    db_path = tmp_path / "state.sqlite3"

    store1 = StateStore(db_path)
    store1.register_pending("cust_1", "customers")
    store1.mark_submitted("cust_1", batch_id="batch_in_flight")
    store1.close()

    # Simulate process restart: open a fresh StateStore against the same file
    store2 = StateStore(db_path)
    record = store2.get("cust_1")
    assert record is not None
    assert record.status == SUBMITTED
    assert record.batch_id == "batch_in_flight"
    store2.close()
