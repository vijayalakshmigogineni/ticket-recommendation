# Benchmark Dataset Specification

Status: **Finalized** (2026-07-23). This is the design for the synthetic data — both the ticket corpus (what gets stored/embedded) and the evaluation query set (labeled test emails used to score retrieval). Schema implementation lives in code (`app/models.py`), not here — this doc is the *data design*, not the *table design*.

## 0. Business Workflow (read this first)

This section explains the real-world process this benchmark models, so the
category taxonomy, corpus design, and evaluation-set scoping below make sense.

**Every incoming email first reaches an Account Manager (AM).** The AM
decides whether it requires operational work.

**Case 1 — No operational work.** Purely informational or general-query
emails are replied to or archived directly. No ticket is ever created, and
no retrieval happens — the AM never checks these against open tickets.

**Case 2 — Operational work required.** The AM either creates a new ticket,
or determines the email belongs to an existing OPEN ticket (one ticket = one
operational issue). Once a ticket exists, all subsequent communication for
that issue becomes part of its history, in one of two ways:

- **2A — Automatic threading (no AI).** If the client replies within the
  existing email thread, the communication platform associates it with the
  ticket automatically, by thread — no retrieval needed. This is why an OPEN
  ticket's history naturally includes non-operational content too
  (documentation, thank-yous, status checks, informational asides): they
  arrive as ordinary thread replies after the ticket already exists.
- **2B — New independent email (AI retrieval required).** Sometimes a client
  starts a fresh email instead of replying — new subject, a different
  employee, a forwarded message, or broken threading. The platform can't
  auto-associate it, so the AM must determine whether it belongs to one of
  the currently OPEN tickets. **This is the one decision the retrieval
  system exists to support** — recommending the most likely OPEN ticket
  match with a confidence score. It does not decide whether to create a
  ticket, and it is never invoked for Case 1 or Case 2A.

**Retrieval Benchmark Scope:** this benchmark evaluates only the semantic
retrieval component described in 2B above — nothing else in the AM's
workflow. It does **not** evaluate ticket-creation decisions, email
classification, automatic replies, ticket assignment, or any other
workflow automation. The only question in scope: given a new, independent
email, does the retrieval system correctly identify the existing OPEN
ticket it belongs to, or correctly determine that no suitable OPEN ticket
exists?

This is why the ticket corpus and the evaluation query set are built
differently — see "Two distinct artifacts" below.

## Two distinct artifacts

