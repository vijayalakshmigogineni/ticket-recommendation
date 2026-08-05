# Pilot QA Report

Ran the full `docs/generation_qa_checklist.md` gate over the pilot dataset in `pilot/raw/` (5 customers, 25 tickets, 128 messages, 20 eval queries, 20 blind-judge labels), adapted for the schema correction earlier this session (no `issue_type` anywhere — checks that referenced it are simply not applicable; category checks use the real 6-team enum). *(A 7th category, `patient_calling`, briefly existed in the schema during this session and was tested at 0 tickets in this pilot — since removed entirely per a since-confirmed decision that it's being phased out of production too, not just irrelevant to an email-driven benchmark; see `PROJECT_PLAN.md`.)*

## Methodology limitation — read this first

I generated Templates 1–4 *and* performed the Template 5 blind judge pass myself, in the same conversation. The whole point of Template 5 being a separate pass is independence from construction intent — that's only partially achieved here: I deliberately judged from the anonymized candidate pool and email text alone, without consulting the "constructed" answer until after forming a judgment, but I can't rule out latent bias from having authored both sides. `docs/execution_roadmap.md` Phase 6 already calls for Template 5 to be a genuine separate API call once the pipeline is automated — this pilot is a reminder why that separation matters, not a substitute for it.

## Rule-based checks (§1–§4, §6)

| Check | Result |
|---|---|
| Customer required fields, email format, no duplicates | PASS (5/5) |
| Ticket category/status are valid enum values, match manifest assignment | PASS (25/25) |
| Closed-ticket date logic (`closed_at_offset_days` present, more recent than `created_at_offset_days`) | PASS (7/7) after refinement — see finding #1 |
| Sibling distinctness (tkt_3_1/tkt_3_2): distinguishing_details non-empty, claim/patient differ | PASS |
| Message 1 = client + initial_request | PASS (25/25) |
| Day offsets non-decreasing per thread | PASS (25/25) |
| Sender-alternation degeneracy (no 3+ same-sender run unless ≤3 messages) | 3 threads flagged (tkt_1_3, tkt_1_5, tkt_5_5) — see finding #2, accepted as realistic |
| Grounding facts (claim/patient/payer) consistent between seed and message text | PASS, spot-checked across all 25 |
| Eval query: non-empty, no label-leakage, no broken character, valid style-tag enums | PASS (20/20) |
| Style-tag word-count bins | 3 boilerplate queries fall under the "short" bin's 10-word floor — see finding #3, accepted as a bin-calibration gap, not an error |
| Batch-level distribution: noise_level | 0/20 queries used `heavy` (spec target ~10%) — flagged for full-scale generation, not a pilot-blocking issue at this sample size |

## Judgment-based checks (Judge 1 / Judge 2 equivalent, done inline)

- **Category fit** (all 25 tickets): reviewed against the redefined 6-team model — every ticket's issue reads as genuinely belonging to its assigned category (e.g. `tkt_5_3`'s "new provider not yet set up for billing" fits Charge Entry; `tkt_2_2`'s aging patient balance fits Accounts Receivable). PASS.
- **Sibling pairing plausibility** (tkt_3_1 vs. tkt_3_2): both are Claims-category epidural-injection denials for the same customer, different patient/payer/denial-reason — genuinely the kind of pair an AM could mix up. PASS.
- **Distractor realism**: strong for the hard_negative and disambiguation tiers (same customer + same category + genuinely similar procedure/vocabulary in every case). One soft/weak distractor flagged: q_10's distractor D (`tkt_5_3`, "waiting on more info") is only loosely confusable with the target (payer-approval wait vs. credentialing wait) — kept as a legitimate but weak distractor, not removed.

## Finding #1 (fixed): two tickets' `closed_at_offset_days` were internally inconsistent with their own conversation

`tkt_1_3` and `tkt_1_5` are marked resolved/closed at a point *earlier* than their own last message's `day_offset` implied — i.e. the ticket seed said the ticket closed before the generated conversation's final message would have occurred. Concretely: `tkt_1_3` was seeded as closing 8 days after creation, but its 5-message thread's last message lands at day 10; `tkt_1_5` was seeded as closing 30 days after creation, but its 7-message thread's last message lands at day 40.

**Fixed**: adjusted `closed_at_offset_days` on both (`tkt_1_3`: -22 → -20, `tkt_1_5`: -40 → -30) so the ticket's stated close date now falls on/after its thread's final message, consistent with the QA checklist's "closed-ticket resolution shape" rule. This is exactly the kind of cross-field consistency bug the QA gate exists to catch before scale — worth building as an automated check in Phase 6's pipeline (`final_message_day_offset <= closed_at_offset_days - created_at_offset_days`), not just a manual spot-check.

## Finding #2 (reviewed, accepted): three long threads have a 3-message same-sender run

`tkt_1_3`, `tkt_1_5`, and `tkt_5_5` each have a stretch of 3 consecutive account-manager messages (sequential status updates on a multi-step prior-auth appeal or a long Medicare reprocessing issue, with the client not replying to each one). The QA rule flags this by design rather than silently passing it, but explicitly allows it as "occasionally realistic" — and it reads as realistic here (an AM tracking a slow external process while the client waits). No change made.

## Finding #3 (fixed): boilerplate tier was under-specified — a real ground-truth-agreement failure, not cosmetic

This is the most important finding, and exactly what the pilot's QA gate was designed to surface before scaling up.

**What happened**: the original `q_15`/`q_16`/`q_17` (boilerplate) were written as genuinely content-free ("just checking in - any update?"). When I ran the blind Template 5 judge pass against each customer's *full* open-ticket pool (not just the intended target), I found these three were **not actually resolvable** — a customer with 3–4 open tickets and a message with zero discriminating content gives a truly blind judge no way to pick one ticket over the others. That's a real property of Case 2B (the message arrived as a new independent email, broken threading, no other context) — in production, this kind of message almost always arrives as an ordinary thread reply (Case 2A) precisely *because* it has nothing new to say, which is why it's rarely a genuine retrieval problem in practice. Constructing it as a Case 2B eval query only works if it happens to carry at least one discriminating word.

**Effect on the headline metric**: this pushed the pilot's ground-truth agreement rate to **17/20 (85%)** — below the ≥90% bar proposed in `docs/execution_roadmap.md` Phase 4 — and all three disagreements traced to the same root cause, not scattered noise. That's a healthy signal: a systemic issue is far easier to fix than random drift.

**Fix applied**: revised all three queries to keep the boilerplate register (still terse, still low-effort) but include exactly one topically-unique word per customer's open-ticket set (`"that payment posting thing"`, `"the refund thing"`, `"the medicaid thing"`). Re-ran the blind judgment on the revised text: all three now resolve cleanly to their intended ticket. **Revised agreement rate: 20/20 (100%)**.

**Recommendation for the docs** (not done in this pass, flagged as follow-up per this session's established pattern): `benchmark_dataset_spec.md`'s boilerplate tier definition and `generation_prompts.md`'s Template 4 boilerplate instructions should state explicitly that a boilerplate message must retain *at least one* topically-discriminating token when the customer has more than one open ticket — "low content" should not mean "zero content." Also worth a matching QA rule addition: check that a boilerplate query's discriminating token set doesn't overlap with more than one open ticket's summary.

## Summary metrics

| Metric | Before refinement | After refinement |
|---|---|---|
| Ground-truth agreement (Template 4 vs. Template 5) | 17/20 (85%) | 20/20 (100%) |
| Unresolved FAILs | 0 (the boilerplate issue is a tier-design finding, not a broken individual item) | 0 |
| FLAGs | 2 categories (date-consistency bug, sender-alternation runs) + 1 style-bin calibration note | Date bug fixed; alternation runs reviewed and accepted; style-bin note carried forward as a docs recommendation |
| Category/tier coverage | Every category ≥1 ticket; every difficulty tier ≥3 eval queries | Unchanged |

## Recommendation

This pilot is in good enough shape to inform prompt refinement (`docs/execution_roadmap.md` Phase 5) — the one substantive issue found (boilerplate under-specification) has a clear, cheap fix that should be folded into the frozen prompt wording, not re-discovered at full scale. The date-consistency bug (#1) suggests Phase 6's automated pipeline should add that specific cross-field check as an automated rule, since a human eyeballing 25 tickets caught it, but it would be easy to miss at 200.
