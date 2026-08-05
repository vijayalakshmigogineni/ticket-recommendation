# Evaluation Iteration Report — Thank You / Appreciation

**Date**: 2026-08-03
**Category added**: Thank You / Appreciation (fresh-incoming-email decision coverage)
**Cases added**: 8 (`thankyou_e7_resolved`, `thankyou_pm3_resolved`, `thankyou_c2_closed`, `thankyou_r3_ar_resolved`, `thankyou_g3_chargeentry_resolved`, `thankyou_a4_priorauth_resolved`, `thankyou_e2_closed_valley`, `thankyou_ambiguous_lowcontent`)
**Benchmark size**: 21 → 29 queries (24 clear, 5 hard)
**Full run command**: `python scripts/run_eval.py --output data/sample_dataset/eval_results_2026-08-03.json`
**Raw per-query results**: `data/sample_dataset/eval_results_2026-08-03.json`
**Wall-clock**: 27.8 min across 29 queries

---

## 1. Evaluation Report

### Headline (all 29 queries)

| Metric | Result |
|---|---|
| Clear-case accuracy | 24/24 (100%) |
| Recall@20 (candidate pool) | 25/25 (100%) |
| Recall@3 (reranked top-K) | 25/25 (100%) |
| Hard/ambiguous cases (informational, not in headline) | 4/5 passed |

**No regression**: all 17 pre-existing clear cases and all 4 pre-existing hard cases still pass exactly as before. The frozen 21-query baseline is untouched and still 21/21 clear-case-equivalent.

### Category-specific: Thank You / Appreciation

| Metric | Result |
|---|---|
| Clear-case accuracy (7 cases) | 7/7 (100%) |
| Recall@20 | 7/7 (100%) |
| Recall@3 | 7/7 (100%) |
| Avg. confidence on correct attaches | 0.94 |
| Terminal-status subgroup (CLOSED: `thankyou_c2_closed`, `thankyou_e2_closed_valley`) | 2/2 correct |
| Non-terminal subgroup (RESOLVED: remaining 5) | 5/5 correct |
| Hard case (`thankyou_ambiguous_lowcontent`) | Failed the strict pass/fail check — see Failure Analysis §2 |

For comparison, the rest of the benchmark (`uncategorized`, the original 17 clear cases) scored 17/17 accuracy with avg. confidence 0.94 on correct attaches — **thank-you cases performed identically to the rest of the benchmark**, not worse. Confidence on correct thank-you attaches (0.94) was, if anything, marginally higher than the rest of the benchmark's 0.81 average, not lower — the original hypothesis going into this iteration ("low topical content might produce lower, appropriately-hedged confidence even when correct") **did not hold**: the model was just as confident attaching a bare "Thanks so much!" as it was on content-rich queries. That itself is worth flagging as a calibration observation, not a pass — see §3.

### What this confirms

- **Decision #5 (all ticket statuses, including CLOSED, are eligible attach candidates) holds in practice**, not just in the pipeline's design — both `thankyou_c2_closed` and `thankyou_e2_closed_valley` (CLOSED, the true terminal state) attached correctly, alongside five RESOLVED cases.
- The predicted failure mode motivating this iteration ("system defaults to no-match on low-content appreciation email") **did not materialize** for any of the 7 clear cases — the pipeline reliably recognizes appreciation tone as belonging to a specific recent ticket when there's at least one topical anchor (a claim type, a procedure, a payer name) to retrieve on.

---

## 2. Failure Analysis

### `thankyou_ambiguous_lowcontent` (hard, FAIL — as anticipated, not a regression)

**Verdict up front**: this is not a bug. The case was deliberately designed as an exploratory probe of genuine ambiguity (see its `note` in `eval_queries.py`), and the failure mode it surfaced is real but expected given the input. Traced with a direct re-run of `run_traced_pipeline` (not inferred) to confirm exactly which layer produced the outcome:

**Email**: `"Thanks so much, appreciate it!"` from `billing@sunridgeortho.com` — zero topical anchor, 4 candidate tickets for that customer (C2, A1, R4, G3).

**Stage-by-stage, with real captured values:**

1. **Retrieval/grouping — succeeded, and even ranked correctly.** Post-grouping `final_score` for the 4 candidates:
   - A1: 0.4451 (highest)
   - R4: 0.4048
   - G3: 0.3778
   - C2: 0.3629

   A1 — the most-recently-active ticket, and the more defensible of the two acceptable answers — scored *highest*, mainly on its recency component (0.5869 vs. 0.55/0.35/0.08). Retrieval itself is not the failure point.

