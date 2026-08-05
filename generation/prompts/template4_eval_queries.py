"""Template 4 -- Eval Query Generation. See docs/generation_prompts.md.

The scenario (customer, difficulty tier, target/near-miss ticket, style tags)
is fully decided before this prompt runs (generation.sampling) -- this
template only realizes it into text. Anti-leakage is the single most
important property here: no internal labels may appear in client-authored text.
"""

from __future__ import annotations

import json

from generation.schemas import EvalQueryBatchOutput

_TIER_INSTRUCTIONS = {
    "easy": (
        "restate the issue clearly, include explicit identifiers (claim "
        "number, patient name, or date of service) so the match is unambiguous."
    ),
    "moderate_paraphrase": (
        "same underlying issue as the target ticket, but reworded -- avoid "
        "reusing the target thread's exact phrases; no requirement to include "
        "explicit identifiers."
    ),
    "hard_semantic": (
        "vague/indirect phrasing about the SAME underlying issue as the "
        "target ticket -- no explicit identifiers, describe the situation "
        "rather than naming it (e.g. \"that thing we talked about last week "
        "is still not fixed\" style, adapted to the actual issue)."
    ),
    "hard_negative": (
        "describe a NEW, different issue that happens to use similar surface "
        "vocabulary/category to the near-miss ticket provided, but is NOT the "
        "same claim/patient/issue. A naive keyword or shallow-semantic match "
        "should find this confusing; a careful reader should see it's "
        "unrelated. The correct outcome here is 'no OPEN ticket matches' -- "
        "you are not deciding whether the AM creates a new ticket, only "
        "writing an email that is genuinely a different issue from the "
        "near-miss ticket provided."
    ),
    "boilerplate": (
        "very low informational content (e.g. \"Any update on this?\", "
        "\"Thanks, attached.\", \"Following up.\") -- still genuinely a reply "
        "about the target ticket, just terse. Do not smuggle in identifiers "
        "just to make it easier."
    ),
    "same_customer_disambiguation": (
        "write about ONE specific candidate ticket (the target_ticket given "
        "below) using language that could plausibly apply to either "
        "candidate at a glance, but contains at least one concrete detail "
        "that, on careful reading, points to the correct one only."
    ),
}

_SCENARIO_HEADER = """\
You are writing ONE incoming email from a medical practice client to their
RCM vendor, for a retrieval benchmark. This email must read as a new,
independent message -- not a reply continuing an existing thread (no quoted
history, no "Re:"-style continuation implied) -- since it models a client
message that broke automatic email threading and now requires the AM to
check it against open tickets. You are NOT the retrieval system and you must
NOT reveal or hint at any internal labels (category name, difficulty tier,
ticket ID, "this is a test", etc.) -- write exactly as a real client would,
who has no idea their message will be scored.

Customer profile: {customer_profile_json}

For each scenario below, write the email_text per its instructions:
{scenarios_json}
"""


def _scenario_payload(scenario: dict) -> dict:
    tier = scenario["tier"]
    payload = {
        "scenario_temp_id": scenario["temp_id"],
        "tier": tier,
        "instructions": _TIER_INSTRUCTIONS[tier],
        "style": {
            "tone": scenario["tone"],
            "length_bucket": scenario["length_bucket"],
            "noise_level": scenario["noise_level"],
        },
    }
    if scenario.get("target_ticket_context") is not None:
        payload["target_ticket"] = scenario["target_ticket_context"]
    if scenario.get("near_miss_ticket_context") is not None:
        payload["near_miss_ticket"] = scenario["near_miss_ticket_context"]
    if scenario.get("candidate_tickets_context") is not None:
        payload["candidates"] = scenario["candidate_tickets_context"]
        payload["write_about_target"] = scenario["target_ticket"]
    return payload


def build_request(customer_profile: dict, scenarios: list[dict]) -> dict:
    """scenarios: list of dicts from generation.sampling.EvalQueryScenario plus
    the resolved ticket seed/thread context per the table in
    docs/generation_prompts.md Template 4 (target_ticket_context /
    near_miss_ticket_context / candidate_tickets_context)."""
    payloads = [_scenario_payload(s) for s in scenarios]
    user_text = _SCENARIO_HEADER.format(
        customer_profile_json=json.dumps(customer_profile, indent=2),
        scenarios_json=json.dumps(payloads, indent=2),
    )
    return {
        "system": None,
        "messages": [{"role": "user", "content": user_text}],
        "output_format": EvalQueryBatchOutput,
    }
