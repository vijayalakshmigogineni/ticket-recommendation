# Length & Style Distribution — P2, G2, E4 Enrichment + 9 New Eval Cases

**Date**: 2026-08-05
**Type**: corpus + benchmark change (Production Readiness Roadmap, Task 1). Full re-run mandatory per standing rule.
**Corpus change**: 175 → 204 interactions. `P2` (payment_posting) 2→7, `G2` (charge_entry) 2→17, `E4` (eligibility) 3→12 — three different narrative shapes (a reconciliation that never fully closes, an NCCI-bundling coding dispute, a Medicare-eligibility-onset coordination-of-benefits saga), not three variations on the denial→appeal→resolution template already used elsewhere.
**Benchmark change**: 62 → 71 queries. 9 new `length_style_distribution` cases (3 short, 3 medium, 3 long — 10-20+ meaningful lines each) against a deliberate mix of the newly-deepened tickets and already-validated deep tickets from the prior pass (`A3`, `R2`, `C4`, `A6`).
**Result**: **63/63 clear-case accuracy (100%), zero regression.** Recall@20/@3 both 100%. Hard-case pattern unchanged (5/8, same 3 known cases). New category: **9/9 (100%), avg. confidence 0.98** — highest of any category in the suite. Total eval time 69.7 min across 71 queries (real LLM decision latency, not a hang).

## What changed, and why it matters for production

The Production Readiness Roadmap's Task 1 combined three things into one workstream: give the 3 RCM services with zero conversational depth (payment posting, eligibility, charge entry) real multi-week history, add long-form (10-20+ line) incoming emails to the benchmark for the first time, and make sure the length *distribution* is realistic — a mix of short acknowledgements, medium updates, and detailed explanations, not just long ones, per explicit direction. The 9 new cases: 3 short (1-line ack/casual-lowercase-followup/thank-you-close), 3 medium (5-8 line status updates with a specific question each), 3 long (10-20+ line recaps with numbered questions, attachment references, greetings/signatures). Targets deliberately mix newly-deepened tickets (`P2`, `G2`, `E4`) with already-validated ones (`A3`, `R2`, `C4`, `A6`) so a failure could be attributed to email length/style rather than ticket novelty.

## A real design correction made mid-task, not just executed as originally scoped

The roadmap's original ticket selection (from the prior turn) picked `E5` for the eligibility slot. Before writing any content, I checked every existing eval case referencing `P2`, `E5`, and `G2` — the same discipline the `C4`/`E2` incident taught us to apply proactively — and found two real conflicts:

- `info_p2_payment_discrepancy` and `crosscust_p2_p5_era` both require `P2` to stay an *unresolved, mid-investigation* ticket. My first-draft plan for `P2` ended in a full resolution, which would have contradicted both. Fixed by redesigning `P2`'s arc to deepen the investigation (ruled out one hypothesis, escalated to the payer's provider rep, still no answer) without ever closing it — a more realistic shape for a payment reconciliation anyway.
- `archive_e5_eligibility_rescheduled` requires `E5` to stay a same-day, patient-still-waiting scenario ("no need to keep chasing... today," "we'll resend when they come back in"). A multi-week saga is fundamentally incompatible with that premise — eligibility tickets are often inherently time-bound/urgent by nature (checking coverage before a visit), unlike claims/prior-auth/charge-entry, which can legitimately span weeks. **Swapped `E5` for `E4`** (coastal_derm, a secondary-Medicaid-then-Medicare-onset coordination-of-benefits story with no such constraint) rather than force an incompatible shape onto a ticket that structurally can't hold it.

This is worth generalizing: not every RCM service is equally suited to a "multi-week saga" shape, and forcing one onto a ticket with an urgency-bound premise breaks existing eval cases rather than just risking retrieval regressions.

## The reranker-truncation risk the roadmap flagged, checked directly

The roadmap named a specific, previously-untested risk: cross-encoder rerankers typically have a hard token limit (confirmed: `BAAI/bge-reranker-base`, 512 tokens), and a long incoming email plus a long ticket context could silently exceed it — which could still produce a "correct" benchmark answer by luck while masking a real defect. Measured directly (real tokenizer, real DB content, worst-case match on each ticket's most recent interaction) for all 3 long-email cases:

| Case | Ticket (total interactions) | Query tokens | Context tokens | Pair tokens fed to model | Truncated? |
|---|---|---|---|---|---|
| `lendist_long_recap_g2` | G2 (17) | 281 | 103 | 388 / 512 | No |
| `lendist_long_followup_a6` | A6 (10) | 216 | 190 | 410 / 512 | No |
| `lendist_long_detailed_e4` | E4 (12) | 244 | 131 | 379 / 512 | No |

No truncation in any case, with 100+ tokens of headroom in the tightest one. This holds because the context builder windows around matched interactions (max 2 matched × ±1 neighbor, per `config.py`) rather than including full ticket history — so ticket depth doesn't inflate reranker input size, only the incoming email's own length does. **This is real headroom, not a permanent guarantee** — a genuinely longer incoming email, or a future change to the neighbor-window settings, could still hit the limit. Worth re-checking if either changes.

## Bottom line

All 9 new cases pass cleanly at high confidence (0.98 avg). The full re-run's 100% Recall@20/@3 across all 71 queries — which includes an eval case for every other ticket in both `coastal_derm` (`R1`, `E4`) and `riverside_family_medicine` (`C1`, `P4`, `R3`) pools — is itself the sibling-pool spot-check the `C4` incident taught us to do proactively; no spillover occurred this time. Corpus now has real depth in all 6 RCM services (previously 3 had zero), with 3 different narrative shapes (unresolved reconciliation, coding dispute, coordination-of-benefits) rather than repeating the denial→appeal→resolution template.

## Still open
Task 2 (attachment-referenced/insufficient-content emails, needs a design decision on a "mandatory human review" output category) and Task 3 (customer identification robustness, needs its own design discussion) per `PRODUCTION_READINESS_ROADMAP.md` — not started.
