# Noise-Floor Findings

**Purpose**: this project confirmed non-determinism at two separate pipeline stages (the LLM decision layer and the cross-encoder reranker) across four benchmark iterations, but every prior observation was a single run -- discovered reactively, only because a case happened to fail and get traced. Nothing had ever deliberately re-run the same query multiple times to measure how often it actually flips. This document is that measurement. Read `EVAL_HISTORY.md` for the benchmark-run index and `eval_reports/` for the iteration reports this builds directly on -- this doc doesn't repeat their findings, it quantifies them.

**Method**: `scripts/run_eval.py --repeat N --keys <query keys>`, added specifically for this. Two batches, run back-to-back on 2026-08-04:
- 4 cases previously flagged for possible instability, N=5 each (20 runs)
- 5 stratified clear cases spanning different categories/customers/code paths, N=3 each (15 runs), to check whether instability exists anywhere it hasn't been noticed yet

Raw output: `noise_floor_known_flaky_2026-08-04.json`, `noise_floor_clear_sample_2026-08-04.json`. Model info recorded with both runs: `qwen3:4b` (digest `359d7dd4...`, Q4_K_M, unchanged since 2026-07-28) and `nomic-embed-text` (F16) -- see those files' `model_info` block. Any future result shift can now be checked against this digest before assuming pure sampling noise.

---

## Headline result

| Query | New observations (N) | Historical observations | Combined pass rate | Verdict |
|---|---|---|---|---|
| `info_ambiguous_archive_boundary` | 5 | 3 | **1/8 (12.5%)** | **Confirmed unstable, and worse than previously characterized** -- see below |
| `archive_ambiguous_lakeside` | 5 | 1 | **4/6 (66.7%)** | **Confirmed unstable -- prior characterization was based on the minority behavior** |
| `archive_c4_claims_selfresolved` | 5 | 3 | **7/8 (87.5%)** | Meaningfully stabilized by Stage 1 corpus enrichment, not fully eliminated |
| `thankyou_ambiguous_lowcontent` | 5 | 1 | **0/6 (0%), but 6/6 identical** | Stable -- reliably declines every time, not flaky |
| 5 stratified clear cases | 3 each (15 total) | -- | **15/15 (100%), 0 instability** | No hidden instability found outside the already-known ambiguous-hard cluster |

**The single most important finding**: `info_ambiguous_archive_boundary` was previously described (across two prior reports) as producing "a confident, content-grounded but debatable choice" and, separately, as evidence that "the reranker's own scores... vary run-to-run." Both were accurate as far as they went. What wasn't visible from 1-3 observations is the actual distribution: across all 8 observations now on record, this query landed on the specific **wrong** answer `C3` four times (confidence 0.7-0.8 -- not a hedge), declined twice, and was only actually correct **once**. This is a worse and more specific problem than "sometimes unstable" -- on this query shape, the system is confidently wrong roughly half the time.

---

## Per-query detail

### `info_ambiguous_archive_boundary` -- confirmed unstable, corrected characterization

All 8 observations to date:

| # | Source | Answer | Confidence |
|---|---|---|---|
| 1 | Informational Email iteration (2026-08-03) | G4 (wrong) | 0.95 |
| 2 | Corpus Stage 0/1 re-run (2026-08-03) | C3 (wrong) | 0.8 |
| 3 | Diagnostic re-trace, same day | A2 (**correct**) | 0.8 |
| 4 | Phase 1, attempt 1 | None (decline) | 0.0 |
| 5 | Phase 1, attempt 2 | None (decline) | 0.0 |
| 6 | Phase 1, attempt 3 | C3 (wrong) | 0.7 |
| 7 | Phase 1, attempt 4 | C3 (wrong) | 0.7 |
| 8 | Phase 1, attempt 5 | C3 (wrong) | 0.7 |

4 distinct outcomes across 8 runs of bit-for-bit identical input (G4, C3, A2, decline), on a system with a confirmed-unchanged model digest throughout. This is not "the reranker occasionally breaks a tie differently" -- `C3` is the modal answer (4/8), at real, non-hedged confidence. **This query shape (near-zero topical content, multiple structurally-similar candidates) should be treated as unreliable, not just "sometimes noisy."**

### `archive_ambiguous_lakeside` -- the finding that overturns a prior conclusion

The original Archive/No-Action report characterized this case's single observed decline as *"the desired behavior this case exists to check for"* -- i.e., treated as a good example of the system correctly recognizing ambiguity and refusing to guess.

