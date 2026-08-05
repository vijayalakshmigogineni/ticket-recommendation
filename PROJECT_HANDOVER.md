# Project Handover — RCM Ticket Recommender

**Written**: 2026-08-04, for handover to a new Claude session with no memory of prior conversations.
**Read this file first, in full, before touching any code.** It supersedes nothing — `README.md` at the repo root is still the maintained day-to-day handoff doc — but this file exists specifically to explain the *reasoning history* behind the current state, not just the state itself, since that reasoning is what makes this project's numbers trustworthy.

**Fact-checked against the live repo at write time**: 62 eval queries (54 clear / 8 hard), 7 categories (`archive_no_action`, `broken_thread_headers`, `cross_customer_similarity`, `explicit_business_identifiers`, `informational_email`, `thank_you_appreciation`, `uncategorized`), `data/sample_dataset/seed_data.py` has zero pending changes (confirmed via `git diff --stat` — the corpus-enrichment proposal in §8 has **not** been implemented). Note: this entire active codebase (`recommender/`, `api/`, `dashboard/`, `data/`, `scripts/`, `tests/`) is currently **untracked in git** — nothing has ever been committed. Worth knowing; not something to fix unprompted.

---

## 1. Project Overview

### Goal

An AI-powered duplicate-ticket recommendation system for a Revenue Cycle Management (RCM) support operation. Client medical practices email in about billing issues (claims, prior authorization, eligibility, payment posting, accounts receivable, charge entry). The system's **only** job:

> Given an incoming email, decide whether it belongs to an existing open ticket for that customer, recommend which one, and explain why — with a confidence score. A human Account Manager accepts or rejects the recommendation. The system never auto-creates, auto-replies, or auto-archives anything.

This is deliberately narrower than full email triage (new-ticket / reply / archive classification) — that's explicitly out of scope. The system only ever answers "attach to existing ticket, or not."

### Current Architecture (locked — do not redesign without explicit user instruction)

Two halves:
- **Offline Interaction Indexing** (batch): new/updated interactions → filter to embeddable types (customer emails + agent replies only, *not* internal notes/system events) → clean text → embed via Ollama → store in pgvector, HNSW-indexed.
- **Online Recommendation** (per incoming email): the 9-stage pipeline below.

This architecture was locked by the user on 2026-07-30 after an earlier, more elaborate production-schema-mirroring effort (`app/`, `generation/`, `pilot/`, most of `docs/`) was explicitly paused in favor of a self-contained prototype. **Do not resurrect or reconcile with that legacy track unless the user explicitly asks.**

### Pipeline Stages (in order — see §6 for the "why" behind each)

