# Generation Prompt Templates

Status: **Draft — pending pilot validation.** These are the prompt templates referenced in `PROJECT_PLAN.md` Phase 1/2. Workflow: design prompts (this doc) → generate a manual pilot (~20–30 tickets) with them → review → freeze → build the automated pipeline that executes these same prompts programmatically. Nothing here is final until the pilot review passes.

Five templates, each a distinct generation concern:

```
1. Customer Generation
        ↓ (customer profile)
2. Ticket Generation (seed)         ← orchestrator assigns category + status
        ↓ (ticket seed: subject + grounding facts)
3. Conversation Generation          ← orchestrator assigns message count
        ↓ (message thread — this is the ticket corpus)
4. Eval Query Generation            ← orchestrator assigns difficulty tier + target ticket + style
        ↓ (raw incoming email text)
5. Ground-Truth Label Generation    ← BLIND pass, independent of step 4's construction intent
        ↓ (structured label — cross-checked against orchestrator's intended label)
```

The "orchestrator" is a human during the manual pilot and a script during automation — same role either way: it makes the *stratified sampling decisions* (which category, which difficulty tier, which style bucket) so the distributions in the spec are actually hit. The LLM's job in every template is narrower: realize one scenario into realistic text/data. Never let the LLM pick its own category/difficulty/status — that's how distributions silently drift.

## Shared conventions (apply to all 5 templates)

