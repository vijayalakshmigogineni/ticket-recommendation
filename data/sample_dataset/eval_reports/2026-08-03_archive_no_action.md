# Evaluation Iteration Report — Archive / No-Action

**Date**: 2026-08-03
**Category added**: Archive / No-Action (fresh-incoming decision coverage — a brand-new "no action needed" email deciding attach-vs-archive from scratch, not a reply inside an already-known thread)
**Cases added**: 8 (`archive_c4_claims_selfresolved`, `archive_e5_eligibility_rescheduled`, `archive_g1_chargeentry_noaction`, `archive_p3_payment_noaction`, `archive_p4_payment_notduplicate`, `archive_r4_ar_noaction`, `archive_a2_priorauth_deprioritize`, `archive_ambiguous_lakeside`)
**Benchmark size**: 45 → 53 queries (45 clear, 8 hard)
**Full run command**: `python scripts/run_eval.py --output data/sample_dataset/eval_results_2026-08-03d.json`
**Raw per-query results**: `data/sample_dataset/eval_results_2026-08-03d.json`
**Wall-clock**: 50.2 min across 53 queries

---

## 1. Evaluation Report

### Headline (all 53 queries)

| Metric | Result |
|---|---|
| Clear-case accuracy | **44/45 (98%)** |
| Recall@20 (candidate pool) | 49/49 (100%) |
| Recall@3 (reranked top-K) | 49/49 (100%) |
| Hard/ambiguous cases (informational, not in headline) | 5/8 passed |

**This is the first clear-case failure in this benchmark's history.** Every prior iteration reported 100% clear-case accuracy; this run reports 98% (44/45) because `archive_c4_claims_selfresolved` failed. This is reported as-observed, not re-run-until-passing — see §2 for why, and for the root cause, which is a known, already-documented limitation showing up in a new way rather than a new defect.

Recall@20 and Recall@3 remain 100% — including for the failed case (confirmed below), meaning this is fully isolated to the decision layer, not retrieval.

### Category-specific: Archive / No-Action

| Metric | Result |
|---|---|
| Clear-case accuracy (7 cases) | 6/7 (86%) |
| Recall@20 | 7/7 (100%) |
| Recall@3 | 7/7 (100%) |
| Avg. confidence on correct attaches | 0.90 |
| Hard case (`archive_ambiguous_lakeside`) | Failed — but as an honest decline under genuine ambiguity, the same good pattern as `thankyou_ambiguous_lowcontent`, not a bad outcome (see §2) |

### What this confirms

