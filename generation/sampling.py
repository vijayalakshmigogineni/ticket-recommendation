"""Stratified sampling: the orchestrator's assignment decisions (category, status,
difficulty tier, style tags). Pure functions, no API calls -- see
docs/generation_prompts.md's "never let the LLM pick its own category/difficulty/
status" rule. Mirrors the structure of pilot/manifest.json, which was hand-built
and QA-reviewed during the pilot phase.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from app.enums import DifficultyTier, TERMINAL_TICKET_STATUSES, TicketStatus

from generation.config import DistributionsConfig, ScaleConfig

NON_TERMINAL_STATUSES = [s for s in TicketStatus if s not in TERMINAL_TICKET_STATUSES]
TERMINAL_STATUSES = [s for s in TicketStatus if s in TERMINAL_TICKET_STATUSES]


@dataclass
class TicketAssignment:
    temp_id: str
    customer_temp_id: str
    category: str
    status: str
    message_count: int
    disambiguation_sibling: str | None = None


@dataclass
class EvalQueryScenario:
    temp_id: str
    tier: str
    customer_temp_id: str
    tone: str
    length_bucket: str
    noise_level: str
    target_ticket: str | None = None
    near_miss_ticket: str | None = None
    should_match: bool = True
    candidates: list[str] = field(default_factory=list)


def sample_customer_ids(n: int) -> list[str]:
    return [f"cust_{i}" for i in range(1, n + 1)]


def _sample_count(rng: random.Random, avg: float, lo: int, hi: int) -> int:
    n = round(rng.gauss(avg, max(avg * 0.3, 1.0)))
    return max(lo, min(hi, n))


def _weighted_choice(rng: random.Random, weights: dict[str, float]) -> str:
    labels = list(weights.keys())
    cumulative = []
    total = 0.0
    for label in labels:
        total += weights[label]
        cumulative.append(total)
    r = rng.random() * total
    for label, c in zip(labels, cumulative):
        if r <= c:
            return label
    return labels[-1]


def build_ticket_assignments(
    customer_ids: list[str],
    scale: ScaleConfig,
    distributions: DistributionsConfig,
    rng: random.Random,
) -> list[TicketAssignment]:
    """Assigns category/status/message_count per ticket, and picks
    disambiguation_customers_min customers to receive a same-category sibling pair.
    Category floor is enforced via round-robin seeding, then the remainder is
    filled by weighted sampling -- mirrors the pilot's "at least one per category,
    let higher-weight categories appear more often" approach at sub-full scale.
    """
    per_customer_counts = {
        cid: _sample_count(
            rng,
            scale.tickets_per_customer.avg,
            scale.tickets_per_customer.min,
            scale.tickets_per_customer.max,
        )
        for cid in customer_ids
    }
    total_tickets = sum(per_customer_counts.values())

    categories = list(distributions.category_weights.keys())
    floor = distributions.category_floor
    forced = categories * min(floor, max(1, total_tickets // max(1, len(categories))))
    rng.shuffle(forced)
    forced = forced[:total_tickets]
    remaining_slots = total_tickets - len(forced)
    sampled = [_weighted_choice(rng, distributions.category_weights) for _ in range(remaining_slots)]
    all_categories = forced + sampled
    rng.shuffle(all_categories)

    disambiguation_customers = set(
        rng.sample(
            customer_ids,
            k=min(distributions.disambiguation_customers_min, len(customer_ids)),
        )
    )

    assignments: list[TicketAssignment] = []
    category_iter = iter(all_categories)
    for cust_idx, cid in enumerate(customer_ids, start=1):
        n_tickets = per_customer_counts[cid]
        needs_sibling_pair = cid in disambiguation_customers and n_tickets >= 2
        sibling_category = next(category_iter) if needs_sibling_pair else None

        for tkt_idx in range(1, n_tickets + 1):
            temp_id = f"tkt_{cust_idx}_{tkt_idx}"
            is_terminal = rng.random() < distributions.status_split.terminal
            status = rng.choice(TERMINAL_STATUSES if is_terminal else NON_TERMINAL_STATUSES)
            message_count = _sample_count(
                rng,
                scale.messages_per_ticket.avg,
                scale.messages_per_ticket.min,
                scale.messages_per_ticket.max,
            )

            if needs_sibling_pair and tkt_idx in (1, 2):
                category = sibling_category
                sibling_temp_id = (
                    f"tkt_{cust_idx}_2" if tkt_idx == 1 else f"tkt_{cust_idx}_1"
                )
            else:
                category = next(category_iter)
                sibling_temp_id = None

            assignments.append(
                TicketAssignment(
                    temp_id=temp_id,
                    customer_temp_id=cid,
                    category=category,
                    status=status.value,
                    message_count=message_count,
                    disambiguation_sibling=sibling_temp_id,
                )
            )
    return assignments


def build_eval_query_scenarios(
    customer_ids: list[str],
    ticket_assignments: list[TicketAssignment],
    scale: ScaleConfig,
    distributions: DistributionsConfig,
    rng: random.Random,
) -> list[EvalQueryScenario]:
    """Assigns difficulty tier + target/near-miss ticket(s) + style tags per eval
    query. Style tags are sampled independently of difficulty tier (spec's rule
    that noise/tone/length are an orthogonal axis) -- see
    pilot/spot_check_heavy_noise.md for the validation of that independence.
    """
    by_customer: dict[str, list[TicketAssignment]] = {}
    for a in ticket_assignments:
        by_customer.setdefault(a.customer_temp_id, []).append(a)

    sibling_customers = [
        cid
        for cid, tickets in by_customer.items()
        if any(t.disambiguation_sibling for t in tickets)
    ]

    scenarios: list[EvalQueryScenario] = []
    for i in range(1, scale.eval_queries + 1):
        temp_id = f"q_{i}"
        tier = _weighted_choice(rng, distributions.difficulty_tier_weights)
        tone = _weighted_choice(rng, distributions.style.tone)
        length_bucket = _weighted_choice(rng, distributions.style.length_bucket)
        noise_level = _weighted_choice(rng, distributions.style.noise_level)

        if tier == DifficultyTier.SAME_CUSTOMER_DISAMBIGUATION.value and sibling_customers:
            cid = rng.choice(sibling_customers)
            tickets = by_customer[cid]
            sibling_pair = next(t for t in tickets if t.disambiguation_sibling)
            candidates = sorted({sibling_pair.temp_id, sibling_pair.disambiguation_sibling})
            target = rng.choice(candidates)
            scenarios.append(
                EvalQueryScenario(
                    temp_id=temp_id, tier=tier, customer_temp_id=cid,
                    tone=tone, length_bucket=length_bucket, noise_level=noise_level,
                    target_ticket=target, candidates=candidates,
                )
            )
        elif tier == DifficultyTier.HARD_NEGATIVE.value:
            cid = rng.choice(customer_ids)
            tickets = by_customer.get(cid) or []
            near_miss = rng.choice(tickets).temp_id if tickets else None
            scenarios.append(
                EvalQueryScenario(
                    temp_id=temp_id, tier=tier, customer_temp_id=cid,
                    tone=tone, length_bucket=length_bucket, noise_level=noise_level,
                    near_miss_ticket=near_miss, should_match=False,
                )
            )
        else:
            cid = rng.choice(customer_ids)
            tickets = by_customer.get(cid) or []
            target = rng.choice(tickets).temp_id if tickets else None
            scenarios.append(
                EvalQueryScenario(
                    temp_id=temp_id, tier=tier, customer_temp_id=cid,
                    tone=tone, length_bucket=length_bucket, noise_level=noise_level,
                    target_ticket=target,
                )
            )
    return scenarios


def build_manifest(
    scale: ScaleConfig,
    distributions: DistributionsConfig,
    seed: int = 0,
) -> dict:
    rng = random.Random(seed)
    customer_ids = sample_customer_ids(scale.customers)
    ticket_assignments = build_ticket_assignments(customer_ids, scale, distributions, rng)
    eval_queries = build_eval_query_scenarios(
        customer_ids, ticket_assignments, scale, distributions, rng
    )
    return {
        "customers": customer_ids,
        "tickets": ticket_assignments,
        "eval_queries": eval_queries,
    }
