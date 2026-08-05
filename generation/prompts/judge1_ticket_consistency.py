"""Judge 1 -- Ticket & Conversation Consistency. See docs/generation_qa_checklist.md.

Runs once per ticket, after Templates 2+3 both exist, only on items that
passed the rule-based pre-checks (generation.qa.rules). When the ticket is
part of a disambiguation-tier sibling pair, the sibling's seed is passed in
too, so this single call also answers the sibling-pairing-plausibility
question.
"""

from __future__ import annotations

import json

from generation.schemas import Judge1Output

_INSTRUCTIONS = """\
You are a QA reviewer for a synthetic RCM support-ticket benchmark. Review
the ticket seed and its full message thread together.

Ticket seed (category + free-text core_issue_summary/distinguishing_details
-- no issue_type field, the real production system has no such concept):
{ticket_seed_json}

Message thread:
{messages_json}
{sibling_section}
Answer:
1. Category fit: given category "{category}" and the issue described in
   core_issue_summary/procedure_description, would an RCM billing expert
   file this under that category, or does it actually belong under a
   different one? If different, name which.
2. Logical flow: reading top to bottom, does each message make sense given
   what came before? Flag any contradiction (e.g. a fact -- claim number,
   patient, payer, amount -- changing between messages without explanation).
3. Intent/content match: for each message, does its content actually match
   its labeled intent_type, or is any message mislabeled (e.g. tagged
   thank_you but actually raises a new issue)?
4. Sibling pairing plausibility (only answer if a sibling seed is given
   above, otherwise output null): is this ticket's underlying issue
   genuinely plausible to confuse with the sibling's in production --
   similar enough that an AM could realistically mix them up -- or too
   dissimilar despite sharing a category?
"""

_SIBLING_SECTION = """
This ticket has a disambiguation-tier sibling for the same customer and
category:
{sibling_seed_json}
"""


def build_request(
    ticket_seed: dict,
    messages: list[dict],
    sibling_seed: dict | None = None,
) -> dict:
    sibling_section = (
        _SIBLING_SECTION.format(sibling_seed_json=json.dumps(sibling_seed, indent=2))
        if sibling_seed
        else ""
    )
    user_text = _INSTRUCTIONS.format(
        ticket_seed_json=json.dumps(ticket_seed, indent=2),
        messages_json=json.dumps(messages, indent=2),
        sibling_section=sibling_section,
        category=ticket_seed["production_fields"]["category"],
    )
    return {
        "system": None,
        "messages": [{"role": "user", "content": user_text}],
        "output_format": Judge1Output,
    }
