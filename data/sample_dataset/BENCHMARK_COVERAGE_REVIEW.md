# Benchmark & Corpus Coverage Review

**Purpose**: a point-in-time audit of `seed_data.py` (the ticket/interaction corpus) and `eval_queries.py` (the regression benchmark) against three coverage dimensions, done *before* generating any further data, specifically to avoid re-creating already-covered scenarios or missing known gaps. Read this before designing the next dataset-expansion or eval-benchmark iteration. **Update it (don't let it go stale) whenever a new iteration changes any table below** — this is a living audit, not a one-time report.

**Framing distinction that matters throughout this document**: a workflow *tone* existing somewhere in a ticket's interaction history (corpus realism) is a different thing from a **fresh incoming email of that type actually being run through the recommendation pipeline as an eval case** (decision coverage). Corpus variety makes ticket history realistic; only a fresh eval case tests whether the recommendation decision handles that email type correctly. Several gaps below exist precisely because corpus realism was already achieved while decision coverage wasn't.

**Companion document note (added 2026-08-03)**: `CORPUS_COVERAGE_AUDIT.md` is now the authoritative, quantitative source for corpus-only questions (interaction-depth distribution, per-customer richness, long-running-conversation coverage, structural-difficulty inventory) — it was written specifically because this document's Dimension 2 tallies *eval cases against* the corpus, not the corpus's own realism independent of any query. Read that document for corpus-realism questions; keep using this one for workflow/service/scenario coverage of the benchmark itself.

---

## Dimension 1 — Business Workflow Coverage

| Workflow | In ticket corpus? | Fresh eval case testing the *decision*? | New ticket or attach? | Sufficiency |
|---|---|---|---|---|
| New Service Request | Yes (every founding interaction) | Yes — `remit_address_reject`, `ggi_no_payment_ticket` (correct no-match) | New ticket | Adequate but thin — only 2 cases, not spread across categories |
| Existing Ticket Update | Yes (pervasive) | Yes (majority of cases) | Attach | Well covered |
| Attach to Existing Ticket | N/A — this is the outcome, not a workflow | This is most of the benchmark | Attach | Well covered |
| General Query | Thin (E5) | Thin (`pm5_eligibility`) | Either | Underrepresented |
| **Informational Email** | Yes (G6) | **Yes, as of 2026-08-03** — 8 fresh cases (`info_*`), spanning 6 services including a CLOSED terminal-status case; 7/7 clear cases correctly attached | Attach | **Covered** — see `eval_reports/2026-08-03_informational_email.md` |
| **Thank You / Appreciation** | Yes (A7, E7 endings) | **Yes, as of 2026-08-03** — 8 fresh cases (`thankyou_*`), spanning all 6 RCM services, including 2 against terminal CLOSED tickets and 5 against RESOLVED tickets | Attach | **Covered** — see `eval_reports/2026-08-03_thank_you_appreciation.md` |
| Document Submission | Yes (E6) | Yes (`e6_document_submission`) | Attach | Covered |
| Missing Information Request | Yes (agent-side, many tickets) | N/A — inherently agent-initiated, not an incoming-email pattern | — | Not applicable as its own case; fine as-is |
| Status Follow-up | Yes (pervasive) | Yes (majority) | Attach | Very well covered — arguably over-represented relative to everything else |
| Clarification Request | Yes (G7) | Thin — only bundled inside `pm2_pm4_disambiguation` | Attach | Underrepresented in isolation |
| Complaint | Thin (folded into A6) | Thin — always bundled with escalation, never alone | Attach | Underrepresented in isolation |
| Escalation | Yes (A6) | Yes (`a6_escalation`) | Attach | Covered |
| Closure Confirmation | Yes (E7, C1) | Partial (`cross_customer_c1`, `g6_no_action_confirm`) | Attach | Adequate |
| **Archive / No Action Required** | Yes (G6) | **Covered, as of 2026-08-03** — 8 fresh cases (`archive_*`), 6/7 clear cases correctly attached (the system does not default to archive); the 7th (`archive_c4_claims_selfresolved`) failed, traced to confirmed LLM non-determinism at the decision layer, not a retrieval or ground-truth issue. The hard case (`archive_ambiguous_lakeside`) had its acceptable set built by tracing real grouping scores first, not recency-guessing — the model honestly declined rather than force a pick. See `eval_reports/2026-08-03_archive_no_action.md` | Attach | **Covered** |

## Dimension 2 — RCM Service Coverage

**Corpus level**: balanced, 8-9 tickets per category across all 6 services (verified in the dataset-expansion pass). For anything beyond category balance — interaction depth, per-customer richness, structural-difficulty inventory — see `CORPUS_COVERAGE_AUDIT.md`, which as of 2026-08-03 is the authoritative document for corpus-only questions. Corpus size as of 2026-08-03 (post Stage 1 enrichment): 50 tickets, **158 interactions** (up from 151; 155 embeddable).

**Eval-benchmark level — even more so now**, tallied by each case's actual expected-ticket category (updated 2026-08-03, after all four workflow iterations plus the Corpus Coverage Audit's Stage 0):