1. **Ticket corpus** — simulates "existing tickets," the OPEN/CLOSED ticket
   history an AM has already built up. Customers, tickets, messages. Per the
   Business Workflow above, a ticket's thread is NOT limited to operational
   content — most follow-ups arrive via automatic email threading (Case 2A,
   no AI involved), so a realistic thread naturally mixes the initial
   operational request with documentation, follow-ups, status checks,
   informational asides, and thank-yous. This is exactly what §3's
   message-intent structural template already models. No special
   ground-truth labels beyond natural fields (category, issue_type, intent,
   etc.) — this is the substrate that gets embedded and searched. **Only
   OPEN tickets are embedded and searched by the baseline retrieval index**
   — CLOSED tickets remain part of the generated corpus (useful for future
   research such as historical lookup or ticket-reopening logic, per
   `PROJECT_PLAN.md`'s open closed-ticket-lookback question) but are
   excluded from the baseline index, consistent with this project's
   existing OPEN-only search-scope decision.
2. **Evaluation query set** — separately generated incoming emails that
   model Case 2B specifically: a new, independent email that broke
   automatic threading, where the AM must decide (with the retrieval
   system's help) whether it belongs to an existing OPEN ticket. Each
   carries an explicit ground-truth label (correct ticket or none,
   should-match, difficulty, reasoning). Two outcomes are both in-scope and
   both scored: **should_match=true** (belongs to a specific OPEN ticket —
   attach) and **should_match=false** (belongs to none — the `hard_negative`
   tier; what the AM does next, e.g. creating a new ticket, is outside this
   benchmark's scope). Explicitly OUT of scope for this set: emails that
   never reach a retrieval decision at all — Case 1 (informational/general
   query) and Case 2A (in-thread replies). Those only appear inside ticket
   corpus conversations (#1 above), never as scored eval queries.

## 1. Scale

| | Count | Notes |
|---|---|---|
| Customers | 40 | |
| Tickets | ~200 | avg 5/customer, range 1–10 |
| — open at snapshot | ~65% (~130) | majority open, matches baseline search scope |
| — closed at snapshot | ~35% (~70) | material for closed-ticket-lookback work later |
| Messages (corpus) | ~1,000 | avg 5/ticket, range 2–15 (deliberately spans above/below `MAX_RECENT_INTERACTIONS=10`) |
| Eval queries (labeled) | ~350 | see difficulty breakdown below |
| Customers w/ ≥2 concurrent open tickets, same category, with semantically similar (not necessarily identical) issue types | ≥10 | required for the disambiguation tier to be meaningful — category alone (operational team) is now too coarse to guarantee genuine difficulty, but requiring *identical* issue_type would be a stricter (and less realistic) test than production ambiguity actually is |

Starting point, not fixed — cheap to scale up later since generation is parametric. Plan: pilot (~20–30 examples) → manual review → full generation, not full generation on the first try.

## 2. Ticket category & issue type

**Category = operational team ownership.** Every ticket belongs to exactly
one of the RCM organization's operational teams:

Claims 25% · Payment Posting 18% · Prior Authorization 16% · Accounts
Receivable 15% · Eligibility 14% · Charge Entry 12% — **minimum 20
tickets/category** at full ~200-ticket scale regardless of percentage (scale
the floor proportionally at other scales).

**Issue Type = the specific business problem**, nested under a category — a
closed enum per category (not free text), used as generation/QA metadata,
not exposed in email text. Ticket realism and diversity come from varying
grounding facts (payer, patient, claim number, denial reason, documentation,
dates, procedure) within an issue type, not from inventing new issue-type
labels.

| Category | Issue Types |
|---|---|
| Claims | Claim Denial · Missing Modifier · Timely Filing · Duplicate Claim · Medical Necessity · Coordination of Benefits · Documentation Request from Payer · Claim Rejection (Clearinghouse) · Claim Status Inquiry · Incorrect Diagnosis Code · Corrected Claim Needed |
| Prior Authorization | Authorization Denied · Authorization Expired · Missing Authorization · Peer-to-Peer Review Required · Incomplete Authorization Request · Retro Authorization Needed · Missing Clinical Documentation · Authorization Status Inquiry · Wrong Procedure Authorized · Auth Renewal for Ongoing Treatment |
| Payment Posting | Underpayment · Overpayment/Refund Request · ERA/EOB Discrepancy · Payment Posted to Wrong Account · Missing Payment · Contractual Adjustment Mismatch · Duplicate Payment Posted · Unapplied/Unidentified Payment · Patient Payment Reconciliation · Payment Plan Posting Issue |
| Eligibility | Coverage Termination · Effective Date Discrepancy · Plan/Payer Change · Benefits Verification Needed · Ineligible for Service · Coordination of Benefits (Eligibility Stage) · Supporting Documentation Required · Incorrect Member ID/Demographic Mismatch · Referral Requirement Confirmation |
| Accounts Receivable | Aging Balance Follow-up · Patient Balance Dispute · Write-off Request · Payment Plan Setup · Collections Escalation · Unapplied Credit Resolution · Refund Processing Delay · Account Reconciliation Request · Bad Debt Referral Status |
| Charge Entry | Missing Charge · Incorrect CPT/Procedure Code · Incorrect Units Billed · Late Charge Submission · Coding Discrepancy · Modifier Missing at Entry · New Provider Charge Setup · Charge Template Configuration · Incorrect Fee Schedule Applied |

Retired from the old taxonomy: `insurance_verification` → renamed
**Eligibility**; `documentation_request` → folded into issue types above
(Claims/Prior Auth/Eligibility, per context); `new_service_request` →
folded into Charge Entry issue types; `general_enquiry` → no longer a
ticket category at all (these are Case 1 emails — no ticket, per Business
Workflow above).

This is the **default controlled vocabulary for Benchmark v1**. New issue
types can be added under a category in future versions without changing the
Category/Issue Type structure, the generation templates, or the QA
pipeline — this list is a starting point, not a permanent ceiling.

## 3. Message intent — structural template, not IID sampling

Message 1 of every ticket = `initial_request` (always). Middle messages mix `follow_up` (~35% overall) / `documentation_provided` (~15%) / `status_check` (~15%). A `thank_you` (~10%) or `informational` (~7%) message *may* appear near the end of a thread, not mandatory. Intent is a function of thread position, not an independent random draw per message — real threads have shape, and boilerplate (`thank_you`/`informational`) realistically clusters at thread-end.

## 4. Difficulty tiers

| Tier | Definition | Tests | Target share |
|---|---|---|---|
| Easy | Clear restatement, explicit identifiers | Sanity floor | 15% |
| Moderate (paraphrase) | Same issue, reworded, no lexical overlap needed | Semantic robustness beyond keyword overlap | 25% |
| Hard semantic | Vague/indirect phrasing, no explicit identifiers | Robustness to messy, underspecified language | 20% |
| Hard negative | Unrelated issue that looks textually similar to an open ticket | False-positive avoidance | 15% |
| Boilerplate/generic | "Thanks", "Any update?", "Attached." | Confidence should drop with low content, not spike by luck | 10% |
| Same-customer disambiguation | 2+ distinct open tickets, same customer, same category | Fine-grained disambiguation — the sharpest version of the real business problem | 15% |

Weighted toward the harder 75% deliberately — an easy-dominated benchmark would look good and prove nothing.

Note on `hard_negative`: this tier is scoped to Case 2B (§0) — situations
where retrieval is genuinely invoked because threading broke. The correct
retrieval outcome is "no OPEN ticket matches" (`should_match=false`); it is
not a judgment about whether the AM should create a new ticket, which is
outside this benchmark's scope. It remains in retrieval-accuracy scoring
because avoiding false-positive matches is itself a retrieval-accuracy
property (see "Two distinct artifacts" above).

Also note on `same_customer_disambiguation`: "same category" in the table
above means same category, with **semantically similar** (not necessarily
identical) issue types (see §2) — e.g. Claim Denial vs. Claim Rejection
(Clearinghouse), or Missing Modifier vs. Incorrect Diagnosis Code, are
plausible disambiguation pairs within Claims; Claim Denial vs. Documentation
Request from Payer would not be, despite sharing a category.

## 5. Writing variation — orthogonal to difficulty

Sampled independently per email, not tied to difficulty (avoids confounding "bad at semantics" with "bad at typos"):

- Tone: professional / casual — 60% / 40%
- Length: short / medium / long — 25% / 50% / 25%
- Noise: clean / mild typos+abbreviations / heavy jargon+typos — 60% / 30% / 10%
- RCM terminology density: loosely correlated with category, still varies within category

## 6. Ground-truth schema (per eval query)

`query_id`, `email_text`, `customer_id`, `correct_ticket_id` (nullable), `should_match` (bool), `difficulty_tier`, `distractor_ticket_ids` (other plausible-but-wrong candidates, mainly populated for hard_negative/disambiguation), `reasoning` (free text — why this label, doubles as QA documentation), `style_tags` (tone/length/noise, for slicing metrics independent of difficulty). Note: each ticket referenced here now also carries a `category` and `issue_type` (see §2).

QA note: ~10% of the generated eval set should be manually spot-checked before Phase 6 — LLM-generated "reasoning" can be self-consistent but wrong.
