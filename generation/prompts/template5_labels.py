"""Template 5 -- Ground-Truth Label Generation (blind judge).
See docs/generation_prompts.md.

Deliberately blind: does not see Template 4's intended answer, re-derives the
label purely from the email text + the customer's candidate ticket pool
(randomized order, anonymized A/B/C labels -- mapped back to real temp_ids by
the caller after the response comes back, never before).
"""

from __future__ import annotations

import json

from generation.schemas import LabelOutput

_INSTRUCTIONS = """\
You are a QA judge for a support-ticket retrieval benchmark. You will be
shown one incoming client email and a list of that client's currently OPEN
tickets (summaries only). Decide, independent of any other context, which
ticket (if any) this email is really about.

Incoming email:
{email_text}

Candidate open tickets for this customer (order is randomized, labels are
arbitrary):
{candidate_tickets_json}

Decide:
1. Does this email genuinely refer to one of the candidate tickets, or is it
   about something not represented in the list (a new/unrelated issue)?
2. If it matches one: which label, and how confident/obvious is the match?
3. Which OTHER candidates (if any) are plausible-but-wrong alternatives a
   retrieval system might mistakenly surface? (distractors)
4. Independently classify the difficulty: would a system relying on plain
   keyword overlap get this right, or does it require real semantic
   understanding? Use one of the tier definitions below.

Tier definitions:
- easy: explicit identifiers present, unambiguous
- moderate_paraphrase: same issue, reworded, no strong lexical overlap needed
- hard_semantic: vague/indirect, no explicit identifiers
- hard_negative: superficially similar to a candidate but actually unrelated -- should_match is false
- boilerplate: very low content, but still a genuine (if terse) reference to a real ticket
- same_customer_disambiguation: 2+ candidates are plausible, requires fine-grained discrimination

matched_label must be one of the candidate labels shown above, or null if no
match. distractor_labels must only contain labels from the candidates shown.
"""


def build_request(email_text: str, candidate_tickets: list[dict]) -> dict:
    """candidate_tickets: [{"label": "A", "subject": ..., "category": ...,
    "brief_description": ...}, ...] in randomized order with anonymized labels.
    """
    user_text = _INSTRUCTIONS.format(
        email_text=email_text,
        candidate_tickets_json=json.dumps(candidate_tickets, indent=2),
    )
    return {
        "system": None,
        "messages": [{"role": "user", "content": user_text}],
        "output_format": LabelOutput,
    }