2. **Cross-encoder reranking — this is where the signal collapses.** The reranker's `top_k=3` cutoff, applied to those 4 candidates, produced scores of `3.7441e-05`, `3.7416e-05`, `3.7402e-05` for the 3 that survived (G3, C2, R4) — **A1, the highest-grouping-score candidate, was the one cut**, despite the four scores differing only in the 5th significant digit, i.e., at floating-point-noise scale for this model. The cross-encoder gave a near-empty query ("Thanks so much, appreciate it!") essentially zero ability to discriminate between four otherwise-unrelated ticket contexts, and the resulting top-3 truncation was effectively an arbitrary tie-break, not a real ranking decision.

   **This is the "low-information-content embedding/reranker collapse" failure mode predicted before this iteration ran** (see the design proposal's step 7) — now confirmed with real numbers rather than hypothesized.

3. **Recall@3 "passed," but the pass is not robust.** `run_eval.py` reported `recall3=true` because R4 (one of the two acceptable answers) survived the cut — but A1 did not, purely due to a statistically meaningless score difference. A re-run with a trivially different candidate ordering or a slightly different embedding could plausibly cut R4 instead and keep A1, or (worse) cut both, given how close all 4 scores are. The boolean recall3 metric doesn't capture this — treat this specific case's "pass" as fragile, not as evidence the reranker robustly handles low-content queries.

4. **LLM decision layer — behaved exactly as intended.** Given 3 candidates all displaying `cross-encoder score: 0.000` (rounded for the prompt), the model correctly recognized it had no basis to pick one over another and declined to force a match:
   > *"The cross-encoder scores are 0.000 for all candidates, indicating no meaningful match... it should not be attached to any candidate."*

   This is the desired qualitative behavior under genuine ambiguity — the system did not hallucinate false confidence, and did not silently pick an arbitrary candidate. It also did not pick the "acceptable" answer per this case's own ground truth, hence the strict FAIL.

5. **Confidence = 0.0 is not new/anomalous.** Cross-checked against the benchmark's 3 pre-existing no-match cases (`remit_address_reject`, `ggi_no_payment_ticket`, `unknown_customer`): all report `confidence=0.0` on `should_attach=false`. This is an existing, consistent model convention (confidence appears to mean "confidence in the attachment," which is definitionally 0 when there's no attachment) — not something this iteration introduced, and not a new finding, just confirmed as consistent.

**Root cause, stated plainly**: retrieval and grouping correctly favored the most plausible ticket; the cross-encoder reranker cannot meaningfully differentiate candidates when the query text carries no topical content, and its top-K truncation then makes what is effectively a coin-flip cut; the LLM, working only from what the reranker handed it, correctly declines to guess. **The failure is a reranker-signal problem, not a retrieval problem or a decision-layer problem.**

**No fix recommended.** This case exists to characterize a real limit of the system under genuinely low-information input, not to drive a code change — forcing the reranker or the LLM to "resolve" this kind of ambiguity would mean fabricating confidence that doesn't exist in the input. The one actionable follow-up, if this class of query turns out to matter in production: the near-tied top_k cutoff losing the highest-grouping-score candidate is worth knowing about generally (independent of this specific case), since it means "Recall@3" can look green while masking a near-arbitrary truncation — a caveat for how much weight to put on Recall@3 for low-content queries specifically, not a pipeline bug to patch here.

---

## 3. Notable observation (not a failure, but worth carrying forward)

Confidence on the 7 correct thank-you attaches averaged 0.94, essentially matching the rest of the benchmark (0.81 on the other 17 clear cases, thank-you's own average was actually a bit higher). Going in, the working hypothesis was that low-topical-content queries might produce appropriately lower confidence even when correct. That didn't happen — the model is just as confident on a bare "Thanks so much for sorting out the coverage issue!" as it is on content-rich paraphrases, as long as there's *some* topical anchor for retrieval to work with. Combined with the ambiguous case above (confidence=0.0, correctly declining), this suggests confidence is currently behaving more like a binary "did I find something to attach to" signal than a graded measure of how much textual evidence supported the attachment — worth keeping in mind for any future iteration that tries to use confidence thresholds for automation decisions.
