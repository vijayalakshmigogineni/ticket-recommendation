# Evaluation Iteration Report — Informational Email

**Date**: 2026-08-03
**Category added**: Informational Email (fresh-incoming-email decision coverage)
**Cases added**: 8 (`info_c5_claims_resolved`, `info_p2_payment_discrepancy`, `info_a3_priorauth_selfresolved`, `info_r1_ar_update`, `info_g4_chargeentry_selffixed`, `info_e3_eligibility_selfupdated`, `info_c7_claims_closed`, `info_ambiguous_archive_boundary`)
**Benchmark size**: 29 → 37 queries (31 clear, 6 hard)
**Full run command**: `python scripts/run_eval.py --output data/sample_dataset/eval_results_2026-08-03b.json`
**Raw per-query results**: `data/sample_dataset/eval_results_2026-08-03b.json`
**Wall-clock**: 39.0 min across 37 queries

---

## 1. Evaluation Report

### Headline (all 37 queries)

| Metric | Result |
|---|---|
| Clear-case accuracy | 31/31 (100%) |
| Recall@20 (candidate pool) | 33/33 (100%) |
| Recall@3 (reranked top-K) | 33/33 (100%) |
| Hard/ambiguous cases (informational, not in headline) | 4/6 passed |

**No regression**: all 24 pre-existing clear cases and the 4 previously-passing hard cases are unchanged. `thankyou_ambiguous_lowcontent` still fails exactly as documented in the prior report (same behavior, same root cause) — not a new issue.

### Category-specific: Informational Email

| Metric | Result |
|---|---|
| Clear-case accuracy (7 cases) | 7/7 (100%) |
| Recall@20 | 7/7 (100%) |
| Recall@3 | 7/7 (100%) |
| Avg. confidence on correct attaches | 0.88 |
| Terminal-status subgroup (CLOSED: `info_c7_claims_closed`) | 1/1 correct |
| Non-terminal subgroup (RESOLVED/OPEN/IN_PROGRESS: remaining 6) | 6/6 correct |
| Hard case (`info_ambiguous_archive_boundary`) | Failed the strict pass/fail check — see Failure Analysis §2, verdict is nuanced, not a clean defect |

For comparison: `thank_you_appreciation` scored 7/7 at 0.94 avg. confidence, `uncategorized` (the original benchmark) scored 17/17 at 0.81. Informational Email's 0.88 sits between the two — consistent with the rest of the benchmark, no degradation.

### What this confirms

- **The predicted failure mode again did not materialize for clear cases.** All 7 informational/FYI-style emails — including ones with no explicit request at all, and one against a CLOSED terminal ticket — correctly attached rather than being treated as "nothing to do here."
- **The category spans a real range of informational sub-types** (self-resolved-by-customer, mid-investigation update, new resolving detail, correction to prior context, terminal-status closure) and all held up equally, not just the easiest variant.

---

## 2. Failure Analysis

### `info_ambiguous_archive_boundary` (hard) — nuanced, not a clean defect

**Verdict up front, and it differs from the previous iteration's ambiguous case**: this is not the same "correctly declined to guess" story as `thankyou_ambiguous_lowcontent`. Here the model made a **specific, confident (0.8-0.95 across two runs) choice** — and whether that choice is "wrong" depends on a ground-truth design question this case exposed, not a clear pipeline defect.

**Email**: `"Just a quick FYI - we think everything's handled on our end now, no action needed!"` from `ar@metrocardiologypartners.com` — zero topical anchor, 4 candidates (C3, A2, G4, E1). Ground truth as designed: acceptable = {E1, A2}, chosen by ticket recency alone (E1 age_days=2, A2 age_days=5).

**Traced with a direct re-run of `run_traced_pipeline`** (confidence came back 0.8 on the re-run vs. 0.95 in the original eval pass — expected non-determinism on qwen3:4b for hard cases, already a documented limitation, not new):