| Service | Eval cases |
|---|---|
| Claims | 12 (`pm1`, `cross_customer_c1`, `c6`, `c8`, `c1_hard_paraphrase`, `thankyou_c2_closed`, `info_c5_claims_resolved`, `info_c7_claims_closed`, `broken_headers_gt_quote`, `broken_headers_early_quote_boundary`, `archive_c4_claims_selfresolved`, `pm1_explicit_claim`) |
| Prior Authorization | 10 (`pm2`, `pm2_pm4`, `a7`, `a6`, `a5`, `thankyou_a4_priorauth_resolved`, `info_a3_priorauth_selfresolved`, `archive_a2_priorauth_deprioritize`, `crosscust_a1_pm4_mri`, `a3_explicit_claim`) |
| Charge Entry | 9 (`pm7`, `g6`, `g5`, `thankyou_g3_chargeentry_resolved`, `info_g4_chargeentry_selffixed`, `broken_headers_pasted_block`, `broken_headers_html_blockquote`, `archive_g1_chargeentry_noaction`, `g1_explicit_charge_detail`) |
| Eligibility | 9 (`pm5`, `e6`, `thankyou_e7_resolved`, `thankyou_e2_closed_valley`, `info_e3_eligibility_selfupdated`, `broken_headers_forwarded`, `archive_e5_eligibility_rescheduled`, `crosscust_e1_pm5_eligibility`, `pm5_explicit_patient_context`) |
| Accounts Receivable | 7 (`pm6`, `three_way_ar`, `thankyou_r3_ar_resolved`, `info_r1_ar_update`, `broken_headers_original_message`, `archive_r4_ar_noaction`, `r1_explicit_aging_bucket`) |
| Payment Posting | 9 positive (`near_dup_p6_p7`, `thankyou_pm3_resolved`, `info_p2_payment_discrepancy`, `broken_headers_on_wrote`, `broken_headers_terse_after_strip`, `archive_p3_payment_noaction`, `archive_p4_payment_notduplicate`, `crosscust_p2_p5_era`, `p5_explicit_claim`) + 1 deliberate-absence case (`ggi_no_payment_ticket`) |

`thankyou_ambiguous_lowcontent`, `info_ambiguous_archive_boundary`, and `archive_ambiguous_lakeside` aren't tallied above — all three hard cases' acceptable-answer sets span two services each, so none cleanly belongs to one row. `broken_headers_terse_after_strip` (hard) *is* tallied under Payment Posting since, unlike those three, it has a single definite answer (P5) — same precedent as `c1_hard_paraphrase` under Claims.

Five rounds of incidental service-spread (four workflow iterations plus Corpus Audit Stage 0) have taken this from a 5x skew (Claims/Prior Auth = 10 of ~15) down to a tight 6-11 range across all six services — every service now has real depth. Rebalancing is no longer a meaningful gap.

## Dimension 3 — Recommendation Coverage