- **Output = JSON only.** No prose before/after, no markdown fences in the actual LLM response (fences shown below are for this doc's readability). This matters now (copy-pasteable into a reviewer) and later (parsed by the automated pipeline).
- **Temp IDs, not DB IDs.** During the pilot nothing is inserted into Postgres yet. Use short string keys (`cust_1`, `tkt_1_2`, `q_7`) to cross-reference between steps; a later ingestion script maps these to real serial IDs.
- **Batch mode.** Every template accepts an array-in/array-out batch so a manual pilot doesn't require 90+ separate chat turns. When batching, explicitly instruct the model to vary surface details across items — LLMs default to formulaic repetition when asked for N similar things in one call.
- **No real PII.** Patient names/IDs, claim numbers, member IDs must be obviously synthetic (e.g. `PT-88213`, `CLM-2026-04471`) — never real-looking SSNs or realistic-but-guessable identifiers.
- **Anti-leakage rule (templates 2–4).** Internal labels (category name, difficulty tier, "this is a hard negative", etc.) must never appear inside client-authored text. A real client doesn't know your taxonomy.
- **Enum fidelity.** Every enum-valued field in the output must be one of the exact strings from `app/enums.py` — not a paraphrase of it. Listed inline in each template.

---

## Template 1 — Customer Generation

**Persisted fields:** `Customer.name`, `CustomerEmail.email_address` (one row per contact). Everything else (specialty, size, payers, PM/EHR system) is *generation context* carried forward into Templates 2–4 to keep facts consistent per customer — it doesn't need its own DB column yet.

**Orchestrator supplies:** batch size `N`; optionally a list of specialties/names already used in prior batches (diversity guard).

**Model outputs:** array of customer profiles.

```
You are generating synthetic customer profiles for a benchmark dataset. These
"customers" are medical practices that are clients of a Revenue Cycle
Management (RCM) company — the RCM company handles their billing, claims,
prior authorizations, and payment posting. Do NOT generate the RCM company
itself; generate its clients.

Generate {{N}} distinct, realistic client practices.

Vary across the batch:
- Specialty (e.g. family medicine, orthopedics, pain management, cardiology,
  dermatology, physical therapy, behavioral health, OB/GYN, urgent care)
- Practice size (solo provider / small group 2-5 providers / multi-location group)
- Primary payer mix (e.g. Medicare, Medicaid, Aetna, UnitedHealthcare, Cigna,
  BCBS, workers' comp — 2-4 payers per practice, realistic for the specialty)
- Practice management / EHR system (e.g. Athenahealth, eClinicalWorks,
  Kareo, AdvancedMD, NextGen — invent plausible ones if needed)

Do not reuse any of these already-generated names/specialties: {{AVOID_LIST}}

Each practice has 1-3 named human contacts who would realistically email an
RCM vendor about billing issues (billing coordinator, office manager,
practice administrator, sometimes the physician directly for smaller
practices). Give each contact a plausible name, role, and email address
using the practice's own invented domain (not @gmail.com etc, unless it's a
deliberately small/informal solo practice).

Output ONLY a JSON array, no other text:
[
  {
    "temp_id": "cust_1",
    "name": "<practice name>",
    "specialty": "<specialty>",
    "practice_size": "solo" | "small_group" | "multi_location",
    "primary_payers": ["<payer>", ...],
    "pm_ehr_system": "<system name>",
    "contacts": [
      {"name": "<full name>", "role": "<role>", "email": "<email>"}
    ]
  }
]
```

---

## Template 2 — Ticket Generation (seed)

Produces the *grounding facts* for a ticket, not the conversation itself. This seed is the source of truth that Template 3 (conversation) and Template 4 (eval query) both draw on, so a ticket stays internally consistent across the thread and any later query that references it.

**Persisted fields:** `Ticket.subject`, `category`, `status`, (`created_at`/`closed_at` derived from the day-offsets). `claim_number`, `patient_id`, `payer`, `date_of_service` map directly onto the *reserved* `Message` columns of the same name (spec note: schema keeps these at message level, reserved for future hybrid retrieval — so the seed's facts get echoed onto the relevant message(s) in Template 3, not stored separately on the ticket).

**Orchestrator supplies:** the customer profile from Template 1; a list of `(category, issue_type, status)` assignments — one per ticket to generate, already sampled to hit the spec's category floor (min 20/category at full scale) and ~65/35 open/closed split; for customers targeted for the disambiguation tier, the *other* same-category (similar-issue-type) ticket seed(s) already generated for that customer, so the new one is instructed to be genuinely distinct but surface-similar.

**Model outputs:** array of ticket seeds, one per assignment.

```
You are generating synthetic RCM (Revenue Cycle Management) ticket scenarios
for one customer. Customer profile:

{{CUSTOMER_PROFILE_JSON}}

Generate {{M}} ticket scenarios, one for each assignment below. Each ticket
represents one real billing/claims issue this practice contacted their RCM
vendor about.

Assignments (category, issue_type, and status are FIXED — do not change them):
{{ASSIGNMENT_LIST}}   e.g. [{"temp_id": "tkt_1_1", "category": "claims", "issue_type": "claim_denial", "status": "open"}, ...]

Category = which operational team owns this ticket. Issue Type = the
specific business problem within that team. Use realistic RCM specifics for
the assigned issue_type, not generic corporate language — issue_type is
generation/QA metadata only, it must never appear verbatim in client-facing
text (write around it, don't quote it):

| Category | Issue Types (pick the one assigned) |
|---|---|
| claims | claim_denial (specific reason: CO-97 bundled service, CO-16 missing/invalid info, timely filing limit, medical necessity, missing modifier, COB) · missing_modifier · timely_filing · duplicate_claim · medical_necessity · coordination_of_benefits · documentation_request_from_payer (specific doc type: op report, progress notes, medical records, itemized statement) · claim_rejection_clearinghouse · claim_status_inquiry · incorrect_diagnosis_code · corrected_claim_needed |
| prior_authorization | authorization_denied · authorization_expired · missing_authorization · peer_to_peer_review_required · incomplete_authorization_request · retro_authorization_needed · missing_clinical_documentation · authorization_status_inquiry · wrong_procedure_authorized · auth_renewal_for_ongoing_treatment |
| payment_posting | underpayment (vs. contracted rate) · overpayment_refund_request · era_eob_discrepancy · payment_posted_to_wrong_account · missing_payment · contractual_adjustment_mismatch · duplicate_payment_posted · unapplied_unidentified_payment · patient_payment_reconciliation · payment_plan_posting_issue |
| eligibility | coverage_termination · effective_date_discrepancy · plan_payer_change · benefits_verification_needed · ineligible_for_service · coordination_of_benefits_eligibility_stage · supporting_documentation_required · incorrect_member_id_demographic_mismatch · referral_requirement_confirmation |
| accounts_receivable | aging_balance_follow_up · patient_balance_dispute · write_off_request · payment_plan_setup · collections_escalation · unapplied_credit_resolution · refund_processing_delay · account_reconciliation_request · bad_debt_referral_status |
| charge_entry | missing_charge · incorrect_cpt_procedure_code · incorrect_units_billed · late_charge_submission · coding_discrepancy · modifier_missing_at_entry · new_provider_charge_setup · charge_template_configuration · incorrect_fee_schedule_applied |

This is the default v1 controlled vocabulary — treat it as closed for
generation now, extensible later without changing this template's structure.

{{#IF DISAMBIGUATION_SIBLINGS}}
This customer already has these OTHER open tickets in the SAME category:
{{SIBLING_SEEDS_JSON}}
The new ticket(s) below must use an issue_type that is SIMILAR to (not
necessarily identical to) the sibling's — plausibly confusable, e.g.
claim_denial + claim_rejection_clearinghouse, or missing_modifier +
incorrect_diagnosis_code (both denial-adjacent); NOT claim_denial +
documentation_request_from_payer (not confusable despite same category).
Beyond that, it must be a genuinely different underlying issue (different
patient, different claim, different specific cause) but should plausibly
use similar surface vocabulary — this pair is used later to test whether a
retrieval system can tell them apart.
{{/IF}}

For each assignment, output realistic synthetic grounding facts. Dates are
expressed as day-offsets from today (negative = days ago); if status is
"closed", closed_at_offset_days must be a smaller-magnitude (more recent)
negative number than created_at_offset_days.

Output ONLY a JSON array, no other text:
[
  {
    "temp_id": "tkt_1_1",
    "subject": "<short subject line, as a human would title it>",
    "category": "<must match the assigned category exactly>",
    "issue_type": "<must match the assigned issue_type exactly>",
    "status": "<must match the assigned status exactly>",
    "core_issue_summary": "<1-3 sentences, internal reference, not client-facing verbatim>",
    "distinguishing_details": "<what makes this ticket different from any sibling ticket>",
    "claim_number": "<synthetic>",
    "patient_id": "<synthetic>",
    "payer": "<one of the customer's primary_payers, or a plausible other>",
    "date_of_service": "<YYYY-MM-DD, recent past>",
    "procedure_description": "<brief, e.g. 'CPT 99214 office visit' or 'MRI lumbar spine'>",
    "created_at_offset_days": <int>,
    "closed_at_offset_days": <int or null>
  }
]
```

Valid `category` values: `claims`, `prior_authorization`, `payment_posting`, `eligibility`, `accounts_receivable`, `charge_entry`.
Valid `issue_type` values: see the table above — must belong to the assigned category.
Valid `status` values: `open`, `closed`.

---

## Template 3 — Conversation Generation

Realizes a ticket seed into the actual message thread. This is the ticket corpus that eventually gets embedded.

**Persisted fields:** `Message.sender_type`, `sender_email`, `body_text`, `intent_type`, `created_at` (derived from day_offset), plus `claim_number`/`patient_id`/`payer`/`date_of_service` echoed from the seed onto whichever message first states them (usually message 1).

**Orchestrator supplies:** the ticket seed(s) from Template 2; the customer profile (for contact emails + an account-manager alias); a target message count per ticket (sample 2–15, avg ~5, per spec §1); can batch all tickets for one customer in a single call.

**Structural rules baked into the prompt** (spec §3 — this is the part most worth getting right, since it's a structural template, not IID sampling):

```
You are generating the message thread for one or more support tickets
between a medical practice (client) and their RCM vendor (account manager).
This structural template reflects real automatic email threading (Case 2A —
see Business Workflow in the spec): once a ticket exists, ordinary thread
replies naturally mix operational and non-operational content, which is why
intent varies by thread position below rather than being purely operational.

Customer profile:
{{CUSTOMER_PROFILE_JSON}}

Ticket seed(s) — treat each independently, do not let details bleed across
tickets. Each seed's issue_type is available context (not to be quoted
verbatim) and should inform message specifics — e.g. a
missing_clinical_documentation Prior Authorization ticket should read
differently than an authorization_expired one:
{{TICKET_SEEDS_JSON}}

For each ticket, generate exactly {{MESSAGE_COUNT}} messages (this count is
given per ticket, may differ across the batch) following this STRUCTURAL
template — intent is a function of position in the thread, not an
independent random draw per message:

1. Message 1 is ALWAYS sender_type=client, intent_type=initial_request. This
   is the client raising the issue for the first time, referencing the
   ticket's core_issue_summary and grounding facts (claim number, patient,
   date of service, etc.) in their own words.
2. Middle messages alternate realistically between client and
   account_manager and should mix intent_type across: follow_up (~35%
   overall share across the whole corpus, so use it often), status_check
   (~15%), documentation_provided (~15%) — pick what's plausible given the
   category and what's already been said, not randomly.
3. Near the end of the thread, a thank_you (~10%) or informational (~7%)
   message MAY appear (not mandatory) — these should cluster at the end,
   never at the start.
4. If the ticket's status is "closed", the last 1-2 messages should read as
   resolution (account_manager confirms resolution, client sends thank_you),
   and the final message's day_offset should be at/before the ticket's
   closed_at_offset_days.
5. account_manager messages come from a consistent internal alias, e.g.
   "{{ACCOUNT_MANAGER_ALIAS}}" — same alias across all tickets in this batch.
6. client messages must use one of this customer's contact emails from the
   profile above — vary which contact sends if there's more than one,
   consistent with role (e.g. billing coordinator more likely for
   payment_posting, office manager for documentation-related issue types
   like documentation_request_from_payer or missing_clinical_documentation).

Independently vary writing style per message (not tied to thread position):
- tone: "professional" (60% of messages) or "casual" (40%)
- length_bucket: "short" (25%), "medium" (50%), "long" (25%)
- noise_level: "clean" (60%), "mild" (30% — light typos/abbreviations like
  "pt" for patient, "asap"), "heavy" (10% — jargon-dense and typo-heavy)

day_offset = days since ticket creation (0 = created_at). Must be
non-decreasing across the thread.

Output ONLY a JSON array, no other text:
[
  {
    "ticket_temp_id": "tkt_1_1",
    "messages": [
      {
        "sender_type": "client" | "account_manager",
        "sender_email": "<must match a contact/alias given above>",
        "intent_type": "initial_request" | "follow_up" | "status_check" | "documentation_provided" | "thank_you" | "informational",
        "tone": "professional" | "casual",
        "length_bucket": "short" | "medium" | "long",
        "noise_level": "clean" | "mild" | "heavy",
        "day_offset": <int>,
        "body_text": "<the actual email/message text>"
      }
    ]
  }
]
```

---

## Template 4 — Eval Query Generation

Writes the actual incoming email for a benchmark test case. **The scenario is fully decided before this prompt runs** — this template only realizes it into text. Deciding the scenario (customer, difficulty tier, target ticket, should_match) is a sampling/orchestration step, not an LLM creative step, or the spec's difficulty-tier percentages (§4) can't be guaranteed.

**Persisted fields:** `EvalQuery.email_text`, `tone`, `length_bucket`, `noise_level` (the rest of `EvalQuery`'s fields — `correct_ticket_id`, `should_match`, `difficulty_tier`, `distractor_ticket_ids`, `reasoning` — come from Template 5, not this one, even though the orchestrator already "knows" the intended answer here. Keeping generation and labeling separate is deliberate — see Template 5).

**Orchestrator supplies:** customer profile; difficulty tier; style tags (tone/length/noise, sampled per spec §5's independent distribution — not correlated with difficulty); and, depending on tier:

| Tier | What's passed in |
|---|---|
| easy | the target ticket's full seed + thread |
| moderate_paraphrase | the target ticket's full seed + thread |
| hard_semantic | the target ticket's full seed + thread |
| hard_negative | a "near-miss" ticket (real, from the corpus) to imitate surface vocabulary from, but the query must describe a genuinely different, new issue |
| boilerplate | the target ticket's full seed + thread (still a real match, just low-content) |
| same_customer_disambiguation | 2+ candidate tickets (same category, semantically similar issue types, same customer) — one is the true target |

```
You are writing ONE incoming email from a medical practice client to their
RCM vendor, for a retrieval benchmark. This email must read as a new,
independent message — not a reply continuing an existing thread (no quoted
history, no "Re:"-style continuation implied) — since it models Case 2B: a
client message that broke automatic email threading and now requires the
AM to check it against open tickets (see Business Workflow in the spec).
You are NOT the retrieval system and you must NOT reveal or hint at any
internal labels (category name, issue_type, difficulty tier, ticket ID,
"this is a test", etc.) — write exactly as a real client would, who has no
idea their message will be scored.

Customer profile: {{CUSTOMER_PROFILE_JSON}}

Scenario type: {{DIFFICULTY_TIER}}
{{SCENARIO_CONTEXT_JSON}}   -- target ticket(s) and/or near-miss ticket, per the table above

Writing style (apply regardless of scenario type):
- tone: {{TONE}}
- length_bucket: {{LENGTH_BUCKET}}
- noise_level: {{NOISE_LEVEL}}

Scenario-specific instructions:
- easy: restate the issue clearly, include explicit identifiers (claim
  number, patient name, or date of service) so the match is unambiguous.
- moderate_paraphrase: same underlying issue as the target ticket, but
  reworded — avoid reusing the target thread's exact phrases; no requirement
  to include explicit identifiers.
- hard_semantic: vague/indirect phrasing about the SAME underlying issue as
  the target ticket — no explicit identifiers, describe the situation
  rather than naming it (e.g. "that thing we talked about last week is
  still not fixed" style, adapted to the actual issue).
- hard_negative: describe a NEW, different issue that happens to use
  similar surface vocabulary/category to the near-miss ticket provided, but
  is NOT the same claim/patient/issue. A naive keyword or shallow-semantic
  match should find this confusing; a careful reader should see it's
  unrelated. The correct outcome here is "no OPEN ticket matches" — you are
  not deciding whether the AM creates a new ticket, only writing an email
  that is genuinely a different issue from the near-miss ticket provided.
- boilerplate: very low informational content (e.g. "Any update on this?",
  "Thanks, attached.", "Following up.") — still genuinely a reply about the
  target ticket, just terse. Do not smuggle in identifiers just to make it
  easier.
- same_customer_disambiguation: write about ONE specific candidate ticket
  (tell me which — you decide, or it's given) using language that could
  plausibly apply to either candidate at a glance, but contains at least one
  concrete detail that, on careful reading, points to the correct one only.

Output ONLY a JSON object, no other text:
{
  "email_text": "<the email as the client would actually write it>"
}
```

For batches, wrap multiple scenarios into an array of `{scenario_temp_id, ...same inputs}` in, `[{scenario_temp_id, email_text}]` out.

---

## Template 5 — Ground-Truth Label Generation (blind judge)

This is deliberately a **separate, blind pass** — it does not see the orchestrator's intended answer from Template 4. It re-derives the label purely from the email text plus the customer's candidate ticket pool, the same information a real retrieval system would have. The result is then reconciled against the intended label:

- **Match → confidence signal.** The construction was clean; label the query with the intended (now double-confirmed) ground truth.
- **Mismatch → flag for manual review.** Either the email didn't actually realize the intended scenario (Template 4 drifted), or the scenario itself was ambiguous. This catches generation drift automatically, on top of — not instead of — the spec's existing 10% manual spot-check (§ QA note).

**Persisted fields:** all of `EvalQuery`'s remaining fields — `correct_ticket_id`, `should_match`, `difficulty_tier`, `distractor_ticket_ids`, `reasoning`.

**Orchestrator supplies:** the email text from Template 4; the customer's full candidate pool — every OPEN ticket for that customer, as short summaries only (subject + category + issue_type + brief description — **not** the full thread, matching what the real pipeline's retrieval scope would see), presented in **randomized order with anonymized labels** (`A`, `B`, `C`, not real ticket IDs, to avoid position/ID bias) — mapped back to real temp_ids only after the model responds. `issue_type` is the signal the judge needs to tell genuinely-hard disambiguation pairs (same category, similar issue types) apart from easy ones (same category, unrelated issue types).

```
You are a QA judge for a support-ticket retrieval benchmark. You will be
shown one incoming client email and a list of that client's currently OPEN
tickets (summaries only). Decide, independent of any other context, which
ticket (if any) this email is really about.

Incoming email:
{{EMAIL_TEXT}}

Candidate open tickets for this customer (order is randomized, labels are
arbitrary):
{{CANDIDATE_TICKETS_JSON}}   -- e.g. [{"label": "A", "subject": "...", "category": "...", "issue_type": "...", "brief_description": "..."}, ...]

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
- hard_negative: superficially similar to a candidate but actually unrelated — should_match is false
- boilerplate: very low content, but still a genuine (if terse) reference to a real ticket
- same_customer_disambiguation: 2+ candidates are plausible, requires fine-grained discrimination

Output ONLY a JSON object, no other text:
{
  "matched_label": "<candidate label, or null if no match>",
  "should_match": true | false,
  "difficulty_tier": "easy" | "moderate_paraphrase" | "hard_semantic" | "hard_negative" | "boilerplate" | "same_customer_disambiguation",
  "distractor_labels": ["<label>", ...],
  "reasoning": "<why — cite specific phrases from the email and candidate that drove the decision>"
}
```

The orchestrator maps `matched_label`/`distractor_labels` back from `A`/`B`/`C` to real `temp_id`s (and eventually DB `ticket_id`s), then diffs `difficulty_tier`/`should_match`/`matched_label` against what Template 4 was instructed to realize. Log every mismatch — don't silently overwrite either side.

---

## Pilot recipe (target: 20–30 tickets)

Scaled down from the full spec's 40 customers / ~5 tickets-per-customer ratio:

| Step | Count | Notes |
|---|---|---|
| Customers (Template 1) | 5 | 1 customer deliberately given 2 open tickets in the same category with similar (not identical) issue types, to exercise the disambiguation tier |
| Tickets (Template 2) | ~25 (avg 5/customer, range 3–7) | Don't force the full category-floor/20-per-category rule at this scale — just make sure every category appears at least once; let Claims/Payment Posting appear more often (matches their higher target share) |
| Conversations (Template 3) | ~25 (1 batched call per customer) | avg ~5 messages/ticket |
| Eval queries (Template 4) | ~20 | aim for at least 2–3 per difficulty tier so review can judge each tier, not just the average |
| Labels (Template 5) | ~20 | one per eval query; log all mismatches vs. intended label for review |

After this pilot: review realism, thread flow, label agreement rate (Template 5 vs. intended), and whether difficulty tiers actually read as intended difficulty — then refine wording here before freezing and building the automated batch pipeline.
