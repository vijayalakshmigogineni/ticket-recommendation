from generation.qa.rules import (
    FAIL,
    FLAG,
    check_broke_character,
    check_conversation,
    check_customer,
    check_distractor_prefilter,
    check_eval_query,
    check_ground_truth_match,
    check_hard_negative,
    check_style_tags,
    check_ticket_seed,
    check_tier_conformance,
)


def make_customer(name="Sunrise Family Medicine", inbox_email="billing@sunrise.com"):
    return {
        "temp_id": "cust_1",
        "production_fields": {"name": name, "inbox_email": inbox_email},
        "generation_metadata": {
            "specialty": "family medicine",
            "practice_size": "small_group",
            "primary_payers": ["Aetna"],
            "pm_ehr_system": "Athenahealth",
            "contacts": [{"name": "Jane Doe", "role": "billing coordinator", "email": "jane@sunrise.com"}],
        },
    }


def test_check_customer_valid_passes_clean():
    customer = make_customer()
    findings = check_customer(customer, batch_inbox_emails=["billing@sunrise.com"], avoid_names=[])
    assert findings == []


def test_check_customer_invalid_email_fails():
    customer = make_customer(inbox_email="not-an-email")
    findings = check_customer(customer, batch_inbox_emails=["not-an-email"], avoid_names=[])
    assert any(f.check == "email_format" and f.severity == FAIL for f in findings)


def test_check_customer_duplicate_inbox_email_in_batch_fails():
    customer = make_customer()
    findings = check_customer(
        customer,
        batch_inbox_emails=["billing@sunrise.com", "billing@sunrise.com"],
        avoid_names=[],
    )
    assert any(f.check == "duplicate_inbox_email" for f in findings)


def test_check_customer_missing_contacts_fails():
    customer = make_customer()
    customer["generation_metadata"]["contacts"] = []
    findings = check_customer(customer, batch_inbox_emails=[customer["production_fields"]["inbox_email"]], avoid_names=[])
    assert any(f.check == "required_fields" and f.severity == FAIL for f in findings)


def make_ticket(category="claims", status="OPEN", created_offset=-10, closed_offset=None,
                 claim_number="CLM-1", patient_id="PT-1"):
    return {
        "temp_id": "tkt_1_1",
        "production_fields": {
            "subject": "Claim denied",
            "category": category,
            "status": status,
            "created_at_offset_days": created_offset,
            "closed_at_offset_days": closed_offset,
        },
        "generation_metadata": {
            "core_issue_summary": "denial",
            "distinguishing_details": "unique cause",
            "claim_number": claim_number,
            "patient_id": patient_id,
            "payer": "Aetna",
            "date_of_service": "2026-01-01",
            "procedure_description": "office visit",
        },
    }


def test_check_ticket_seed_valid_open_ticket_passes():
    ticket = make_ticket()
    assignment = {"category": "claims", "status": "OPEN"}
    findings = check_ticket_seed(ticket, assignment)
    assert findings == []


def test_check_ticket_seed_invalid_category_fails():
    ticket = make_ticket(category="bogus_category")
    assignment = {"category": "bogus_category", "status": "OPEN"}
    findings = check_ticket_seed(ticket, assignment)
    assert any(f.check == "category_valid" and f.severity == FAIL for f in findings)


def test_check_ticket_seed_category_mismatch_with_assignment_fails():
    ticket = make_ticket(category="claims")
    assignment = {"category": "payment_posting", "status": "OPEN"}
    findings = check_ticket_seed(ticket, assignment)
    assert any(f.check == "category_matches_assignment" for f in findings)


def test_closed_ticket_missing_closed_offset_fails():
    ticket = make_ticket(status="CLOSED", created_offset=-20, closed_offset=None)
    assignment = {"category": "claims", "status": "CLOSED"}
    findings = check_ticket_seed(ticket, assignment)
    assert any(f.check == "closed_date_logic" and f.severity == FAIL for f in findings)


def test_closed_ticket_closed_before_created_fails():
    # pilot/qa_report.md finding #1 -- this is exactly the bug that was caught
    ticket = make_ticket(status="CLOSED", created_offset=-10, closed_offset=-20)
    assignment = {"category": "claims", "status": "CLOSED"}
    findings = check_ticket_seed(ticket, assignment)
    assert any(f.check == "closed_date_logic" and f.severity == FAIL for f in findings)