1. **Preprocessing** (`recommender/preprocessing.py`) — strip HTML, strip quoted reply/forward history, strip signatures/disclaimers, normalize whitespace. `embedding_text = subject + "\n\n" + clean_body`.
2. **Customer identification** — exact inbox-email lookup. No match → hard stop (`path="unknown_customer"`), no retrieval, no LLM call.
3. **Thread detection** (`recommender/thread_detection.py`) — deterministic `conversation_id` → `in_reply_to` → `references` match against **non-terminal** tickets only. A hit skips the entire rest of the pipeline (`path="auto_attach"`, zero AI involved).
4. **Embedding** — via Ollama (`nomic-embed-text` by default).
5. **Hybrid retrieval** (`recommender/retrieval/hybrid.py`) — Postgres full-text (keyword) + pgvector ANN (embedding), merged via Reciprocal Rank Fusion (by rank position, not raw score — the two scales aren't comparable).
6. **Grouping/aggregation** (`recommender/grouping.py`) — interactions → tickets, `final_score = weight_max·max_score + weight_topk_avg·topk_avg + weight_recency·recency_score` (exponential decay). Top-M candidates survive.
7. **Context builder** (`recommender/context_builder.py`) — literal interaction text (matched interaction + neighbors), **no summarization**.
8. **Cross-encoder rerank** (`recommender/reranker.py`) — `BAAI/bge-reranker-base`, CPU. Top-K survive.
9. **LLM decision layer** (`recommender/decision.py`) — `qwen3:4b` via Ollama, structured JSON: `should_attach` / `candidate_index` (1-based, not real UUID — prevents ID hallucination) / `confidence` / `explanation`.

Orchestrated in `recommender/pipeline.py` (`run_pipeline`) and, for full observability (dashboard + eval harness), `recommender/pipeline_trace.py` (`run_traced_pipeline` — same stage functions, wrapped with timing/capture, zero logic duplication).

---

## 2. Current Project Status

### Completed
- Full 9-stage pipeline, end-to-end, verified.
- One real bug found and fixed via the benchmark (see §3, "baseline" row) — the `candidate_index` / `should_attach` downgrade bug.
- Debug dashboard (`api/` FastAPI + `dashboard/` React, 8 pages) with zero pipeline-logic changes, built purely as observability.
- Manager feedback loop (`recommendation_feedback` table, Accept/Reject in the Playground) — built and working, but has **no real usage data yet** (empty table). Distinct from the synthetic eval benchmark.
- Dataset expanded from ~24 to 50 tickets / 158 interactions / 12 customers.
- Eval benchmark grown from 21 → 62 queries across 5 iterations + a corpus audit's Stage 0/1 (full detail in §3).
- Non-determinism confirmed at **two** separate pipeline stages (LLM decision layer, and the reranker itself) and, as of 2026-08-04, **quantified** via a purpose-built repeated-trial tool rather than characterized from single observations (`NOISE_FLOOR_FINDINGS.md`).
- `ambiguity_type` taxonomy split (`multi_acceptable` vs. `single_answer`) added to all 8 hard cases — the reporting layer no longer conflates "genuinely ambiguous, declining is fine" with "one right answer, a miss is a real gap."
- Model-version metadata capture added to every eval run's output (Ollama digest/modified_at/quantization) — closes a reproducibility gap.

### In Progress — read this carefully, it's the most important state to preserve
**A corpus-enrichment proposal has been fully designed and presented to the user, but is NOT yet implemented.** `seed_data.py` has zero pending changes (confirmed). The proposal: deep-enrich two existing tickets (`R2` / `harborview_bh`, `A3` / `valley_womens_health`) with realistic multi-week interaction histories, rather than adding brand-new tickets. Full detail, including the drafted interaction-by-interaction content, is in **§8 — do not skip re-reading it before proceeding.** The user's last message before this handover was requested asked for this document instead of confirming — **the very next thing to do, if the user says "continue," is to get explicit confirmation on this design (or proceed with it if that confirmation is implicit in how the conversation resumes) — not to invent a new direction.**

### Intentionally Postponed (with reasoning — do not silently revisit without flagging why)
- **Benchmark-side**: a harder Broken-Headers case (degraded subject *and* stripped body together), Ambiguous Wording as its own independent axis, the Noisy/Informal Writing Style iteration (9 cases designed in an earlier session, never implemented — needs a scope decision first: standing 4th dimension vs. cross-cutting modifier).
- **Corpus-side**: Stage 4 (a new structural-difficulty construct — 4-way near-duplicate or a 2nd same-customer pair) and Stage 5 (internal-note realism, cosmetic only) — both lower priority than the current R2/A3 proposal.
- **Production-only items**, deliberately ranked "Group C" after a rigorous cost/benefit review (see `NOISE_FLOOR_FINDINGS.md`'s companion design-review discussion, not saved as a separate file — summarized in §5/§10): MRR/NDCG (no evidence of value — Recall@20/@3 already sit at 100% ceiling with tiny candidate pools), a formal held-out/blind eval set (exposure is bounded to ~5 hard cases, no second labeler available, disproportionate for this project's research/internship goal), adversarial/prompt-injection robustness testing (zero observed need, human-in-the-loop already mitigates it), model-version-pinning *enforcement* (metadata recording was implemented instead — cheaper, sufficient), and drift monitoring (literally no real production traffic exists yet to monitor drift against — the most clearly premature item on that list).

---

## 3. Benchmark History

All cases live in `data/sample_dataset/eval_queries.py`. Scored by `scripts/run_eval.py` against `recommender/pipeline_trace.py`. Full detail for every iteration below is in `data/sample_dataset/EVAL_HISTORY.md` (append-only index) and `data/sample_dataset/eval_reports/*.md` (one detailed report per iteration). **Rule, never violate**: the original 21 queries are frozen — never modify, only add. Every eval-query addition is safe by construction (can never affect another query's result); every corpus change requires a mandatory full re-run.

| Iteration | Date | Cases added | Why added | Key thing learned |
|---|---|---|---|---|
| **Baseline** | pre-2026-08-03 | 21 (17 clear / 4 hard) | First correctness check for the newly-built pipeline | First run scored 53%. Root-caused via instrumented tracing (not guessing) to a real bug: `decide()` silently downgraded a *correct* `should_attach=true` to `false` whenever the model omitted the optional `candidate_index` field (~75% of the time). One-line fix (default missing index to 0). Re-run: 21/21. **This "trace before hypothesizing" discipline governs every failure investigation since.** |
| **Thank You / Appreciation** | 2026-08-03 | 8 (`thankyou_*`) | Low-content gratitude tone had never been tested as a *fresh* incoming email | 7/7 clear passed at 0.94 avg. confidence (higher than baseline, not lower — the "low content → lower confidence" hypothesis was wrong). The 1 hard case failed cleanly: reranker signal collapses to near-zero discrimination on zero-topical-content queries. |
| **Informational Email** | 2026-08-03 | 8 (`info_*`) | FYI/no-request tone untested fresh | 7/7 clear passed. The hard case exposed a **methodology bug in how we build hard-case ground truth**: the acceptable-answer set was chosen by ticket recency alone, without checking each candidate's actual retrieval score — the "correct" answer turned out to be the retrieval-weakest of the field. **Lesson applied to every hard case since**: trace real grouping/rerank scores before locking in ground truth. |
| **Broken Thread Headers** | 2026-08-03 | 8 (`broken_headers_*`) | Tests every quote/forward-stripping pattern `preprocessing.py` handles, end-to-end through the real pipeline | 8/8 passed — first zero-failure iteration. But the hard case passed for the *wrong* reason: the subject line (`Re: <exact subject>`) did the work, not the aggressively-stripped body it meant to isolate — because `embedding_text = subject + body`. Flagged as an open follow-up (still open — see §2). |
| **Archive / No-Action** | 2026-08-03 | 8 (`archive_*`) | Cold "no action needed" emails, deciding from scratch (not a reply in a known thread) | **First-ever clear-case failure** (`archive_c4_claims_selfresolved`), reported as-observed rather than re-run-until-passing. Traced to confirmed LLM sampling non-determinism — broadened the known limitation from "affects only hard cases" to "can flip a clear case when retrieval doesn't cleanly favor the right answer." |
| **Corpus Coverage Audit → Stage 0 + Stage 1** | 2026-08-03 | 3 new queries (`crosscust_*`) + 7 tickets enriched with one agent reply each | A dedicated, query-independent audit of the corpus itself found 3 unused cross-customer lookalikes (free eval value) and 18% single-interaction tickets (realism gap) | 48/48 clear (100%), zero regression. `archive_c4` now passed — "consistent with a fix, not proof." A different hard case (`info_ambiguous_archive_boundary`) produced a *third* different wrong answer across observations, extending non-determinism to the **reranker's own scores**, not just the LLM. |
| **Phase 1 — Noise-floor measurement** | 2026-08-04 | 0 new queries (measurement only) | Every non-determinism finding above came from single observations — no one had ever deliberately repeated a query to measure a real rate | Built `--repeat N`/`--keys` on `run_eval.py`. Found `info_ambiguous_archive_boundary` is correct only 1/8 times across all observations (confidently wrong `C3` 4/8 times — worse than "sometimes noisy"). **Overturned a prior conclusion**: `archive_ambiguous_lakeside` was reported as reliably declining under honest ambiguity — actually confidently correct 4/6 of the time; declining is the minority behavior. `archive_c4` is 7/8 (meaningfully stabilized, not fully fixed). `thankyou_ambiguous_lowcontent` is genuinely stable (6/6 identical decline). 5-query stratified clear sample: 0/5 unstable. Full detail: `NOISE_FLOOR_FINDINGS.md`. |
| **Explicit Business Identifiers** | 2026-08-04 | 6 (`*_explicit_*`), one per RCM category | Every prior case was deliberately paraphrased (see §6 for why) — nothing tested the easier ceiling of an exact claim/auth-number citation | 6/6 passed, 0.98 avg. confidence (2nd-highest category). Failure analysis took one paragraph, not a fresh investigation, because Phase 1 had already characterized every hard-case failure in this run — direct payoff of doing measurement work before scenario work. Also surfaced a minor pre-existing data-integrity issue: `info_a3_priorauth_selfresolved` cites an auth number that doesn't actually exist in the real corpus content (not fixed, flagged per the append-only doc discipline). |

**Current benchmark coverage** (62 queries, 54 clear / 8 hard):
- Clear-case accuracy: **54/54 (100%)**. Recall@20/@3: **100%/100%**.
- Hard cases, split by the new taxonomy: **single_answer: 3/3 passed** (`pm2_pm4_disambiguation`, `c1_hard_paraphrase`, `broken_headers_terse_after_strip`) — the "true difficulty ceiling" bucket is fully solid. **multi_acceptable: 2/5 passed** (`near_dup_p6_p7`, `three_way_ar` pass; `thankyou_ambiguous_lowcontent`, `info_ambiguous_archive_boundary`, `archive_ambiguous_lakeside` fail — all 3 failures fully pre-characterized by `NOISE_FLOOR_FINDINGS.md`, not open questions).
- All 6 RCM service categories covered in a 6-12 case range (no longer the original 5x skew).
- Remaining named gaps: harder Broken-Headers case, Ambiguous Wording as an independent axis, Noisy Writing (undecided scope).

---

## 4. Corpus Evolution

All content in `data/sample_dataset/seed_data.py` (hand-authored literals, not generated).

- **Original**: ~24 hand-authored tickets, used to verify the pipeline end-to-end.
- **Expansion to 50 tickets / 151 interactions / 12 customers**: deliberate coverage of cross-customer lookalikes, near-duplicate/3-way same-customer disambiguation, missing-identifier emails, long-running multi-week threads, a "looks like a denial but was actually approved" false-positive trap.
- **Corpus Coverage Audit** (2026-08-03, `CORPUS_COVERAGE_AUDIT.md`) — a from-scratch, quantitative audit **independent of any eval query** (deliberately: it answers "is the underlying data realistic," which no benchmark-query result can answer on its own). Findings, in priority order:
  1. 18% of tickets (9/50) had exactly one interaction — no agent reply ever recorded.
  2. Long-running conversation coverage (>5 interactions) was 2 tickets, **both belonging to the same customer** (`pinehill_ophtho`).
  3. Per-customer interaction richness varied 5x (`pinehill_ophtho` 7.0 avg/ticket vs. `harborview_bh` 1.3 avg/ticket).
  4. 3 real cross-customer lookalike pairs existed in the corpus but were never tested (free eval value, zero corpus risk).
  5. Only 3 structural-difficulty *families* total; minimal internal-note interaction-type diversity (3/151).
- **Stage 0** (mine the 3 latent lookalikes — zero corpus risk, pure query addition): **DONE**.
- **Stage 1** (enrich the 7 non-frozen single-interaction tickets with one agent reply each — real risk, mandatory full re-run): **DONE**. Corpus grew 151 → 158 interactions. `PM1`/`PM7` deliberately excluded (part of the frozen original 21 — enriching them would silently redefine what "frozen baseline" means).

### Current corpus limitations (as of this writing)
- `harborview_bh`'s 3rd ticket (`R2`) is still thin — explicitly named in the roadmap as "remains untouched" after Stage 1.
- Long-running/evolving-context coverage is still concentrated in `pinehill_ophtho` alone.
- Per-customer richness imbalance is still real (`valley_womens_health`, `metro_cardiology` tied lowest at 2.0 avg interactions/ticket among customers not already targeted).
- Only 3 structural-difficulty families exist (no 4-way near-duplicate, no 2nd same-customer pair).
- Internal-note/attachment interaction-type diversity is minimal — low priority, since these types aren't embedded/retrieved per the production contract anyway.

### Current roadmap
The original `CORPUS_EXPANSION_ROADMAP.md` proposed Stage 2 (deepen `harborview_bh` with a **new** ticket) and Stage 3 (a **new** long-running ticket for a customer other than `pinehill_ophtho`) as the next steps — both still formally "proposed, not approved" in that file. **These have since been superseded in the live conversation by a more specific, more conservative proposal** (deep-enrich *existing* tickets instead of adding new ones — lower structural risk, since it doesn't grow any customer's candidate-pool size). See §8 for the exact, current, awaiting-confirmation design. **`CORPUS_EXPANSION_ROADMAP.md` itself has not yet been updated to reflect this pivot — do that as part of implementing §8, not before.**

---

## 5. Evaluation Methodology

### Benchmark philosophy
Fully synthetic, hand-authored corpus and queries — chosen deliberately to solve a cold-start problem (no real production traffic exists yet to mine ground truth from) and to guarantee ground-truth certainty (the author controls both the ticket content and the "correct" answer). Traded realism for certainty on purpose, at exactly the stage where certainty is what catches bugs. Governed by explicit standing rules: never modify the frozen 21; one named capability per iteration; every expected outcome traceable to real ticket content, not vibes; avoid near-verbatim wording (would make matches trivially easy and teach nothing); avoid stacking multiple difficulties in one query (makes failure attribution ambiguous); propose the full iteration design and get it confirmed before writing code.

### Noise-floor methodology
Confirmed non-determinism at two independent stages — the LLM decision layer (`qwen3:4b`, temperature 0, still shows sampling variance because it's a local "thinking" model) and, separately, the cross-encoder reranker itself (raw scores vary run-to-run on bit-for-bit identical input — mechanism not diagnosed, only empirically confirmed; floating-point non-associativity in batched inference is plausible but unverified). Every prior finding came from single, reactive observations (a case happened to fail and got traced) — never a deliberate, systematic measurement, until Phase 1 (2026-08-04).

### Repeat testing
`scripts/run_eval.py --repeat N --keys key1,key2,...` — runs each selected query N times, reports a pass-rate and the set of distinct answers seen, instead of a single boolean. **Deliberately targeted, not brute-force**: repeating the entire 62-query suite N times would cost hours for negligible marginal value on cases with wide score margins that will essentially never flip. Target known-flaky/previously-single-observation cases plus a small stratified sample of comfortably-passing clear cases (to check for hidden instability elsewhere). Output for `--repeat > 1` writes a **different-shaped payload** (`"runs": [...]` per query, not a flat `"correct"` boolean) — **never write this to the `eval_results_*.json` naming pattern**, the dashboard's `evaluation_service.py` globs exactly that pattern and expects the normal single-run shape.

### Regression testing
Two different safety tiers: (1) a new eval query can *never* affect any other query's result — safe by construction, no re-run strictly required for correctness, though one is still always done for reporting consistency; (2) a corpus change (new ticket, or enriched existing ticket) *can* affect other queries' results (grows/changes a customer's candidate pool or a ticket's embedded content) — **mandatory full re-run before accepting**, no exception, regardless of how "low-risk" the change seems.

### Why full benchmark reruns are performed every time
Not purely about risk-detection — it's also how every category/headline number in `EVAL_HISTORY.md` has ever been produced. Skipping a full re-run on a "safe" query-only addition would make that iteration's numbers non-comparable with every other row in the table. Consistency of measurement method is treated as more important than saving the ~60-70 minutes it currently costs.

---

## 6. Important Design Decisions

**Why hybrid retrieval (keyword + ANN), not either alone**: keyword search catches exact identifiers (claim numbers, payer names) that dense embeddings can blur; ANN/embedding search catches semantic paraphrase that keyword search misses entirely. RRF merges them **by rank position, not raw score**, because `ts_rank` and cosine similarity live on incomparable scales — rank-based fusion needs no cross-system calibration.

**Why reranking (a second, more expensive stage)**: a cross-encoder scores `(query, candidate)` jointly, attending across both texts — meaningfully more accurate at relevance judgment than a bi-encoder's independently-computed cosine similarity, but too slow to run un-indexed over an entire corpus. Hence the classic two-stage IR pattern: cheap/broad retrieval narrows the field first, expensive/accurate reranking only touches the survivors.

**Why thread detection runs first and can skip everything else**: it's the one signal in the whole pipeline that's deterministic ground truth (a literal message-ID match), not a similarity estimate. Paying for embedding/retrieval/rerank/LLM on it would add latency and non-determinism risk for zero benefit. Explicitly excludes terminal-status tickets — a reply to an old closed-ticket thread shouldn't silently reopen it; that case falls through to the full AI pipeline instead.

**Why literal context, never a summary**: summarization is itself a lossy, error-prone LLM step. Passing literal interaction text keeps ground truth intact for every downstream stage (reranker, LLM) instead of adding a second failure mode stacked on top of the one the pipeline already needs (the decision layer itself).

**Why semantic/paraphrase benchmark cases came before the identifier-anchored ("easy ceiling") ones**: this was a standing rule from the very first eval case, not an afterthought — "avoid near-verbatim copies of ticket wording" is explicit in the benchmark's process rules, precisely because trivially-easy exact-match cases teach little about whether the system's actual semantic/reasoning capability works. Five iterations deliberately stress-tested paraphrase, disambiguation, and reasoning under ambiguity first. Only once that capability was extensively validated did testing the easier ceiling become worth doing — both for completeness (real traffic will include plenty of exact-identifier emails) and as a diagnostic tool: `pm1_paraphrase` and `pm1_explicit_claim` target the *same* ground truth via two different mechanisms, so a future regression that breaks keyword-matching specifically (but not semantic matching, or vice versa) would now show up as that pair diverging.

**Why corpus realism is the current priority, over remaining benchmark items**: after 5 benchmark iterations plus Phase 1's measurement infrastructure, the coverage review's own words describe what's left on the benchmark side as "narrow and mechanical." Meanwhile the Corpus Coverage Audit's most significant finding — long-running, evolving-context conversation coverage concentrated in a single customer — is structurally impossible for any benchmark query to fix (a fresh incoming email tests whether *that email* attaches correctly; it cannot retroactively give a *ticket* a richer history it doesn't have). Only a corpus change closes this gap, and it maps directly onto the user's own stated goal of testing real-world RCM communication patterns, not a tangent from it.

---

## 7. Current Phase

Per the phased plan agreed after the user clarified scope (explicitly: **Path B — harden the system as-is, pre-integration**, not yet integrating with any real production ticketing system; PHI/compliance is confirmed relevant for whenever integration eventually happens, tracked as a parallel, non-blocking track, not currently gating any engineering work):

- **Phase 1 — Measurement foundation**: ✅ **DONE**. `--repeat`/`--keys` tooling, model-version metadata, hard-case taxonomy split, `NOISE_FLOOR_FINDINGS.md`.
- **Phase 2 — Close already-known gaps + corpus realism**: **IN PROGRESS**.
  - ✅ Explicit Business Identifiers (done, §3).
  - 🔶 Corpus realism/enrichment — **designed, awaiting confirmation, not implemented** (§8).
  - ⬜ Harder Broken-Headers case, Ambiguous Wording axis, Noisy Writing scope decision — not started.
  - ⬜ Corpus Stage 4/5 — not started, lower priority than the current proposal.

**What has just been completed**: the Explicit Business Identifiers iteration (full 4-deliverable cycle) and the Phase 1 noise-floor measurement pass, including two corrections to previously-published characterizations (documented via append-notes, not silent rewrites, per this project's documentation discipline).

**What remains in Phase 2**: get the §8 corpus-enrichment design confirmed and implemented (this is the very next piece of work), then the remaining benchmark items in whatever order the user prefers, then reassess whether Stage 4/5 are still needed from that new baseline — consistent with this project's standing "measured-results-driven, not committed upfront" process for corpus work.

---

## 8. Next Recommended Task

**Implement the corpus-enrichment design below, once confirmed by the user.** This is a complete restatement of the design as last presented — a new session should be able to execute directly from this section without needing anything else.

### Selection: 2 tickets, deliberately not more

| Ticket | Customer | Current state | Why this one |
|---|---|---|---|
| `R2` | `harborview_bh` | 2 interactions, "Patient balance dispute after insurance adjustment", IN_PROGRESS | Explicitly named in `CORPUS_EXPANSION_ROADMAP.md` as the one thing Stage 1 didn't touch. |
| `A3` | `valley_womens_health` | 2 interactions, "Missing prior auth number on submitted claim", OPEN | `valley_womens_health` is tied for the lowest customer richness in the corpus (2.0 avg interactions/ticket). Prior-auth appeals are a naturally slow, multi-touchpoint RCM workflow. |

**Deliberately excluded from this pass**: `C4` (also `valley_womens_health`; the ticket behind `archive_c4_claims_selfresolved`, which has a known ~87.5% empirical stability per `NOISE_FLOOR_FINDINGS.md`). Deepening an already-partially-fragile case is worth trying, but as its own dedicated before/after experiment later — not bundled into a first general-realism pass, to keep this pass cleanly attributable.

**Also deliberately not chosen**: `metro_cardiology` (also 2.0 avg, tied-lowest) — its candidate pool (`E1`/`A2`/`C3`/`G4`) is exactly what `info_ambiguous_archive_boundary` draws from, the single most unstable case in the whole benchmark (confidently wrong ~50% of the time). Touching that customer's tickets right now would disturb the most fragile thing in the benchmark for no clear benefit.

### Drafted arcs (grounded in each ticket's real existing seed content — verify against `seed_data.py` before writing, don't assume this transcription is byte-perfect)

**`R2` — harborview_bh, accounts_receivable.** Existing 2 interactions kept, 6 new added, spanning ~30 days:
1. *(existing)* Customer flags a $180 patient balance dispute after an insurance adjustment.
2. *(existing)* Agent starts reviewing the EOB.
3. **+3d, agent**: EOB confirms $180 patient responsibility is correct — but the patient may have been quoted from a different EOB by their insurer; asks the practice to have the patient confirm directly with the insurer.
4. **+7d, customer**: patient followed up — the $0 quote was for a *different* visit; she now acknowledges owing $180 for this one.
5. **+7.5d, agent**: good to have it cleared up, sending the statement now.
6. **+20d, customer**: patient can't pay in full, asks about a payment plan.
7. **+21d, agent**: sets up a 3-month, $60/month plan.
8. **+30d, agent**: first payment posted; will track remaining installments, closing out as resolved for now.

Suggested metadata update: `status` → `RESOLVED`, `age_days` extended to accommodate the full ~30-day arc (currently 10 — needs to become roughly 32-35 so `days_ago()` correctly precedes the interaction timeline), `closed_age_days` set a couple of days after the last interaction (per the corpus's existing convention of `closed_age_days < age_days`).

**`A3` — valley_womens_health, prior_authorization.** Existing 2 interactions kept, 5 new added, spanning ~35 days:
1. *(existing)* Customer flags claim #90112 rejected for missing auth number.
2. *(existing)* Agent pulls the original authorization, will add it and resubmit.
3. **+1d, agent**: resubmitted with the auth number added.
4. **+8d, agent**: denied *again* — payer now claims the authorization had expired by the date of service, despite being valid when approved.
5. **+9d, customer**: pushes back — the visit was well within the original 90-day approval window.
6. **+10d, agent**: agrees, files an appeal with the approval letter and visit date attached.
7. **+24d, agent**: payer acknowledges the error, agrees to reprocess under the original auth.
8. **+35d, agent**: claim #90112 reprocessed and paid correctly; closing out.

Suggested metadata update: `status` OPEN → `RESOLVED`, `age_days` extended to roughly 38, `closed_age_days` ≈ 3.

### Implementation steps
1. Write the new interactions into `data/sample_dataset/seed_data.py`'s `INTERACTIONS["R2"]` and `INTERACTIONS["A3"]` lists, and update the corresponding `TICKETS` entries' `age_days`/`status`/`closed_age_days`.
2. Re-seed and re-index: `python scripts/init_db.py` is **not** needed (no schema change) — just re-run `python scripts/seed_data.py` then `python scripts/run_indexing.py` (mirrors how Stage 1 was applied).
3. Full benchmark re-run (mandatory for any corpus change): `python scripts/run_eval.py --output data/sample_dataset/eval_results_<date>.json`.
4. **New, more rigorous verification step this project didn't have during Stage 0/1**: targeted repeat-trial check on the existing cases that touch these two tickets — `--keys a3_explicit_claim,info_a3_priorauth_selfresolved,broken_headers_original_message --repeat 5` — to confirm richer context doesn't destabilize anything currently solid, with a real before/after comparison instead of Stage 1's single-observation "consistent with a fix" language.
5. Write the standard deliverables: an entry in `EVAL_HISTORY.md` (note this is a corpus-only change, no new eval queries), update `CORPUS_EXPANSION_ROADMAP.md` to reflect this pivot away from the original Stage 2/3 "new ticket" framing, and a short report under `eval_reports/` following the established template.

### Why this is the right next task (not a different one)
It's the only currently-designed, user-confirmed-in-principle piece of work sitting at "ready to implement" — everything else in Phase 2 (§2, §7) is either lower-priority or not yet designed at this level of detail.

---

## 9. Important Files

| Path | Responsibility |
|---|---|
| `recommender/pipeline.py` | `run_pipeline` — the real, production online-recommendation orchestration. Do not modify casually; `tests/recommender/test_pipeline_e2e.py` covers it. |
| `recommender/pipeline_trace.py` | `run_traced_pipeline` — same stages, timed/captured for the dashboard and `run_eval.py`. Both share this so they can't drift apart. |
| `recommender/preprocessing.py` | Email/interaction text cleaning: HTML stripping, quote/forward-history stripping, signature removal, `embedding_text` construction. |
| `recommender/thread_detection.py` | Deterministic auto-attach shortcut. |
| `recommender/retrieval/hybrid.py`, `ann_search.py`, `keyword_search.py` | Hybrid retrieval + RRF. |
| `recommender/grouping.py` | Interaction → ticket aggregation (max/topk-avg/recency scoring). |
| `recommender/context_builder.py` | Literal-text context assembly per candidate ticket. |
| `recommender/reranker.py` | Cross-encoder reranking. |
| `recommender/decision.py` | LLM decision layer — includes the `candidate_index` default-to-0 fix; be careful modifying this, it's the site of the one confirmed real bug in project history. |
| `recommender/ollama_client.py` | Ollama HTTP wrappers: `embed_texts`, `chat_structured`, and `get_model_info` (added 2026-08-04 for reproducibility metadata). |
| `recommender/eval_reporting.py` | Shared summarization logic (`summarize_results`, `format_console_report`) — used by both `scripts/run_eval.py`'s console output and the dashboard's Evaluation page, so they can't diverge. Includes the `ambiguity_type` split added 2026-08-04. |
| `recommender/config.py` | `RecommenderConfig`/`settings` — all tunables live in `config/recommender_config.yaml`, not hardcoded. |
| `recommender/models.py` | SQLAlchemy models, including `RecommendationFeedback`. |
| `data/sample_dataset/seed_data.py` | The actual corpus — `TICKETS`, `CUSTOMERS`, `INTERACTIONS` dicts. Hand-authored literals only. **Any change here requires a full benchmark re-run.** |
| `data/sample_dataset/eval_queries.py` | The benchmark — `EVAL_QUERIES` list. **Original 21 are frozen, never modify.** Read its module docstring before adding cases — it documents the `difficulty`/`ambiguity_type`/`category` field conventions precisely. |
| `data/sample_dataset/EVAL_HISTORY.md` | Append-only run index. Never rewrite a past row — add a correcting note in a later entry instead. |
| `data/sample_dataset/BENCHMARK_COVERAGE_REVIEW.md` | Living audit of the *benchmark* (workflow/service/scenario coverage) — independent of the corpus audit below. Update after every iteration. |
| `data/sample_dataset/CORPUS_COVERAGE_AUDIT.md` | Living, quantitative audit of the *corpus itself*, deliberately independent of any eval query — computes directly from `seed_data.py`. |
| `data/sample_dataset/CORPUS_EXPANSION_ROADMAP.md` | Staged, risk-annotated corpus-change plan. Needs updating once §8 is implemented (the current text still describes the superseded "add new tickets" framing for Stage 2/3). |
| `data/sample_dataset/NOISE_FLOOR_FINDINGS.md` | The 2026-08-04 repeated-trial measurement results. Read before trusting any single-observation characterization of a hard case. |
| `data/sample_dataset/eval_reports/*.md` | One detailed report per iteration — evaluation report + failure analysis + notable observations. |
| `scripts/run_eval.py` | The eval harness. `--limit`, `--keys`, `--repeat`, `--output` flags. Read the module docstring — it documents exactly why `--repeat` output must not use the `eval_results_*.json` naming pattern. |
| `scripts/seed_data.py`, `scripts/run_indexing.py`, `scripts/init_db.py` | Load corpus into Postgres; embed pending interactions; create schema/indexes. |
| `api/main.py`, `api/routers/`, `api/services/`, `api/schemas/` | Thin FastAPI glue over `recommender/` for the dashboard. Zero business logic here by design. |
| `dashboard/` | React/Vite/TS debug dashboard, 8 pages. `.env` sets `VITE_API_BASE_URL` — **currently `http://localhost:8001`, not the default 8000** (see environment note below). |
| `config/recommender_config.yaml` | All tunables (models, retrieval top-N, aggregation weights, reranker device, decision timeout). |
| `tests/recommender/` | 27 unit tests, currently passing. |
| `README.md` (repo root) | The maintained day-to-day handoff doc. Read it too — this file adds reasoning history, not a replacement. |

### Environment / operational notes (learned the hard way this session — save yourself the rediscovery time)
- **Port 8000 is permanently occupied on this machine by an unrelated project** (`C:\Users\vishnu\Unified-ticket-management-system\unified-backend`, its own FastAPI app, its own venv). Do **not** try to free it or stop that process. This project's backend runs on **8001** instead — `dashboard/.env`'s `VITE_API_BASE_URL` is already set to `http://localhost:8001` to match.
- The bare `uvicorn` command on this machine resolves to a broken global launcher tied to a stale Python 3.14 install. Always invoke via the venv explicitly: `.venv\Scripts\python.exe -m uvicorn api.main:app --host 0.0.0.0 --port 8001`.
- Vite auto-increments to 5174 if 5173 is already taken by a stray/orphaned process — check `Get-NetTCPConnection -LocalPort 5173` before assuming the dashboard is reachable at the default URL; CORS only allows `localhost:5173`/`127.0.0.1:5173`, not 5174.
- LLM-backed eval queries take highly variable time — historically documented as 30s-3min, but observed as low as 20s and as high as 750s (12.5 min) in this session. Do not assume a fixed budget; always run full-suite evals in the background.
- The Postgres container (`rcm-pgvector`, port 5433) and Ollama (`qwen3:4b`, `nomic-embed-text`) were both already running throughout this session — check before assuming you need to start them.

---

## 10. Things a New Claude Must NOT Change Without Discussion

1. **The locked pipeline architecture** (§1/§6) — do not propose redesigning any of the 9 stages or their ordering. This was deliberately decided and repeatedly reconfirmed.
2. **The original 21 eval queries** — never modify, only add. This is what makes every "no regression" claim in `EVAL_HISTORY.md` meaningful.
3. **`EVAL_HISTORY.md`'s append-only discipline** — never rewrite a past row, even one that turns out to be wrong. Add a correcting note in a later entry instead (see the `archive_ambiguous_lakeside` correction in `eval_reports/2026-08-03_archive_no_action.md` for the exact pattern to follow).
4. **The mandatory full-re-run rule for any corpus change** — no exceptions for "this seems low-risk."
5. **The legacy `app/`, `generation/`, `pilot/` tracks** — a different, paused effort with a different data model entirely. Don't touch or try to reconcile without an explicit user request.
6. **The §8 corpus-enrichment design** — don't substitute a different design (e.g., reverting to "add new tickets" instead of "enrich existing ones") without re-confirming with the user; the pivot to enrichment-over-addition was a deliberate response to a regression-risk concern raised in conversation, not an arbitrary choice.
7. **The deliberately-deprioritized Group C items** (§2) — MRR/NDCG, a formal held-out set, adversarial/prompt-injection testing, drift monitoring, model-pinning enforcement. Each was rejected with specific reasoning tied to this project's actual current evidence and stated goals (a research/internship-grade benchmark, not a production certification). Don't implement any of these without surfacing the reasoning again and getting it re-evaluated — the reasoning could genuinely change (e.g., if real production integration becomes imminent), but it shouldn't be silently reversed.
8. **Port 8000** — don't use it for this project's backend, and don't stop whatever else is using it.
9. **Don't run a full 62-query eval suite without warning about runtime** (60-70+ minutes observed) and running it in the background.
10. **Don't commit anything to git without being asked** — the entire active codebase is currently untracked; that's the existing state, not a problem to silently fix.
