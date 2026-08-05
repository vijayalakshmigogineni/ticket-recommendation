# Corpus Expansion Roadmap

Companion to `CORPUS_COVERAGE_AUDIT.md` (the audit that motivated every stage below) and `BENCHMARK_COVERAGE_REVIEW.md` (the equivalent living document for eval-query work). This file tracks the staged plan for growing the corpus's realism and structural difficulty, one measured step at a time — **status per stage reflects what's actually been approved and done, not the full plan as a fait accompli.** Update this file's status column whenever a stage is approved, executed, or its results change the plan for later stages.

**Agreed process for this roadmap** (2026-08-03): approve and execute one stage (or a small approved batch) at a time, re-run the full benchmark after any corpus change, and review measured results before deciding whether the next stage is still needed or should be adjusted — never commit to the full roadmap upfront.

---

## Stage 0 — Mine existing latent structural difficulty (not corpus expansion)

**Status: DONE (2026-08-03).** 3/3 passed, avg. confidence 0.99 (the highest of any category in the benchmark) — exactly as predicted, since customer-scoped retrieval makes these structurally easy. See `eval_reports/2026-08-03_corpus_stage0_stage1.md`.

| | |
|---|---|
| Objective | Write eval queries against 3 cross-customer lookalike pairs the audit found already existing in the corpus but never tested: `A1`/`PM4` (both MRI denials, "insufficient conservative treatment"), `E1`/`PM5` (both "Eligibility verification failed for new patient"), `P2`/`P5` (both ERA-vs-contracted-rate mismatches). |
| Rationale | Free, zero-risk value the corpus already paid for — should be captured before spending effort building new structural difficulty from scratch. |
| Expected retrieval benefit | Tests the cross-customer similarity guard (already proven once via `cross_customer_c1`) against 3 more real, naturally-occurring lookalike pairs. |
| Regression risk | **None.** Pure eval-query addition — same safety profile as every prior iteration; cannot affect the database or any other query's result. |
| Type | New eval queries only. No corpus changes. |
| Full re-run required? | Yes, as with every iteration (to confirm no regression and get real category/hard-case numbers), but not because of *risk* — because that's how every iteration's report has been produced. |

## Stage 1 — Enrich thin (single-interaction) tickets

**Status: DONE (2026-08-03).** Corpus grew 151→158 interactions (re-seeded, re-indexed: `scanned=155, embedded_this_run=7, already_current=148`). Full benchmark re-run: **48/48 clear-case accuracy (100%), zero regression** on the 45 previously-passing clear cases. `archive_c4_claims_selfresolved` (the confirmed non-determinism case from the prior iteration) now passes — consistent with the enrichment stabilizing it, though 2 passing observations vs. 1 failing one isn't proof, just suggestive. One hard case (`info_ambiguous_archive_boundary`, not itself an enriched ticket's case, but sharing a customer — `metro_cardiology` — with enriched ticket `E1`) produced a *third* different wrong answer across observations, revealing the reranker itself (not just the LLM) varies run-to-run on near-zero-content queries. See `eval_reports/2026-08-03_corpus_stage0_stage1.md` for full detail.

| | |
|---|---|
| Objective | Add at least one realistic agent-side reply to the 7 non-frozen single-interaction tickets: `A3`, `C4`, `E1`, `G1`, `P3`, `P4`, `R4`. |
| Rationale | 18% of the corpus (9/50 tickets) had zero staff-side trace — the least realistic ticket shape possible, and the audit's highest-priority finding. |
| Expected retrieval benefit | Richer per-ticket context for the context-builder/reranker stages; tests whether adding real agent-side language changes retrieval behavior for tickets that previously relied on customer text alone. |
| Regression risk | **Real.** All 7 are existing eval targets (including `archive_c4_claims_selfresolved`, the confirmed-non-determinism case) — enrichment changes what gets embedded for these tickets. |
| Type | Enriches existing tickets. No new tickets, no new customers. |
| Full re-run required? | **Yes, mandatory** — this change is not safe by construction. |
| Explicit exclusion | `PM1` and `PM7` are also single-interaction but belong to the **frozen original 21** — deliberately excluded from this stage. Enriching either would mean redefining what "frozen baseline" means, which is a separate decision requiring its own explicit approval, not something to fold into a routine pass. |

---

## Stage 2/3 — SUPERSEDED (2026-08-04): deep-enriched existing tickets instead of adding new ones

**Status: DONE (2026-08-04).** The original framing below (add a *new* ticket to `harborview_bh`; add a *new* long-running ticket elsewhere) was reconsidered during planning and replaced with a lower-risk alternative: enrich *existing* thin tickets into realistic multi-week arcs instead of growing any customer's candidate-pool size. Executed: `R2` (harborview_bh, accounts_receivable, 2→8 interactions, ~33-day patient-balance-dispute-to-payment-plan arc) and `A3` (valley_womens_health, prior_authorization, 2→8 interactions, ~38-day denial-appeal-reprocessing arc). Corpus grew 158→170 interactions.

A production-relevant issue was found and fixed during this work, not just a statistical curiosity: enriching `A3` caused a different ticket in the same customer pool (`C4`) to start losing to a stale, thematically-unrelated candidate (`E2`) — the system was confidently (0.8-0.9) attaching to the wrong ticket, which matters because a confidently-wrong recommendation is worse for a real Account Manager's trust than an honest decline. Root cause: `C4` was already a thin, weakly-anchored ticket competing in a now-more-crowded pool. Fixed by enriching `C4` too (2→7 interactions, its own ~23-day timely-filing-dispute arc), which resolved the misattribution. Full re-run after all three changes: **54/54 (100%), zero regression.** See `eval_reports/2026-08-04_corpus_a3_r2_c4_enrichment.md`.

`harborview_bh`'s remaining ticket (`P3`) and a brand-new long-running ticket for a customer other than `pinehill_ophtho` are no longer planned as separate stages — reassess after this baseline if still needed.

## Stage 4 — One new structural-difficulty construct

**Status: PROPOSED, not approved. Lowest priority — defer until Stage 0 shows whether more structural difficulty is actually still needed.**

Add a genuinely new near-duplicate/lookalike construct (4-way same-customer near-duplicate, or a second same-customer 2-way pair) not already latent in the corpus. New tickets; new customer if same-customer near-dup, mixed if cross-customer. Regression risk and re-run requirement depend on whether any existing customer is touched.

## Stage 5 — Internal-note realism (cosmetic)

**Status: PROPOSED, not approved. Lowest priority.**

Add a handful of `internal_note` interactions for realism. Zero regression risk by construction (internal notes aren't embedded/retrieved per the production contract) — cosmetic only, not a retrieval-quality change.

---

*As of this writing (2026-08-03): Stages 0 and 1 are DONE — see `eval_reports/2026-08-03_corpus_stage0_stage1.md` for full results (48/48 clear-case accuracy, zero regression, the previously-flaky `archive_c4_claims_selfresolved` now passing, and a new finding that reranker-level non-determinism, not just LLM-level, affects near-zero-content hard cases). Stages 2-5 remain proposed only, pending explicit review of these results and a decision on whether/how to adjust them — per the agreed iterative, measured-results-driven process. No further corpus changes have been made.*