- **6 of 7 clear cases correctly attached a cold "no action needed" email**, including temporary-deprioritization phrasing (`archive_a2_priorauth_deprioritize`) that's softer than full closure — the category's core hypothesis (the system doesn't blindly archive) continues to hold.
- **The rigor improvement worked as intended.** `archive_ambiguous_lakeside`'s acceptable set was built by tracing real grouping scores first (A4=0.496, P1=0.447, E3=0.408 — a real gap) rather than guessing from recency, directly applying the lesson from `info_ambiguous_archive_boundary`. The model declined to guess rather than force a pick — an honest, appropriate response to genuine top-layer ambiguity, not a sign the ground truth was still wrong.

---

## 2. Failure Analysis

### `archive_c4_claims_selfresolved` (clear) — genuine LLM non-determinism, traced and reproduced

**This is a real, evidenced finding, not a shrug.** Traced by independently re-running the *exact same* query (same email, same customer, same candidates) through `run_traced_pipeline` outside the eval harness:

1. **Retrieval and reranking are identical and fully explain nothing wrong on their own — but they do mislead slightly.** Grouping `final_score`: C4=0.6281 (highest, correctly), A3=0.6177, E2=0.5201. But the *raw* content-similarity component (`max_score`, before recency weighting) actually favors E2 (0.6403) over C4 (0.6094) — E2 only ranks last in grouping because its recency score is terrible (0.113, a CLOSED ticket closed weeks ago). The cross-encoder reranker, working from text alone with no recency input, reproduces and *amplifies* this: reranked order is **E2 (0.00659) > C4 (0.000993) > A3 (0.000742)** — the correct answer (C4) is only the reranker's *second* choice, not first, in both the failing run and the re-trace (confirmed identical order in both).

2. **Recall@3 is still satisfied** (C4 is in the top-3) — this is a decision-layer question, not a retrieval miss.

3. **On re-run, the LLM correctly overcame the misleading rank order**: `should_attach=True, ticket=C4, confidence=0.85`, reasoning explicitly that the email's "found proof and payer agreed to reprocess" is a direct continuation of C4's "timely filing... we have proof of original submission," and explicitly rejecting E2 ("Candidate 1 is closed and involves coverage termination, not reprocessing") and A3 ("about missing prior authorization, unrelated").

4. **In the original failing run, the same model, same prompt, same candidate order, same temperature (0.0, confirmed in `config/recommender_config.yaml`), declined to attach to anything** — its explanation described the exact same three candidates in the exact same order (confirming candidate ordering was not the variable that changed), but concluded "the underlying issue in the email is distinct from all candidates."

**Root cause, stated plainly**: this is LLM sampling non-determinism at the decision layer, reproduced under identical inputs — the same phenomenon already documented in this project's Known Limitations ("`qwen3:4b` at temperature 0 has shown non-determinism on hard disambiguation cases across identical re-runs"), **but this is the first confirmed instance of it flipping a *clear*-difficulty case's outcome, not just a hard/disambiguation one.** The distinguishing factor here is that retrieval/reranking didn't cleanly favor the correct candidate (it came second, not first) — meaning the decision layer had real interpretive work to do to reach the right answer, and a "thinking" model's internal chain-of-thought sampling isn't perfectly stable across runs even at temperature 0, especially when the ranking evidence it's given isn't unambiguous.

**No fix applied, and none recommended right now.** This isn't a code defect to patch — it's inherent to running a local "thinking" LLM at this scale. The two theoretical levers (disabling thinking mode, or switching decision models) are both already-known, already-logged tradeoffs (thinking mode is deliberately kept on because it may matter for decision quality on hard cases) — re-litigating that tradeoff on the strength of one observed flip isn't warranted. **Reporting this honestly, rather than re-running until it passes, is the correct response** — re-running and only keeping the passing result would hide a real, now-confirmed-broader limitation.

**Process/documentation update**: the Known Limitations note about `qwen3:4b` non-determinism should be broadened — see README update below — since it's no longer accurate to scope it to "hard disambiguation cases" only.

### `archive_ambiguous_lakeside` (hard) — expected, good behavior, not a concern

Declined to attach (confidence 0.0) to either A4 or P1, reasoning that the message is too generic to tell which RESOLVED ticket it refers to. This is the same honest-decline pattern as `thankyou_ambiguous_lowcontent`, and — unlike `info_ambiguous_archive_boundary` — this time the ground truth itself was properly verified (real grouping-score gaps, not recency guesswork) before the run, so there's no question of whether the "right" answer was even well-defined. The model choosing not to force a guess under genuine ambiguity is the desired behavior this case exists to check for.

**Update (2026-08-04, `NOISE_FLOOR_FINDINGS.md`)**: this characterization was based on a single observation and does not hold up under repeated trials. 5 repeat runs of this exact query found 4/5 confidently picked A4 (confidence 0.8, correct) and only 1/5 declined — declining is the *minority* behavior (2/6 combined), not the modal one. The system usually does decide, and usually decides correctly, but the "desired behavior this case exists to check for" framing above overstates how reliably it declines. See `NOISE_FLOOR_FINDINGS.md` for the full per-observation breakdown. Left as originally written above per this project's append-only documentation discipline — this note corrects the record rather than rewriting it.

---

## 3. Notable observation

This iteration is a useful complement to the last one's finding. Broken Thread Headers showed the system can be *overconfident in a good way* (very high confidence, well-justified) when signal is genuinely strong. This iteration shows the reverse edge: when retrieval/reranking hand the decision layer a *slightly* misleading rank order (correct answer ranked 2nd, not 1st, by a real but modest margin) on an otherwise unambiguous case, outcome stability isn't guaranteed run-to-run. That's a materially different risk than "low-content queries are hard" (the throughline from the last three hard-case findings) — it's specifically about *decision-layer stability when evidence is good but not dominant*, worth keeping distinct from the ambiguity-driven failures when thinking about where this system's real reliability edges are.
