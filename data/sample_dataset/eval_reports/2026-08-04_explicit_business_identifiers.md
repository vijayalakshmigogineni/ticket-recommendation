# Evaluation Iteration Report — Explicit Business Identifiers

**Date**: 2026-08-04
**Category added**: Explicit Business Identifiers (fresh-incoming-email decision coverage — the "easy ceiling" every prior iteration deliberately avoided testing)
**Cases added**: 6 (`pm1_explicit_claim`, `a3_explicit_claim`, `p5_explicit_claim`, `r1_explicit_aging_bucket`, `pm5_explicit_patient_context`, `g1_explicit_charge_detail`)
**Benchmark size**: 56 → 62 queries (54 clear, 8 hard)
**Full run command**: `python scripts/run_eval.py --output data/sample_dataset/eval_results_2026-08-04.json`
**Raw per-query results**: `data/sample_dataset/eval_results_2026-08-04.json`
**Wall-clock**: 64.0 min across 62 queries

---

## 1. Evaluation Report

### Headline (all 62 queries)

| Metric | Result |
|---|---|
| Clear-case accuracy | **54/54 (100%)** |
| Recall@20 (candidate pool) | 58/58 (100%) |
| Recall@3 (reranked top-K) | 58/58 (100%) |
| Hard/ambiguous cases (informational, not in headline) | 5/8 passed |

**No regression**: all 48 previously-passing clear cases still pass, plus all 6 new cases pass. Both `archive_c4_claims_selfresolved` (7/8 empirical pass rate per `NOISE_FLOOR_FINDINGS.md`) and `archive_ambiguous_lakeside`'s clear-case neighbors are unaffected — this run's `archive_ambiguous_lakeside` hard-case outcome is discussed below, not a clear-case regression.

### Category-specific: Explicit Business Identifiers

| Metric | Result |
|---|---|
| Clear-case accuracy (6 cases) | 6/6 (100%) |
| Recall@20 | 6/6 (100%) |
| Recall@3 | 6/6 (100%) |
| Avg. confidence on correct attaches | **0.98** — second-highest of any category, behind only Cross-Customer Similarity (0.99) |

### What this confirms

- **The hypothesis motivating this iteration held exactly as predicted**: an exact, unambiguous identifier (claim number, or an equally unambiguous quantitative/patient-context anchor where no formal ID exists in this corpus) resolves at very high confidence, every time, across all 6 RCM service categories. This is the "easy ceiling" this benchmark had never deliberately tested — every other case was written as paraphrase specifically to test semantic understanding, leaving this simpler capability with zero coverage until now.
- **`pm1_explicit_claim` vs. `pm1_paraphrase` — the direct contrast pair this iteration was designed to produce**: identical ground truth (ticket PM1), one case paraphrased with zero identifiers (the very first eval case in this benchmark's history), one case citing `claim #93021` directly. Both pass, but the identifier-anchored version is a useful reference point for future comparison if either the embedding model or the keyword-search configuration ever changes — a regression that hit keyword matching specifically, but not semantic matching, would show up as this pair diverging where they don't today.
- **The two AR/Eligibility cases without a formal ID (`r1_explicit_aging_bucket`, `pm5_explicit_patient_context`) performed identically well** to the four cases with an actual claim number. This suggests the "explicit identifier" capability generalizes to any sufficiently unambiguous exact detail, not narrowly to numeric claim/auth codes specifically — worth knowing if a future iteration wants to test this capability on services where no formal ID exists.

---

## 2. Failure Analysis

**No new failures, and no new root-cause work needed.** All 3 hard-case failures this run (`thankyou_ambiguous_lowcontent`, `info_ambiguous_archive_boundary`, `archive_ambiguous_lakeside`) are already fully characterized in `NOISE_FLOOR_FINDINGS.md` (2026-08-04) via repeated-trial measurement, not single-observation guessing:

- `thankyou_ambiguous_lowcontent`: declined again (confidence 0.0) — consistent with its confirmed 0/6 pass rate, 6/6 identical (fully stable, reliable decline behavior, not a concern).
- `info_ambiguous_archive_boundary`: picked `C3` again (confidence 0.8) — consistent with `C3` being the modal (4/8, now effectively 5/9) answer for this query shape; confirmed unreliable, not merely noisy.
- `archive_ambiguous_lakeside`: declined this time (confidence 0.0, 147.9s — the slowest call in this run) — consistent with decline being the confirmed minority-but-real outcome (roughly 1/3 of observations); this run happened to land there.

This is the first iteration where a failure analysis section can point to a dedicated measurement document instead of re-deriving root cause from scratch — a direct, concrete payoff of the Phase 1 noise-floor work: these three outcomes were expected in advance, not investigated after the fact.

**One data-integrity note, unrelated to any failure**: while grounding this iteration's identifiers against the real corpus (`seed_data.py`), found that an existing case, `info_a3_priorauth_selfresolved`, cites "auth #4471-B" for ticket A3 — that number does not appear anywhere in A3's actual seed interaction content (`#4471` belongs to a different ticket, P1, for a different customer). Not fixed here, per this project's append-only documentation discipline — flagged for whoever next touches that case.

---

## 3. Notable observation

Average confidence by category, now spanning 7 categories: Explicit Business Identifiers (0.98) and Cross-Customer Similarity (0.99) are the two highest, both by design — one tests an unambiguous keyword anchor, the other tests a structurally-guaranteed-unambiguous customer-scoped retrieval. Informational Email (0.76, the lowest) and the original uncategorized set (0.81) both rely more heavily on semantic/contextual reasoning. This is a clean, expected ordering — confidence tracks how much unambiguous signal the input actually carries, which is exactly what this iteration set out to test at the high end of that spectrum.
