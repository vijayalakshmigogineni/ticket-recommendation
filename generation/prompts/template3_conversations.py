"""Template 3 -- Conversation Generation. See docs/generation_prompts.md.

Structural template: intent is a function of thread position, not an
independent random draw per message. This is the part most worth getting
right per the design doc, since it models real automatic email threading
(Case 2A in the Business Workflow), not IID sampling.
"""

from __future__ import annotations

import json

from generation.schemas import ConversationBatchOutput

_INSTRUCTIONS = """\
You are generating the message thread for one or more support tickets
between a medical practice (client) and their RCM vendor (account manager).
This structural template reflects real automatic email threading (Case 2A):
once a ticket exists, ordinary thread replies naturally mix operational and
non-operational content, which is why intent varies by thread position below
rather than being purely operational.

Customer profile:
{customer_profile_json}

Ticket seed(s) -- treat each independently, do not let details bleed across
tickets. Each seed's generation_metadata (core_issue_summary,
distinguishing_details, claim/patient/payer/date-of-service facts) is
available context, not to be quoted verbatim, and should inform message
specifics so two tickets in the same category still read distinctly from
each other:
{ticket_seeds_json}

For each ticket, generate exactly the message count given below (this count
is given per ticket, may differ across the batch) following this STRUCTURAL
template -- intent is a function of position in the thread, not an
independent random draw per message:
{message_counts_json}

1. Message 1 is ALWAYS sender_type=client, intent_type=initial_request. This
   is the client raising the issue for the first time, referencing the
   ticket's core_issue_summary and grounding facts (claim number, patient,
   date of service, etc.) in their own words.
2. Middle messages alternate realistically between client and
   account_manager and should mix intent_type across: follow_up (~35%
   overall share across the whole corpus, so use it often), status_check
   (~15%), documentation_provided (~15%) -- pick what's plausible given the
   category and what's already been said, not randomly.
3. Near the end of the thread, a thank_you (~10%) or informational (~7%)
   message MAY appear (not mandatory) -- these should cluster at the end,
   never at the start.
4. If the ticket's status is "RESOLVED" or "CLOSED" (terminal), the last 1-2
   messages should read as resolution (account_manager confirms resolution,
   client sends thank_you), and the final message's day_offset should be
   at/before the ticket's closed_at_offset_days.
5. account_manager messages come from a consistent internal alias, e.g.
   "{account_manager_alias}" -- same alias across all tickets in this batch.
6. client messages must use one of this customer's contact emails from the
   profile above -- vary which contact sends if there's more than one,
   consistent with role (e.g. billing coordinator more likely for
   payment_posting, office manager for documentation-related issues).

Independently vary writing style per message (not tied to thread position):
- tone: "professional" (60% of messages) or "casual" (40%)
- length_bucket: "short" (25%), "medium" (50%), "long" (25%)
- noise_level: "clean" (60%), "mild" (30% -- light typos/abbreviations like
  "pt" for patient, "asap"), "heavy" (10% -- jargon-dense and typo-heavy)

day_offset = days since ticket creation (0 = created_at). Must be
non-decreasing across the thread.

Return one entry under the "conversations" key per ticket_temp_id, each
containing its message list, split into production_fields (sender_type,
sender_email, day_offset, body_text) and generation_metadata (intent_type,
tone, length_bucket, noise_level).
"""


def build_request(
    customer_profile: dict,
    ticket_seeds: list[dict],
    message_counts: dict[str, int],
    account_manager_alias: str = "support@rcm-vendor.com",
) -> dict:
    """ticket_seeds: full seed dicts (temp_id, production_fields,
    generation_metadata) for every ticket in this batch (one customer's batch).
    message_counts: {ticket_temp_id: message_count} -- orchestrator-assigned.
    """
    user_text = _INSTRUCTIONS.format(
        customer_profile_json=json.dumps(customer_profile, indent=2),
        ticket_seeds_json=json.dumps(ticket_seeds, indent=2),
        message_counts_json=json.dumps(message_counts, indent=2),
        account_manager_alias=account_manager_alias,
    )
    return {
        "system": None,
        "messages": [{"role": "user", "content": user_text}],
        "output_format": ConversationBatchOutput,
    }
