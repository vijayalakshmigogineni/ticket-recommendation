# Evaluation Iteration Report — Corpus Expansion Stage 0 + Stage 1

**Date**: 2026-08-03
**Work done**: Stage 0 (3 new eval queries against latent cross-customer lookalikes found by the Corpus Coverage Audit) + Stage 1 (enriched 7 single-interaction tickets — `A3`, `C4`, `E1`, `G1`, `P3`, `P4`, `R4` — with one grounded agent reply each, per `CORPUS_EXPANSION_ROADMAP.md`)
**Cases added**: 3 (`crosscust_a1_pm4_mri`, `crosscust_e1_pm5_eligibility`, `crosscust_p2_p5_era`)
**Corpus change**: 151 → 158 interactions (7 new agent replies), re-seeded and re-indexed (`scanned=155, embedded_this_run=7, already_current=148` — the 3 pre-existing `internal_note` interactions correctly excluded from embedding, per Decision #10)
**Benchmark size**: 53 → 56 queries (48 clear, 8 hard)
**Full run command**: `python scripts/run_eval.py --output data/sample_dataset/eval_results_2026-08-03e.json`
**Raw per-query results**: `data/sample_dataset/eval_results_2026-08-03e.json`
**Wall-clock**: 61.2 min across 56 queries

---

## 1. Evaluation Report

### Headline (all 56 queries)

| Metric | Result |
|---|---|
| Clear-case accuracy | **48/48 (100%)** |
| Recall@20 (candidate pool) | 52/52 (100%) |
| Recall@3 (reranked top-K) | 52/52 (100%) |
| Hard/ambiguous cases (informational, not in headline) | 5/8 passed |

**No regression from the corpus change**: all 45 previously-passing clear cases (including the 44 that passed before Stage 1, but excluding `archive_c4_claims_selfresolved` which had failed) still pass, plus all 3 new Stage-0 cases pass. That's the mandatory full-re-run check `CORPUS_EXPANSION_ROADMAP.md` required before accepting Stage 1 — passed.

**The headline number is back to 100%, and `archive_c4_claims_selfresolved` (the confirmed non-determinism case from the last iteration) now passes** — see §2 for what this does and doesn't prove.

### Stage 0: Cross-Customer Similarity (new category)

| Metric | Result |
|---|---|
| Clear-case accuracy (3 cases) | 3/3 (100%) |
| Recall@20 / Recall@3 | 3/3 / 3/3 |
| Avg. confidence | **0.99** — the highest of any category in the benchmark |

All 3 latent lookalike pairs the audit found (`A1`/`PM4`, `E1`/`PM5`, `P2`/`P5`) behaved exactly as the roadmap predicted: trivially easy, very high confidence, because customer-scoped retrieval means the decoy ticket was never structurally reachable as a candidate in the first place. This diversifies the cross-customer regression guard from 1 instance (`cross_customer_c1`) to 4, at zero cost.

### Stage 1: Interaction Enrichment

`archive_no_action` category accuracy moved from 6/7 to **7/7** — directly attributable to `archive_c4_claims_selfresolved` (targets `C4`, one of the 7 enriched tickets) now passing. No other enriched ticket (`A3`, `E1`, `G1`, `P3`, `P4`, `R4`) had a case that was failing before, so this is the only accuracy number that could have moved, and it did.

---

## 2. Failure Analysis (and one important non-failure worth scrutinizing)

### `archive_c4_claims_selfresolved` now passes — consistent with a fix, not proof of one

This run: `should_attach=true, ticket=C4, confidence=0.85`, clean reasoning. This matches the diagnostic re-trace from the *previous* report (also 0.85, same reasoning shape) — two independent observations of a pass, against one observed failure (the original run, before enrichment). That's suggestive but **not proof that non-determinism is eliminated for this case**: three observations isn't enough to distinguish "enrichment genuinely stabilized it" from "it was already right most of the time and the one recorded failure was an unlucky draw." Both are consistent with the data. Reported honestly as "passes now, plausibly because of the enrichment" rather than "confirmed fixed."

### `info_ambiguous_archive_boundary` — new evidence that broadens the non-determinism finding further

This hard case's acceptable set (`E1`, `A2`) failed again, but **its wrong answer changed from the last iteration**: previously `G4` (confidence 0.95), this run `C3` (confidence 0.8). Tracing this immediately after the eval run, with a *third*, independent diagnostic re-run, produced a *third* different answer: `A2` (confidence 0.8) — which would have been **correct**.

Real numbers across all three observations:

| Observation | Reranked top-3 (order) | Decision |
|---|---|---|
| Prior iteration (pre-enrichment) | A2, C3, **G4** | G4 (wrong) |
| This eval run (post-enrichment) | (inferred: A2, C3, — ) | C3 (wrong) |
| Diagnostic re-trace (post-enrichment, minutes later) | A2, C3, **E1** | A2 (**correct**) |

Grouping-stage scores are nearly identical across observations (e.g. `A2` final_score 0.5161→0.5149, `C3` 0.5153→0.5142 — noise-level differences, not a real shift from enrichment). **The instability is downstream of grouping, in the reranker itself**: cross-encoder scores for this near-zero-content query are degenerate in every observation (differing only in the 5th significant digit, e.g. `4.07e-05` vs `4.06e-05` vs `3.81e-05`) — genuinely too close together to represent a real ranking, and which candidate ends up 3rd (cut or kept) appears to vary run-to-run from that noise alone.

**This extends, rather than repeats, the last iteration's finding.** The previous report attributed non-determinism to the *LLM decision layer* specifically (retrieval and reranking were identical across both observed runs, only the LLM's conclusion changed). Here, the reranker's *own output* varies across runs on the same input — meaning the instability isn't confined to the decision layer. **On this category of query (near-zero topical content, multiple structurally-similar candidates), the entire stack from reranking onward is exhibiting run-to-run variance**, not just the final LLM call. This is a more precise, more concerning characterization than "the LLM is sometimes unstable," and is worth carrying forward as the accurate scope of the limitation.

**No fix applied.** Same reasoning as before: this is inherent to running a local reranker/LLM stack on genuinely low-information inputs, not a code defect. The actionable takeaway is purely about *how much weight to put on a single hard-case run* for this specific query shape — not much, since three observations produced three different answers.

### `thankyou_ambiguous_lowcontent` and `archive_ambiguous_lakeside`

Unchanged from prior reports — neither of these customers' tickets were touched by Stage 1 enrichment, and both still correctly decline to force a guess (confidence 0.0) under genuine ambiguity. No new analysis needed.

---

## 3. Notable observation

This iteration's biggest methodological lesson: **when a query's reranked candidate set is built from degenerate, near-tied cross-encoder scores, treat that case's outcome as a single noisy sample, not a stable measurement** — regardless of which specific stage (reranker or LLM) turns out to be the proximate source of variance in a given trace. Three separate observations of `info_ambiguous_archive_boundary` produced three different answers; a single re-run of any such case, in either direction, shouldn't be over-interpreted. This doesn't change how the case is scored (still an honest, informational hard-case tracking, never counted in headline accuracy) — it changes how much confidence to place in any *specific* trace's explanation as "the" reason for an outcome on this query shape.