def test_non_terminal_ticket_with_closed_offset_set_fails():
    ticket = make_ticket(status="OPEN", closed_offset=-5)
    assignment = {"category": "claims", "status": "OPEN"}
    findings = check_ticket_seed(ticket, assignment)
    assert any(f.check == "closed_date_logic" for f in findings)


def test_sibling_with_identical_claim_number_fails():
    ticket = make_ticket(claim_number="CLM-SAME")
    sibling = make_ticket(claim_number="CLM-SAME")
    findings = check_ticket_seed(ticket, {"category": "claims", "status": "OPEN"}, sibling_seeds=[sibling])
    assert any(f.check == "sibling_distinctness" for f in findings)


def make_message(sender_type, intent_type, day_offset, body_text="hi", tone="professional",
                  length_bucket="short", noise_level="clean"):
    return {
        "production_fields": {
            "sender_type": sender_type,
            "sender_email": "a@b.com",
            "day_offset": day_offset,
            "body_text": body_text,
        },
        "generation_metadata": {
            "intent_type": intent_type,
            "tone": tone,
            "length_bucket": length_bucket,
            "noise_level": noise_level,
        },
    }


def test_conversation_valid_thread_passes():
    ticket = make_ticket(status="OPEN")
    conversation = {
        "ticket_temp_id": "tkt_1_1",
        "messages": [
            make_message("client", "initial_request", 0, body_text="CLM-1 for PT-1 denied"),
            make_message("account_manager", "follow_up", 1),
            make_message("client", "thank_you", 2),
        ],
    }
    findings = check_conversation(ticket, conversation)
    assert findings == []


def test_conversation_first_message_not_client_fails():
    ticket = make_ticket()
    conversation = {
        "messages": [
            make_message("account_manager", "initial_request", 0),
        ],
    }
    findings = check_conversation(ticket, conversation)
    assert any(f.check == "message_1_structure" for f in findings)


def test_conversation_day_offset_decreasing_fails():
    ticket = make_ticket()
    conversation = {
        "messages": [
            make_message("client", "initial_request", 0, body_text="CLM-1 PT-1"),
            make_message("account_manager", "follow_up", 5),
            make_message("client", "follow_up", 2),
        ],
    }
    findings = check_conversation(ticket, conversation)
    assert any(f.check == "day_offsets_non_decreasing" for f in findings)


def test_conversation_grounding_facts_not_echoed_fails():
    ticket = make_ticket(claim_number="CLM-999")
    conversation = {
        "messages": [
            make_message("client", "initial_request", 0, body_text="my claim is denied, no number mentioned"),
        ],
    }
    findings = check_conversation(ticket, conversation)
    assert any(f.check == "grounding_facts_echoed" for f in findings)


def test_check_eval_query_leakage_detects_category_and_tier_literals():
    findings = check_eval_query("this is a hard_semantic query about claims")
    checks = {f.check for f in findings}
    assert "label_leakage" in checks


def test_check_eval_query_clean_text_passes():
    findings = check_eval_query("hey can you check on my claim, aetna denied it again")
    assert findings == []


def test_check_broke_character_detects_refusal():
    findings = check_broke_character("As an AI, I cannot generate real PII.")
    assert findings and findings[0].severity == FAIL


def test_check_style_tags_length_mismatch_flags():
    long_text = " ".join(["word"] * 150)
    findings = check_style_tags(long_text, tone="professional", length_bucket="short", noise_level="clean")
    assert any(f.check == "length_bucket_conformance" for f in findings)


def test_check_ground_truth_match_agreement_passes():
    assert check_ground_truth_match("tkt_1_1", "tkt_1_1") == []


def test_check_ground_truth_match_disagreement_fails():
    findings = check_ground_truth_match("tkt_1_1", "tkt_1_2")
    assert findings and findings[0].severity == FAIL


def test_check_tier_conformance_mismatch_flags():
    findings = check_tier_conformance("easy", "hard_semantic")
    assert findings and findings[0].severity == FLAG


def test_check_hard_negative_matched_fails():
    findings = check_hard_negative(should_match_judged=True)
    assert findings and findings[0].severity == FAIL


def test_check_distractor_prefilter_self_distraction_fails():
    findings = check_distractor_prefilter("tkt_1_1", "tkt_1_1", same_customer=True)
    assert any(f.check == "distractor_prefilter" for f in findings)


def test_check_distractor_prefilter_different_customer_fails():
    findings = check_distractor_prefilter("tkt_1_1", "tkt_2_1", same_customer=False)
    assert any(f.check == "distractor_prefilter" for f in findings)
