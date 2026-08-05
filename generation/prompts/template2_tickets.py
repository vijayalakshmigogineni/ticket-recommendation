"""Template 2 -- Ticket Generation (seed). See docs/generation_prompts.md.

No issue_type field -- category is the only classification axis (confirmed
against production; see app/enums.py). Category/status are orchestrator-fixed
(generation.sampling), never left to the model.
"""

from __future__ import annotations

import json

from generation.schemas import TicketSeedBatchOutput

_CATEGORY_GROUNDING = """\
Category = which operational team owns this ticket. Use realistic RCM
specifics for the assigned category, not generic corporate language -- vary
the specific scenario naturally across a batch (this is inspiration for
realism/diversity, not a field to echo back verbatim):
- claims: denial reasons (missing modifier, timely filing, medical
  necessity, coordination of benefits, incorrect diagnosis code),
  clearinghouse rejections, duplicate submissions, documentation requests
  from a payer, corrected-claim resubmissions, status inquiries
- prior_authorization: authorization denied/expired, missing authorization,
  peer-to-peer review required, incomplete request, retro auth needed,
  missing clinical documentation, wrong procedure authorized, renewal for
  ongoing treatment
- payment_posting: underpayment vs. contracted rate, overpayment/refund
  request, ERA/EOB discrepancy, payment posted to wrong account, missing
  payment, contractual adjustment mismatch, duplicate payment, unapplied
  payment, patient payment reconciliation
- eligibility: coverage termination, effective date discrepancy, plan/payer
  change, benefits verification, ineligible for service, coordination of
  benefits at the eligibility stage, supporting documentation required,
  incorrect member ID, referral requirement confirmation
- accounts_receivable: aging balance follow-up, patient balance dispute,
  write-off request, payment plan setup, collections escalation, unapplied
  credit resolution, refund processing delay, account reconciliation, bad
  debt referral status
- charge_entry: missing charge, incorrect CPT/procedure code, incorrect
  units billed, late charge submission, coding discrepancy, modifier
  missing at entry, new provider charge setup, charge template
  configuration, incorrect fee schedule applied
"""

_SIBLING_GUIDANCE = """\
This customer already has these OTHER open tickets in the SAME category:
{sibling_seeds_json}
The new ticket must be a genuinely different underlying issue (different
patient, different claim, different specific cause) but should plausibly
use similar surface vocabulary to the sibling(s) -- e.g. both are denial
scenarios, both are documentation requests -- so an Account Manager skimming
both tickets could plausibly confuse them. Write distinguishing_details
explicitly stating what makes this one different; plausibility of the pair
is a judgment call reviewed by Judge 1, not enforced by a formal field.
"""

_INSTRUCTIONS = """\
You are generating synthetic RCM (Revenue Cycle Management) ticket scenarios
for one customer. Customer profile:

{customer_profile_json}

Generate {m} ticket scenarios, one for each assignment below. Each ticket
represents one real billing/claims issue this practice contacted their RCM
vendor about.

Assignments (category and status are FIXED -- do not change them):
{assignment_list_json}

{category_grounding}
{sibling_guidance}
For each assignment, output realistic synthetic grounding facts under the
temp_id given in the assignment list. Dates are expressed as day-offsets from
today (negative = days ago); if status is "RESOLVED" or "CLOSED" (terminal),
closed_at_offset_days must be a smaller-magnitude (more recent) negative
number than created_at_offset_days; otherwise closed_at_offset_days must be
null.

Return exactly {m} items under the "tickets" key, split into
production_fields (subject, category, status, created_at_offset_days,
closed_at_offset_days) and generation_metadata (core_issue_summary,
distinguishing_details, claim_number, patient_id, payer, date_of_service,
procedure_description). production_fields.category and .status must match
the assignment exactly.
"""


def build_request(
    customer_profile: dict,
    assignments: list[dict],
    sibling_seeds: list[dict] | None = None,
) -> dict:
    """assignments: [{"temp_id": ..., "category": ..., "status": ...}, ...]
    sibling_seeds: full ticket seed dicts for this customer's other same-category
    open tickets, only passed for disambiguation-tier customers.
    """
    sibling_guidance = ""
    if sibling_seeds:
        sibling_guidance = _SIBLING_GUIDANCE.format(
            sibling_seeds_json=json.dumps(sibling_seeds, indent=2)
        )

    user_text = _INSTRUCTIONS.format(
        customer_profile_json=json.dumps(customer_profile, indent=2),
        m=len(assignments),
        assignment_list_json=json.dumps(assignments, indent=2),
        category_grounding=_CATEGORY_GROUNDING,
        sibling_guidance=sibling_guidance,
    )
    return {
        "system": None,
        "messages": [{"role": "user", "content": user_text}],
        "output_format": TicketSeedBatchOutput,
    }