With 5 new repeats: **4/5 confidently picked A4 (confidence 0.8, correct), only 1/5 declined.** Combined with the original observation, declining is the *minority* behavior (2/6, 33%), not the modal one. The system does not, in fact, reliably treat this input as too ambiguous to decide -- it usually decides, and usually decides correctly, but not always. The original report's framing was accurate as a description of the one run it had; it was not representative of the query's actual behavior, which N=1 could never have shown.

**Correction applied**: see the append-note added to `eval_reports/2026-08-03_archive_no_action.md`. `BENCHMARK_COVERAGE_REVIEW.md` and `EVAL_HISTORY.md` still carry the original framing in places and haven't been swept for this -- flagging here rather than silently rewriting every downstream mention, consistent with this project's append-only documentation discipline.

### `archive_c4_claims_selfresolved` -- stabilization now has real evidence behind it

The Stage 0/1 report said the case "now passes -- consistent with a fix, not proof of one," explicitly noting 2 observations against 1 failure wasn't enough to conclude anything. With 5 more (all pass, confidence 0.8-0.85, all correctly identifying C4): **7 of 8 total observations pass.** This is still not proof the original failure mode is impossible -- one in eight is a real, nonzero rate -- but it's now a real quantified rate instead of an educated guess, and it does support "meaningfully improved by the Stage 1 enrichment" more strongly than before.

### `thankyou_ambiguous_lowcontent` -- the one case that turned out to be genuinely stable

Every one of 6 total observations (1 original + 5 new) declined with confidence exactly 0.0. This case was never actually confirmed flaky -- it only had one observation before this. It's now the cleanest result in this whole exercise: **fully reproducible behavior**, even though that behavior is a strict-check failure by the case's own ground truth. Worth remembering as a caveat on the taxonomy split done alongside this work: `ambiguity_type: multi_acceptable` describes the *ground truth's* shape (more than one defensible answer), not a claim about run-to-run stability -- this case proves those are independent properties.

### Stratified clear-case sample -- no hidden instability found

`pm1_paraphrase`, `thankyou_c2_closed`, `info_c7_claims_closed`, `broken_headers_html_blockquote`, `crosscust_e1_pm5_eligibility` -- spanning the original frozen set, thank-you, informational, broken-headers, and cross-customer categories. All 15 runs (3 per query) landed on the identical ticket, and in 4 of 5 cases the identical confidence value to three decimal places. **No evidence that instability exists anywhere outside the already-known ambiguous-hard cluster**, at least for this sample. This doesn't prove the other ~39 untested clear cases are equally solid -- see limitations below -- but it's a real, if partial, answer to "is this hiding elsewhere."

---

## What this does and doesn't establish

- **Does establish**: real, quantified pass rates (not single-observation guesses) for the 4 targeted cases, using combined historical + new data where available. Does establish that instability so far is concentrated in the `multi_acceptable` hard-case cluster and has not been found in clear cases, in this sample.
- **Does not establish**: a rigorous confidence interval. N=5 (or N=3, or N=8 combining historical runs of different provenance) is enough to move from "we don't know" to "here's a real rate," but not enough for a tight statistical bound -- a 7/8 pass rate has a genuinely wide plausible range at this sample size. Treat these as real, actionable point estimates, not precise probabilities.
- **Does not establish** that the 39 untested clear cases are stable -- only that a 5-case stratified sample showed no instability. A future pass could sample differently or more broadly.
- **Does not diagnose *why*** the reranker itself varies run-to-run on identical input (a CPU floating-point non-associativity effect, thread-scheduling-dependent execution order, and library-level nondeterminism in `sentence-transformers` are all plausible, none confirmed) -- that remains an open mechanism question, not resolved by this exercise.

## Recommendations

1. Treat `info_ambiguous_archive_boundary`'s query shape (near-zero content, multiple similar candidates) as unreliable, not merely noisy -- roughly 50% confidently-wrong is a materially different risk than "sometimes hedges."
2. Correct the standing characterization of `archive_ambiguous_lakeside` wherever it's cited as an example of "correct honest decline" -- it usually isn't declining.
3. `archive_c4_claims_selfresolved`'s stabilization claim can now be stated with an actual number (7/8) instead of "consistent with, not proof of."
4. This kind of repeat-trial check is now a standing tool (`--repeat`/`--keys` on `scripts/run_eval.py`) -- worth re-running on any case a future iteration flags as a single-observation failure, before writing a characterization based on N=1 again.