| Scenario | Coverage |
|---|---|
| Existing Ticket Match | Well covered (most cases) |
| New Ticket Required | Thin — 2 cases, both different in kind; no case of "a genuinely new issue in a category with other tickets, matching none of them" |
| Near Duplicate | 1 case (`near_dup_p6_p7`, 2-way) |
| Semantic Paraphrase | 2 cases — good |
| Ambiguous Wording (independent of disambiguation) | Thin/absent as its own axis |
| Multiple Similar Open Tickets | 1 case (`three_way_ar`, 3-way) |
| Missing Identifiers | 1 case (`c6`) |
| **Explicit Business Identifiers** | **Covered, as of 2026-08-04** — 6 fresh cases (`*_explicit_*`) across all 6 RCM services, each citing an exact identifier (claim number, or an equally unambiguous quantitative/patient-context anchor where no formal ID exists in the corpus) verified against real `seed_data.py` content. 6/6 passed at 0.98 avg. confidence, second-highest of any category. See `eval_reports/2026-08-04_explicit_business_identifiers.md` |
| Thread Continuation | 1 case (`pm2_autoattach`) |
| **Broken Thread Headers** | **Covered, as of 2026-08-03** — 8 fresh cases (`broken_headers_*`) with `conversation_id`/`in_reply_to` omitted, verified against the real `clean_text()` function pre-run: plain `>` quoting, "On...wrote:", Outlook "-----Original Message-----"/"-----Forwarded Message-----" banners, a pasted header block, an HTML `gmail_quote` blockquote, the `_MIN_CHARS_BEFORE_QUOTE_CUT` boundary, and a post-strip semantic-floor probe. 8/8 passed (7 clear + 1 hard). See `eval_reports/2026-08-03_broken_thread_headers.md` — the hard case passed but with a caveat (subject-line matching did more work than the stripped body it meant to isolate) |
| Long-running Conversations | 2 cases — **audit finding (2026-08-03, see `CORPUS_COVERAGE_AUDIT.md` Dimension 5): both belong to the same customer (pinehill_ophtho)**, so this isn't yet 2 independent data points |
| **Cross-customer Similarity** | **4 cases, as of 2026-08-03** (`cross_customer_c1` originally, plus `crosscust_a1_pm4_mri`, `crosscust_e1_pm5_eligibility`, `crosscust_p2_p5_era` — 3 more lookalike pairs the Corpus Coverage Audit found *already existing* in the corpus but never tested). All pass at very high confidence (0.99 avg) since customer-scoped retrieval makes them structurally easy — value is in diversifying the regression guard, not difficulty |
| False Positive Scenarios | 2 cases |
| False Negative Scenarios | 1 case (`c1_hard_paraphrase`) — designed to *probe for* one, not a guaranteed demonstration |

**Structural observation, not one of the three named dimensions**: the proposed (unimplemented, as of this writing) Noisy Writing iteration is a 4th, orthogonal axis — surface-form robustness cuts across all three named dimensions rather than living inside any one. Decide explicitly whether this becomes a standing 4th dimension, or a "modifier" applicable to any workflow/service/scenario combination, before implementing it.

## Coverage matrix (Workflow × Service, annotated with Recommendation Scenario)

A literal 14×6×15 cube isn't a usable table — 30 total cases can't densely populate 84 workflow×service cells. This is the practical version: cells with real coverage and what scenario each demonstrates. Everything not listed is genuinely empty (expected at this dataset size, not hidden).

