# Evaluation Iteration Report — Broken Thread Headers

**Date**: 2026-08-03
**Category added**: Broken Thread Headers (fresh-incoming decision coverage of `recommender/preprocessing.py`'s quote/forward-stripping logic)
**Cases added**: 8 (`broken_headers_gt_quote`, `broken_headers_on_wrote`, `broken_headers_original_message`, `broken_headers_forwarded`, `broken_headers_pasted_block`, `broken_headers_html_blockquote`, `broken_headers_early_quote_boundary`, `broken_headers_terse_after_strip`)
**Benchmark size**: 37 → 45 queries (38 clear, 7 hard)
**Full run command**: `python scripts/run_eval.py --output data/sample_dataset/eval_results_2026-08-03c.json`
**Raw per-query results**: `data/sample_dataset/eval_results_2026-08-03c.json`
**Wall-clock**: 42.5 min across 45 queries

---

## 1. Evaluation Report

### Headline (all 45 queries)

| Metric | Result |
|---|---|
| Clear-case accuracy | 38/38 (100%) |
| Recall@20 (candidate pool) | 41/41 (100%) |
| Recall@3 (reranked top-K) | 41/41 (100%) |
| Hard/ambiguous cases (informational, not in headline) | 5/7 passed |

**No regression**: all 31 pre-existing clear cases unchanged. Both pre-existing hard-case failures (`thankyou_ambiguous_lowcontent`, `info_ambiguous_archive_boundary`) are unchanged from their prior reports — not new, already explained.

### Category-specific: Broken Thread Headers

| Metric | Result |
|---|---|
| Clear-case accuracy (7 cases) | 7/7 (100%) |
| Recall@20 | 7/7 (100%) |
| Recall@3 | 7/7 (100%) |
| Avg. confidence on correct attaches | **0.98** — highest of any category so far |
| Hard case (`broken_headers_terse_after_strip`) | Passed at 0.997 confidence — see §2, this result comes with an important caveat |

This is the first iteration where **every single new case passed**, clear and hard alike. Confidence is also markedly higher than every other category (0.98 vs. 0.94 Thank You, 0.88 Informational, 0.81 the original benchmark) — see §2 for why that's a real but partly-explained result, not simply "this capability is more reliable."

### What this confirms

- **The quote/forward-stripping preprocessing logic works end-to-end, across every pattern it's designed to handle**: plain `>` quoting, Gmail/Apple "On...wrote:", Outlook "-----Original Message-----" and "-----Forwarded Message-----" banners, a pasted From/Sent/To/Subject block with no banner, and an HTML `gmail_quote`-class blockquote. Each was verified pre-run against the real `clean_text()` function, then confirmed end-to-end through the full pipeline including retrieval and the LLM decision.
- **The `_MIN_CHARS_BEFORE_QUOTE_CUT` boundary behaves as documented, and doesn't break anything even when it partially fails.** `broken_headers_early_quote_boundary` deliberately left one quoted line un-stripped (verified pre-run: `"Thanks!\n\n> Reviewing all three now..."` survives cleaning), and the pipeline still attached correctly — the boundary's imperfection doesn't cause a wrong match.

---

## 2. Failure Analysis

**No new failures.** All 8 cases passed, including the hard one. In place of a failure to trace, the analytically important finding this iteration produced is a **caveat on how rigorous the hardest case actually was** — worth reporting with the same honesty as an actual failure, per this project's standing rule to report limitations rather than let a clean scorecard imply more than it shows.

### `broken_headers_terse_after_strip` passed at 0.997 — but the "semantic floor" wasn't as low as designed

**What was intended**: after stripping, only `"Sounds good, thanks for looking into it."` (40 characters) should survive as body content — a deliberate test of whether near-zero surviving *body* signal is still enough to resolve correctly among summit_neurology's 4 tickets.

**What the traced explanation actually shows**: the model's own reasoning leaned heavily on the **subject line**, not the surviving body text:
> *"Incoming email directly addresses candidate 1's active ticket (ERA payment mismatch) with matching subject line and context: customer is replying to agent's action on the same issue (claim #59042, CPT 99215 payment discrepancy)."*

The subject I used, `"Re: ERA payment amount doesn't match contracted rate"`, is a near-exact match to P5's actual ticket subject (`"ERA payment amount doesn't match contracted rate"`). Since `PreprocessedEmail.embedding_text` is `subject + "\n\n" + clean_body` (by design — short follow-ups need the subject for signal), the subject line alone did most of the retrieval work here, not the 40 characters of surviving body text. **Checking all 8 cases confirms this pattern, not just this one** — every explanation across the category cites subject-line matching prominently, and confidence for the category (0.98 avg.) is the highest of any tested capability so far.

**Is this a design flaw?** No — it's a realistic scenario, not an artificial one. Real mail clients (Gmail, Outlook, Apple Mail) auto-populate `Re: <original subject>` on reply, almost always unedited. So this iteration correctly validated the **common, realistic case**: headers stripped in transit, but the subject line still carries the original topic. What it did *not* rigorously test is the **harder edge case**: a reply where the subject has also degraded (edited by the sender, mangled by a relay, or a client that generates a generic subject) and only the stripped-to-almost-nothing body remains. That's a genuinely distinct, harder probe — worth flagging as a specific follow-up rather than assuming this iteration already covered it.

**Process lesson, same spirit as the Informational Email iteration's**: when designing a "tests the semantic floor" hard case, check what `embedding_text` the pipeline actually constructs (subject + body, not body alone) before assuming a short body means low overall signal — a strong subject line can fully compensate for a stripped body, which is worth accounting for explicitly next time a similarly-framed hard case is built.

---

## 3. Notable observation

Across three iterations now, the two "genuinely hard" case types have diverged in an interesting way: cases testing **zero-content ambiguity across multiple plausible tickets** (`thankyou_ambiguous_lowcontent`, `info_ambiguous_archive_boundary`) both failed the strict pass/fail check, in informative rather than alarming ways. Cases testing **low surviving content but only one plausible ticket** (`c1_hard_paraphrase`, `broken_headers_terse_after_strip`) have both passed, at high confidence. This suggests the system's real weak point isn't "how little text is there" in isolation — it's specifically **disambiguation among multiple similarly-plausible candidates when the incoming text can't distinguish between them**. That's a more precise characterization of the actual risk area than "low-content queries are risky" would be, and should guide where future hard cases get placed.