1. **Retrieval/grouping**: `final_score` for the 4 candidates — A2: 0.5161, C3: 0.5153, G4: 0.4889, **E1: 0.4757 (lowest of the four)**. E1 has the highest recency component (0.742) but the weakest actual content-match signal (`max_score`/`topk_avg` both 0.4091, well below the others) — meaning E1's own ticket content (a new-patient eligibility check request) has genuinely little semantic overlap with "everything's handled, no action needed." **This is the first concrete finding**: the ground truth's recency-only heuristic picked a ticket that retrieval itself considers the weakest-matching of the four, which is a gap in how the hard case was constructed, not something the pipeline did wrong.

2. **Reranking**: top-3 kept A2, C3, G4 — E1 was cut. Scores were again near-degenerate (4.07e-05, 4.06e-05, 3.79e-05, differing only in the 5th significant digit), the same reranker-signal-collapse-on-low-content-queries pattern documented in the Thank You report. `recall3=true` was satisfied via A2 surviving, not E1.

3. **LLM decision — the actually interesting part.** The model didn't treat this as unresolvable ambiguity (unlike the Thank You case). It reasoned about each candidate's own conversational state:
   > *"The incoming email states the issue is resolved with no action needed, which aligns with Candidate 3 [G4] where the agent has already voided the duplicate charge... Candidate 1 and 2 are still in progress (agent working on new auth or resubmissions), so the customer wouldn't claim resolution."*

   This is genuine content-grounded reasoning, not a guess — G4's last recorded interaction is literally an agent confirming a fix ("voiding the duplicate now"), which does read as compatible with a closure-style FYI. The model correctly ruled out A2 and C3 because their tickets are demonstrably still open work, not closed.

4. **The nuance it missed**: the email says "handled on **our** end" (customer-side action), but G4's actual resolution was agent-side (the agent voided the duplicate, not the customer). None of the four candidates has a customer-self-resolution moment on record for the LLM to point to — it approximated "resolved-sounding ticket" as good enough, without distinguishing *who* performed the resolution the email claims. E1, by contrast, is the one candidate whose *type* of request (a customer asking staff to double-check something before tomorrow) a customer could later self-resolve and report back on informationally — which is the closest fit to this category's actual intent — but E1's weak retrieval score meant it was cut before the LLM ever got to consider it as a live option.

**Root cause, stated plainly**: this is jointly a **ground-truth construction gap** (the acceptable set was built from ticket recency alone, without checking that each acceptable answer actually clears the retrieval bar) and a **decision-layer nuance gap** (the model matches "resolved-sounding" tone to a candidate's last known status, without checking whether the party who resolved it — agent vs. customer — matches what the email actually claims). Neither is a bug to patch: forcing the reranker to fix a content-free query's degenerate scores would fabricate signal that isn't there, and adding a customer-vs-agent-resolution check to the decision prompt for one hard case would be overfitting to a single example rather than a validated general improvement.

**Process lesson for future hard-case design** (the concrete, actionable takeaway): when building a deliberately-ambiguous case's acceptable-answer set, check each candidate's actual grouping/rerank score, not just ticket recency — a recency-only heuristic can pick an answer that's already the weakest retrieval match of the field, as happened with E1 here. This doesn't invalidate the case (the underlying question — does a zero-content "no action needed" email get handled sensibly? — is still being tested, and answered: the system makes a specific, explainable, non-arbitrary choice rather than hallucinating or randomly guessing) but it means the strict PASS/FAIL framing overstates how clear-cut the "right" answer was.

---

## 3. Notable observation

Comparing the two hard ambiguous cases across both iterations: the Thank You case (zero content, no resolvable context in any candidate) produced honest non-attachment at confidence 0.0. This Informational Email case (zero content, but each candidate has *some* status the model can reason about) produced a confident, specific attachment at 0.8-0.95. This suggests the model's willingness to guess under ambiguity is driven by whether it can construct *any* plausible-sounding narrative from the candidates' context — not by how much genuine signal is actually in the incoming email itself. That's worth carrying into any future work on confidence thresholds or automation: confidence here tracked "could I build a story" more than "is the input actually informative enough to decide," which is a softer guarantee than the number alone suggests.