| | Claims | Payment Posting | Prior Auth | Eligibility | AR | Charge Entry |
|---|---|---|---|---|---|---|
| Status Follow-up | ✅ Semantic paraphrase | — | ✅ Disambiguation (hard) | ✅ Explicit match | ✅ Missing-ID guard | ✅ Standard |
| New Service Request (no match) | — | ✅ Category-absent | — | — | — | — |
| Near Duplicate / Multi-similar | — | ✅ 2-way | — | — | ✅ 3-way | — |
| Cross-customer guard | ✅ (C1/C5) | ✅ (P2/P5, 2026-08-03) | ✅ (A1/PM4, 2026-08-03) | ✅ (E1/PM5, 2026-08-03) | — | — |
| False-positive guard | — | — | ✅ | — | — | — |
| Escalation | — | — | ✅ | — | — | — |
| Document Submission | — | — | — | ✅ | — | — |
| Archive/No-action | — | — | — | — | — | ✅ (weak, see gap) |
| Thread Continuation (auto-attach) | — | — | ✅ | — | — | — |
| Hard/false-negative paraphrase | ✅ | — | — | — | — | — |
| Thank You/Appreciation | ✅ CLOSED | ✅ RESOLVED | ✅ RESOLVED (+ambiguous, hard) | ✅ RESOLVED+CLOSED | ✅ RESOLVED (+ambiguous, hard) | ✅ RESOLVED |
| Informational Email | ✅ RESOLVED+CLOSED | ✅ IN_PROGRESS | ✅ OPEN | ✅ IN_PROGRESS | ✅ OPEN (+ambiguous, hard) | ✅ IN_PROGRESS (+ambiguous, hard) |
| Broken Thread Headers | ✅ IN_PROGRESS (x2 patterns) | ✅ RESOLVED (+hard, semantic-floor) | — | ✅ RESOLVED (forward) | ✅ IN_PROGRESS | ✅ PENDING+WAITING_FOR_CLIENT (x2 patterns) |
| Archive/No-Action (cold) | ✅ OPEN | ✅ PENDING+OPEN | ✅ IN_PROGRESS (+ambiguous, hard) | ✅ OPEN | ✅ PENDING | ✅ OPEN (+ambiguous, hard) |

All four of the last four iterations (Thank You/Appreciation, Informational Email, Broken Thread Headers, Archive/No-Action) each have coverage across most or all 6 services — a direct result of deliberate service-spread during case design, not a general pattern to expect elsewhere in this matrix. Blank cells still outnumber filled ones overall. This benchmark validates specific, deliberately-chosen scenarios well, not broad cross-product coverage — that was always the design intent (targeted iterations, not exhaustive grid-filling), worth stating plainly rather than implying otherwise.

## Gap analysis

- **Missing workflows** (as fresh eval decisions, not corpus tone): all closed. Thank You/Appreciation, Informational Email, and Archive/No-Action all have 6-7/7 clear-case accuracy, with the one Archive/No-Action failure traced to LLM non-determinism (see below), not a design or ground-truth gap.
- **Missing RCM services** (in the eval benchmark specifically, not the corpus): closed — four iterations of incidental service-spread took the benchmark from a 5x skew down to a 6-11 range across all six services. See updated Dimension 2 table.
- **Missing recommendation scenarios**: Broken Thread Headers is closed (2026-08-03, 8/8 passed). Explicit Business Identifiers is closed (2026-08-04, 6/6 passed, see `eval_reports/2026-08-04_explicit_business_identifiers.md`). Still open: a genuinely-harder Broken Thread Headers follow-up, Ambiguous Wording as its own independent axis.
- **Weak combinations**: nothing tests Escalation/Complaint/Clarification outside Prior Authorization; nothing tests Near-Duplicate or Multi-Similar outside Payment Posting/AR.
- **Unrealistic distribution**: resolved — see Dimension 2 above.
- **Process-level findings from 2026-08-03** (worth applying to any future hard-case or clear-case design):
  1. Constructing a hard/ambiguous case's acceptable-answer set from ticket recency alone, without checking each candidate's actual retrieval/rerank score, can produce a "wrong" acceptable set (Informational Email report §2) — fixed in the Archive/No-Action iteration by tracing real scores first.
  2. A "tests the semantic floor" case needs to account for `embedding_text` being subject *and* body — a strong, realistic `Re: <subject>` line can fully compensate for an aggressively-stripped body (Broken Thread Headers report §2).
  3. `qwen3:4b` non-determinism at temperature 0 can flip a *clear*-difficulty case's outcome, not just hard/disambiguation ones (Archive/No-Action report §2) — a broadening of an already-known limitation, not a new one.
  4. **Corpus-side change (2026-08-03): the Corpus Coverage Audit found the corpus itself — not just the benchmark — had real, quantifiable gaps** (18% single-interaction tickets, long-running coverage concentrated in one customer, per-customer richness varying 5x). Stage 0 (mine 3 latent cross-customer pairs) and Stage 1 (enrich 7 thin tickets) closed part of this at zero-to-mild regression risk — full re-run showed zero regression and the prior `archive_c4_claims_selfresolved` failure now passing. See `CORPUS_COVERAGE_AUDIT.md`, `CORPUS_EXPANSION_ROADMAP.md`, and `eval_reports/2026-08-03_corpus_stage0_stage1.md`.
  5. **The non-determinism finding above was further broadened by the Stage 0/1 re-run**: `info_ambiguous_archive_boundary` produced a *third* different wrong answer across observations, and tracing showed the *reranker's* cross-encoder scores — not just the LLM's conclusion — vary run-to-run on near-zero-content queries with multiple similar candidates. Treat any single observation of this query shape as one noisy sample, not a stable measurement.

