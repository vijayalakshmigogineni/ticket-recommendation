"""Template 1 -- Customer Generation. See docs/generation_prompts.md.

Prompt wording lives here (not just in the doc) per the Phase 6 plan: the doc
stays the source of truth for the template's *design*, this module is the
source of truth for how real data gets substituted into the wire text sent to
the API. Output shape is enforced structurally via CustomerBatchOutput
(client.messages.parse(output_format=...) / output_config.format) rather than
by the "output ONLY a JSON array" instruction the doc illustrates for a human
copy-paste pilot -- that instruction is redundant once the schema is enforced,
so the wire text describes the object-wrapper shape instead.
"""

from __future__ import annotations

from generation.schemas import CustomerBatchOutput

_INSTRUCTIONS = """\
You are generating synthetic customer profiles for a benchmark dataset. These
"customers" are medical practices that are clients of a Revenue Cycle
Management (RCM) company -- the RCM company handles their billing, claims,
prior authorizations, and payment posting. Do NOT generate the RCM company
itself; generate its clients.

Generate {n} distinct, realistic client practices.

Vary across the batch:
- Specialty (e.g. family medicine, orthopedics, pain management, cardiology,
  dermatology, physical therapy, behavioral health, OB/GYN, urgent care)
- Practice size (solo provider / small group 2-5 providers / multi-location group)
- Primary payer mix (e.g. Medicare, Medicaid, Aetna, UnitedHealthcare, Cigna,
  BCBS, workers' comp -- 2-4 payers per practice, realistic for the specialty)
- Practice management / EHR system (e.g. Athenahealth, eClinicalWorks,
  Kareo, AdvancedMD, NextGen -- invent plausible ones if needed)

Do not reuse any of these already-generated names/specialties: {avoid_list}

Each practice needs ONE inbox_email (e.g. "billing@practicename.com") -- this
is the one real, persisted identifying address for the customer. It's the
practice's own recognizable address (should read as a shared/group inbox on
their side, not a named individual's address) -- NOT a mailbox we host for
them to send into. Every practice actually sends to the same shared RCM
intake address ("{account_manager_alias}"); inbox_email is instead what
production matches against the *sender* of an incoming email to figure out
which client it's from.

Separately, each practice also has 1-3 named human contacts who would
realistically email an RCM vendor about billing issues (billing coordinator,
office manager, practice administrator, sometimes the physician directly for
smaller practices) -- these are generation-only, used to vary who writes each
message later, mirroring how real individual staff addresses appear in
message traffic without being tracked in any formal roster. Give each contact
a plausible name, role, and email address using the practice's own invented
domain -- same domain as inbox_email (so a domain-level match would recognize
them too), different local part (not @gmail.com etc, unless it's a
deliberately small/informal solo practice).

Return exactly {n} items under the "customers" key, each with a unique
"temp_id" formatted as "cust_{{n}}" (e.g. "cust_1", "cust_2", ...), split into
production_fields (name, inbox_email) and generation_metadata (specialty,
practice_size, primary_payers, pm_ehr_system, contacts).
"""


def build_request(
    n: int,
    avoid_list: list[str] | None = None,
    account_manager_alias: str = "support@rcm-vendor.com",
) -> dict:
    avoid_text = ", ".join(avoid_list) if avoid_list else "(none yet)"
    user_text = _INSTRUCTIONS.format(
        n=n, avoid_list=avoid_text, account_manager_alias=account_manager_alias
    )
    return {
        "system": None,
        "messages": [{"role": "user", "content": user_text}],
        "output_format": CustomerBatchOutput,
    }
