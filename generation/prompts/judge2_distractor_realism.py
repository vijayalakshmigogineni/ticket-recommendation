"""Judge 2 -- Distractor Realism. See docs/generation_qa_checklist.md.

Runs only on distractors that already passed the rule pre-filter (same
customer, not self, category-plausible per tier).
"""

from __future__ import annotations

import json

from generation.schemas import Judge2Output

_INSTRUCTIONS = """\
You are a QA reviewer checking whether a benchmark distractor is realistic.

Incoming email:
{email_text}

Correct ticket (what this email is actually about):
{correct_ticket_summary_json}

Candidate distractor ticket (flagged as a plausible-but-wrong match):
{distractor_ticket_summary_json}

Would a retrieval system relying on textual/semantic similarity plausibly
confuse the distractor for the correct answer here -- i.e. is this a
realistic near-miss, or is it only nominally similar (same category label)
with nothing in the actual content that would cause confusion?
"""


def build_request(
    email_text: str,
    correct_ticket_summary: dict,
    distractor_ticket_summary: dict,
) -> dict:
    user_text = _INSTRUCTIONS.format(
        email_text=email_text,
        correct_ticket_summary_json=json.dumps(correct_ticket_summary, indent=2),
        distractor_ticket_summary_json=json.dumps(distractor_ticket_summary, indent=2),
    )
    return {
        "system": None,
        "messages": [{"role": "user", "content": user_text}],
        "output_format": Judge2Output,
    }