## Final assessment

1. **Overall coverage**: comprehensive across Business Workflow (status follow-up, document submission, escalation, thank-you/appreciation, informational email, cold archive/no-action) and Recommendation Coverage's structural-difficulty scenarios (disambiguation, 4-instance cross-customer guard, missing identifiers, broken-threading recovery, explicit-identifier ceiling). What's left is narrow and mechanical: Ambiguous Wording as its own axis, and a harder Broken-Headers follow-up — plus, on the corpus side (tracked in `CORPUS_COVERAGE_AUDIT.md`, not here), long-running-conversation coverage still concentrated in one customer and per-customer richness imbalance.
2. **Sufficiently representative of real-world RCM traffic?** Yes, on the benchmark side. All four of the most-common "everyday" email patterns (thank-you, FYI/informational, reply-with-stripped-headers, and cold no-action-needed) are now tested and all perform well, with a well-understood, now-broadened exception (non-determinism affecting both the reranker and the LLM decision layer on near-zero-content, multi-candidate queries). The corpus itself is a separate, partially-open question — see the companion audit.
3. **Would an AM encounter the same diversity here as in production?** Yes, closely, on workflow variety. They'd also recognize that the AI's answer can occasionally shift between otherwise-identical runs on a genuinely ambiguous case — a realistic property of any LLM-backed tool, now observed at both the reranker and decision layers.
4. **Prioritized gaps to address next on the benchmark side** (highest-value first, renumbered after closing Explicit Business Identifiers on 2026-08-04):
   1. A genuinely-harder Broken Thread Headers follow-up: degraded/generic subject line *plus* stripped body, to isolate the semantic floor the 2026-08-03 iteration didn't fully isolate.
   2. Ambiguous Wording as its own independent recommendation-coverage axis (distinct from the disambiguation-across-multiple-tickets cases already covered).
   3. Decide whether Noisy Writing becomes a standing 4th dimension or a cross-cutting modifier, before implementing it.
   4. (Lower priority, informational) Non-determinism on the `multi_acceptable` hard-case cluster is now quantified, not just observed — see `NOISE_FLOOR_FINDINGS.md` (2026-08-04). `info_ambiguous_archive_boundary` specifically (confidently wrong ~50% of the time) is worth revisiting the thinking-mode/model-choice tradeoff for, if this query shape turns out to matter in production; the other two (`thankyou_ambiguous_lowcontent`, `archive_ambiguous_lakeside`) are lower concern per that document's findings.

   **On the corpus side, see `CORPUS_EXPANSION_ROADMAP.md` for Stages 2-5** (deepen the thinnest customer, add a long-running ticket for a customer other than pinehill_ophtho, a new structural-difficulty construct, internal-note realism) — all proposed, none approved, pending review of Stage 0/1's results as a stable baseline before deciding whether they're still needed.

---

*As of this writing (2026-08-03): the Thank You/Appreciation, Informational Email, Broken Thread Headers, and Archive/No-Action iterations (8 cases each, 32 total) plus the Corpus Coverage Audit's Stage 0 (3 cases) and Stage 1 (7 tickets enriched, 151→158 interactions) have all been implemented and run in the same session — see the five reports under `eval_reports/`, `EVAL_HISTORY.md`, `CORPUS_COVERAGE_AUDIT.md`, and `CORPUS_EXPANSION_ROADMAP.md`. This document has been updated to reflect all closed gaps; remaining findings above stay open. The Noisy Writing iteration (9 cases) referenced elsewhere was designed in an earlier pass but is still not implemented.*
