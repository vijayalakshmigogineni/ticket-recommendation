import random

import pytest

from app.enums import DifficultyTier, TicketCategory, TicketStatus
from generation.config import DistributionsConfig, ScaleConfig
from generation.sampling import (
    build_eval_query_scenarios,
    build_manifest,
    build_ticket_assignments,
    sample_customer_ids,
)

VALID_CATEGORIES = {c.value for c in TicketCategory}
VALID_STATUSES = {s.value for s in TicketStatus}
VALID_TIERS = {t.value for t in DifficultyTier}


def make_scale(customers=20, tickets_avg=5, eval_queries=60):
    return ScaleConfig(
        customers=customers,
        tickets_per_customer={"avg": tickets_avg, "min": 1, "max": 10},
        messages_per_ticket={"avg": 5, "min": 2, "max": 15},
        eval_queries=eval_queries,
    )


def make_distributions(disambiguation_min=5):
    return DistributionsConfig(
        category_weights={
            "claims": 0.25, "payment_posting": 0.18, "prior_authorization": 0.16,
            "accounts_receivable": 0.15, "eligibility": 0.14, "charge_entry": 0.12,
        },
        category_floor=3,
        status_split={"non_terminal": 0.65, "terminal": 0.35},
        difficulty_tier_weights={
            "easy": 0.15, "moderate_paraphrase": 0.25, "hard_semantic": 0.20,
            "hard_negative": 0.15, "boilerplate": 0.10, "same_customer_disambiguation": 0.15,
        },
        style={
            "tone": {"professional": 0.6, "casual": 0.4},
            "length_bucket": {"short": 0.25, "medium": 0.5, "long": 0.25},
            "noise_level": {"clean": 0.6, "mild": 0.3, "heavy": 0.1},
        },
        disambiguation_customers_min=disambiguation_min,
    )


def test_sample_customer_ids():
    ids = sample_customer_ids(5)
    assert ids == ["cust_1", "cust_2", "cust_3", "cust_4", "cust_5"]


def test_ticket_assignments_valid_categories_and_statuses():
    scale = make_scale()
    dist = make_distributions()
    rng = random.Random(42)
    customer_ids = sample_customer_ids(scale.customers)
    assignments = build_ticket_assignments(customer_ids, scale, dist, rng)

    assert len(assignments) > 0
    for a in assignments:
        assert a.category in VALID_CATEGORIES
        assert a.status in VALID_STATUSES
        assert scale.messages_per_ticket.min <= a.message_count <= scale.messages_per_ticket.max


def test_category_floor_all_categories_present():
    scale = make_scale(customers=30, tickets_avg=6)
    dist = make_distributions()
    rng = random.Random(1)
    customer_ids = sample_customer_ids(scale.customers)
    assignments = build_ticket_assignments(customer_ids, scale, dist, rng)

    seen = {a.category for a in assignments}
    assert seen == VALID_CATEGORIES


def test_disambiguation_siblings_link_back_correctly():
    scale = make_scale(customers=15, tickets_avg=6)
    dist = make_distributions(disambiguation_min=5)
    rng = random.Random(7)
    customer_ids = sample_customer_ids(scale.customers)
    assignments = build_ticket_assignments(customer_ids, scale, dist, rng)

    by_id = {a.temp_id: a for a in assignments}
    siblings = [a for a in assignments if a.disambiguation_sibling]
    assert len(siblings) >= 2  # at least one pair (2 entries) was created

    for a in siblings:
        sibling = by_id[a.disambiguation_sibling]
        assert sibling.disambiguation_sibling == a.temp_id
        assert sibling.category == a.category
        assert sibling.customer_temp_id == a.customer_temp_id


def test_deterministic_given_same_seed():
    scale = make_scale()
    dist = make_distributions()
    customer_ids = sample_customer_ids(scale.customers)

    a1 = build_ticket_assignments(customer_ids, scale, dist, random.Random(99))
    a2 = build_ticket_assignments(customer_ids, scale, dist, random.Random(99))

    assert [ (a.temp_id, a.category, a.status, a.message_count) for a in a1 ] == \
           [ (a.temp_id, a.category, a.status, a.message_count) for a in a2 ]


def test_eval_query_scenarios_valid_tiers_and_counts():
    scale = make_scale(eval_queries=80)
    dist = make_distributions()
    rng = random.Random(3)
    customer_ids = sample_customer_ids(scale.customers)
    assignments = build_ticket_assignments(customer_ids, scale, dist, rng)
    scenarios = build_eval_query_scenarios(customer_ids, assignments, scale, dist, rng)

    assert len(scenarios) == scale.eval_queries
    for s in scenarios:
        assert s.tier in VALID_TIERS
        assert s.customer_temp_id in customer_ids


def test_hard_negative_scenarios_should_not_match():
    scale = make_scale(eval_queries=200)
    dist = make_distributions()
    rng = random.Random(11)
    customer_ids = sample_customer_ids(scale.customers)
    assignments = build_ticket_assignments(customer_ids, scale, dist, rng)
    scenarios = build_eval_query_scenarios(customer_ids, assignments, scale, dist, rng)

    hard_negatives = [s for s in scenarios if s.tier == DifficultyTier.HARD_NEGATIVE.value]
    assert hard_negatives, "expected at least one hard_negative scenario at this scale"
    for s in hard_negatives:
        assert s.should_match is False
        assert s.near_miss_ticket is not None


def test_same_customer_disambiguation_has_two_candidates():
    scale = make_scale(customers=20, tickets_avg=6, eval_queries=200)
    dist = make_distributions(disambiguation_min=8)
    rng = random.Random(21)
    customer_ids = sample_customer_ids(scale.customers)
    assignments = build_ticket_assignments(customer_ids, scale, dist, rng)
    scenarios = build_eval_query_scenarios(customer_ids, assignments, scale, dist, rng)

    disambig = [
        s for s in scenarios if s.tier == DifficultyTier.SAME_CUSTOMER_DISAMBIGUATION.value
        and s.candidates
    ]
    assert disambig, "expected at least one satisfiable disambiguation scenario"
    for s in disambig:
        assert len(s.candidates) == 2
        assert s.target_ticket in s.candidates


def test_build_manifest_end_to_end():
    scale = make_scale()
    dist = make_distributions()
    manifest = build_manifest(scale, dist, seed=5)

    assert len(manifest["customers"]) == scale.customers
    assert len(manifest["tickets"]) > 0
    assert len(manifest["eval_queries"]) == scale.eval_queries
