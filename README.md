# RCM Ticket Recommendation System

**Status as of this writing (2026-08-04)**: core pipeline built and working, debug dashboard built and working (including a now-real, data-backed Evaluation page), manager feedback loop built and working, the regression benchmark has grown from 21 to 62 cases (**54/54 clear-case accuracy, 100%**, 5/8 hard cases) across five workflow iterations (Thank You/Appreciation → Informational Email → Broken Thread Headers → Archive/No-Action → Explicit Business Identifiers) plus a Corpus Coverage Audit and its first two approved expansion stages, all under a 4-deliverable process (queries + report + failure analysis + history log). One real bug was found and fixed via the benchmark; non-determinism (at both the LLM decision layer and the reranker) has been traced, reported honestly, and — as of 2026-08-04 — **quantified via repeated-trial measurement** (`scripts/run_eval.py --repeat`/`--keys`, see `NOISE_FLOOR_FINDINGS.md`) rather than characterized from single observations. The corpus itself was audited independently of the benchmark (`CORPUS_COVERAGE_AUDIT.md`) and enriched from 151 to 158 interactions with zero regression. See "Evaluation Benchmark" and "Current dataset" below for exactly where to resume.

This file is the handoff document — read this first in any new session before touching code.

---

## 1. What this project is

An AI-powered duplicate-ticket recommendation system for a Revenue Cycle Management (RCM) support operation. Client practices email in about billing issues (claims, payment posting, prior authorization, eligibility, accounts receivable, charge entry). The **only** job of this system is:

> Given an incoming email, decide whether it belongs to an existing open ticket for that customer, recommend which one, and explain why — with a confidence score. A human Account Manager accepts or rejects the recommendation. The system never auto-creates, auto-replies, or auto-archives anything.

This is a narrower scope than full email triage (which would also classify "new ticket / reply directly / archive") — that fuller classification is explicitly out of scope; this system only ever answers "attach to existing ticket, or not."

## 2. Locked architecture (do not redesign)

Two halves, per the original architecture diagram this was built against:

**Offline Interaction Indexing** (batch, runs separately): new/updated interactions → filter to embeddable types (customer emails + agent replies only, not internal notes/system events) → clean text → embed via Ollama → store in pgvector, HNSW-indexed.

**Online Recommendation** (per incoming email): Preprocess → Identify customer (exact inbox-email lookup) → Thread detection (deterministic conversation_id/in_reply_to/references match against non-terminal tickets — if it hits, auto-attach immediately, no AI involved) → Embed → Hybrid retrieval (Postgres full-text + pgvector ANN, merged via Reciprocal Rank Fusion) → Group interactions by ticket, weighted score (max/top-k-avg/recency) → Top 20 candidates → Context builder (literal interaction text, no summarization) → Cross-encoder rerank → Top 3 → LLM decision (structured JSON: should_attach/candidate_index/confidence/explanation) → Recommendation.

Full narrative walkthrough of every stage (with actual config numbers) is in the project's chat history; the code itself is the source of truth — see file map below.

## 3. Repo layout (what's real vs. legacy)

- **`recommender/`** — the actual, locked pipeline. Everything above lives here. This is the only package that matters for the recommendation logic.
- **`api/`** — thin FastAPI backend, zero business logic, exposes the pipeline + dataset + feedback over HTTP for the dashboard. No auth (trusted local tool).
- **`dashboard/`** — React+Vite+TS+Tailwind internal debug/eval dashboard (8 pages: Home, Playground, Pipeline Explorer, ANN Inspector, Dataset Explorer, Metrics, Evaluation, Settings).
- **`data/sample_dataset/`** — `seed_data.py` (the actual ticket/interaction dataset), `eval_queries.py` (the regression benchmark — see §6), `EVAL_HISTORY.md` (append-only log of every benchmark run's headline numbers), `eval_reports/` (one detailed report + failure analysis per iteration), `BENCHMARK_COVERAGE_REVIEW.md` (living 3-dimension coverage audit of the *benchmark*), `CORPUS_COVERAGE_AUDIT.md` (living, quantitative audit of the *corpus itself* — interaction depth, per-customer richness, structural-difficulty inventory — independent of any eval query), `CORPUS_EXPANSION_ROADMAP.md` (staged, risk-annotated plan for growing the corpus, tracked separately from benchmark iterations).
- **`scripts/`** — `init_db.py` (schema+indexes), `seed_data.py` (load dataset), `run_indexing.py` (embed pending interactions), `recommend.py` (CLI), `compute_metrics.py` (accuracy/precision/recall from manager feedback), `run_eval.py` (automated benchmark runner).
- **`config/recommender_config.yaml`** — every tunable (embedding model, retrieval top-N, aggregation weights, reranker model/device, decision model/timeout). Change behavior here, not by editing code.
- **`tests/recommender/`** — 27 tests, all passing, covering preprocessing/thread-detection/full pipeline e2e.
- **`app/`, `generation/`, `pilot/`, most of `docs/`** — **legacy, paused track.** An earlier effort to mirror the real production schema and generate a large synthetic benchmark via LLM templates. Abandoned when the architecture was locked in favor of `recommender/`'s self-contained approach. Don't reconcile these with `recommender/` unless explicitly asked — they're a different data model entirely. `PROJECT_PLAN.md` at the repo root is also stale (describes this abandoned track) — this README supersedes it for current state.

## 4. How to run it

**One-time setup**: `pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu`, `cd dashboard && npm install`, `ollama pull nomic-embed-text`, `ollama pull qwen3:4b`.

**Every session**:
1. `docker start rcm-pgvector` (pgvector Postgres container, port **5433** — deliberately separate from any native Postgres on 5432; if the container doesn't exist yet: `docker run --name rcm-pgvector -e POSTGRES_PASSWORD=postgres -p 5433:5432 -d pgvector/pgvector:pg16`). Requires Docker Desktop actually running first.
2. Confirm Ollama is up: `curl http://localhost:11434/api/tags` (it usually runs as a background service already — don't `ollama serve` manually, it'll just fail to bind since it's already running).
3. First time only / after a reset: `python scripts/init_db.py` → `python scripts/seed_data.py` → `python scripts/run_indexing.py`.
4. Backend: `uvicorn api.main:app --host 0.0.0.0 --port 8000` (no `--reload` — breaks on Windows with a socket permission error).
5. Frontend: `cd dashboard && npm run dev` → open `http://localhost:5173`.

All Python commands assume the project venv: `.venv/Scripts/python.exe` (Windows-native, not the MSYS-style path).

## 5. Current dataset

12 customers, 50 tickets, **158 interactions (155 embeddable)** as of 2026-08-03, balanced ~8-9 tickets per RCM category. One customer, **PainMed PA** (`gogineni@painmedpa.com`), is deliberately the "use your own email to test" customer with 7 tickets across all 6 categories.

The dataset was deliberately expanded (from an original ~24-ticket hand-authored set) to cover specific QA dimensions: RCM service coverage (all 6 categories), business-workflow tone variety (escalation, appreciation, closure, document-submission, informational/no-action), and recommendation-difficulty scenarios (cross-customer lookalikes, near-duplicate same-customer tickets, 3-way disambiguation, missing-identifier emails, long-running multi-week threads, a "looks like a denial but was actually approved" false-positive trap).

**Corpus audited and (lightly) grown 2026-08-03**: `data/sample_dataset/CORPUS_COVERAGE_AUDIT.md` is a from-scratch, quantitative audit of the corpus *independent of the eval benchmark* — interaction-depth distribution, per-customer richness, long-running-conversation coverage, and a structural-difficulty inventory (found 3 real cross-customer lookalike pairs that existed but had never been tested). Its top finding: 18% of tickets (9/50) had exactly one interaction (no agent reply ever recorded) — the single biggest realism gap found. **Stage 1** of `CORPUS_EXPANSION_ROADMAP.md` enriched 7 of those 9 (excluding `PM1`/`PM7`, which are part of the frozen original 21 — see §6a) with one grounded agent reply each, taking the corpus from 151 to 158 interactions; a full benchmark re-run confirmed zero regression. Stages 2-5 (deepen the thinnest customer, add a long-running ticket for a customer other than the one that currently owns both of them, a new structural-difficulty construct, internal-note realism) are proposed but not approved — see the roadmap for exact status.

## 6. Evaluation benchmark — **read this before doing anything else here**

This is mid-process. Here's exactly where it stands:

### 6a. What exists and is frozen

`data/sample_dataset/eval_queries.py` — **56 hand-written eval queries** (the original frozen 21 + 8 Thank You/Appreciation + 8 Informational Email + 8 Broken Thread Headers + 8 Archive/No-Action + 3 Cross-Customer Similarity, all added 2026-08-03), each an (incoming email → expected ticket, or expected "no match") pair with a `difficulty` tag (`clear` vs `hard`/deliberately-ambiguous) and, for cases added from 2026-08-03 onward, a `category` tag. `scripts/run_eval.py` runs every query through the real pipeline and scores it automatically — no manual UI clicking needed. Reports: clear-case accuracy, Recall@20 (did the right ticket reach the candidate pool), Recall@3 (did it survive reranking), and a per-category breakdown when more than one category is present.

**Current status: 48/48 clear-case accuracy (100%), 100% Recall@20, 100% Recall@3, 5/8 hard cases passing.** This is back to 100% after the corpus-enrichment re-run — the one clear-case failure from the prior run (`archive_c4_claims_selfresolved`) now passes, consistent with (though not proof of) the corpus enrichment having stabilized it; see `eval_reports/2026-08-03_corpus_stage0_stage1.md` §2 for exactly what that evidence does and doesn't establish. The original 21 queries are still frozen and unmodified — **do not modify them**, that rule stands. Every run's headline numbers are logged in `data/sample_dataset/EVAL_HISTORY.md`, with a full per-iteration report under `data/sample_dataset/eval_reports/`; check there before assuming a number instead of re-deriving it from memory.

**To save a run so it shows up in the dashboard's Evaluation page**: pass `--output data/sample_dataset/eval_results_<date>.json` — without `--output`, results only print to the terminal. Reusing an existing filename overwrites that run instead of adding a new history row; use a distinct, dated filename each time.

### 6b. The bug that was found and fixed (important precedent for method)

First eval run scored only 53% (9/17 clear cases). Root-cause investigation (not guessing — actual instrumented tracing of raw LLM JSON output at every transformation boundary) found: **the LLM's `should_attach: true` decision was correct in every failing case**, but `recommender/decision.py`'s post-processing silently downgraded it to `false` whenever the model omitted the optional `candidate_index` field (which it did ~75% of the time) — because `DecisionResult(should_attach = should_attach and ticket_id is not None, ...)` requires a resolved ticket_id, which requires a candidate_index, which the model often just didn't include even when it meant to attach.

**Fix applied** (`recommender/decision.py`, `decide()`): when `should_attach=True` but `candidate_index` is missing, default to index 0 (candidate 1 — the reranker's top pick, which is what the model's own explanation was discussing in every observed case) instead of silently discarding the decision. One-line change. Re-ran full eval after: 21/21. Re-ran all 27 pre-existing tests: still passing. No new false positives on the two "must correctly say no match" cases.

Methodological lesson worth preserving: **when a benchmark shows unexpected failures, instrument and trace real evidence (raw HTTP responses, parsed objects, each transformation step) before hypothesizing a fix.** The first hypothesis (schema field ordering forcing a premature decision) was plausible-sounding but wrong — the actual mechanism (missing optional field silently downgrading a correct decision) was different and was only found by capturing the literal raw JSON the model returned.

### 6c. The process going forward (rules, agreed with the user)

1. Never modify the existing 21 eval queries, the recommendation pipeline, or the knowledge base/dataset as part of benchmark work — only ever *add* new queries.
2. Each iteration adds ~8-10 new queries covering **one** specific, named capability — not a grab-bag.
3. Each new query must test something the existing 21 do not already cover.
4. Every query needs a justified expected outcome (traceable to specific ticket content, not vibes) and an explanation of the real-world scenario it represents.
5. Avoid near-verbatim copies of ticket wording (that makes matches trivially easy) and avoid stacking multiple unrelated difficulties into one query (makes failures hard to attribute).
6. Propose a full iteration design (theme, rationale, all cases with sender/body/expected/why/what's-being-tested, plus a coverage summary of already-covered vs. new vs. still-remaining capabilities) and **get it approved before writing any code** — this has been the pattern for every iteration so far.

### 6d. Exact current state — where to pick up

**`data/sample_dataset/BENCHMARK_COVERAGE_REVIEW.md` — read this before designing any new benchmark iteration. `data/sample_dataset/CORPUS_COVERAGE_AUDIT.md` — read this before considering any further corpus change.** Two separate living documents now, by design (see the "Two separate workstreams" note below). Remaining top-priority findings:

*Benchmark side:*
1. A deliberate **Explicit-Business-Identifier** positive case — still a named Recommendation-Coverage scenario with zero representation. Top priority on this side.
2. A genuinely-harder **Broken Thread Headers follow-up**: degraded/generic subject line *plus* stripped body, to isolate the semantic floor the 2026-08-03 iteration didn't fully isolate.
3. **Ambiguous Wording as its own independent recommendation-coverage axis** — distinct from the disambiguation-across-multiple-tickets cases already covered.

*Corpus side (see `CORPUS_EXPANSION_ROADMAP.md` for full detail):*
4. Stage 2 (deepen thinnest customer `harborview_bh`), Stage 3 (long-running ticket for a customer other than `pinehill_ophtho`, which currently owns both existing long threads), Stage 4 (a new structural-difficulty construct), Stage 5 (internal-note realism) — all proposed, **none approved yet**. Per the user's explicit direction (2026-08-03), Stage 0+1's results are being treated as a stable baseline first; Stages 2-5 are reviewed from that baseline, not committed to upfront.

**Two separate workstreams, as of 2026-08-03**: benchmark expansion (new eval queries against the existing corpus) and corpus expansion (changing `seed_data.py` itself) are now tracked as explicitly distinct efforts, each with its own audit document, because they have different regression-safety profiles — a new eval query can never affect any other query's result (safe by construction), but a corpus change can (a new ticket grows a customer's candidate pool; enriching an existing ticket changes what gets embedded for it) and therefore always requires a full benchmark re-run before being accepted.

**Completed 2026-08-03, in order: Thank You/Appreciation → Informational Email → Broken Thread Headers → Archive/No-Action → Corpus Coverage Audit (Stage 0 + Stage 1)**, all following the same 4-deliverable process:
- **Thank You/Appreciation** (`thankyou_*`, 8 cases): all 6 RCM services, both RESOLVED and CLOSED tickets. 7/7 clear-case accuracy. The 1 hard case (`thankyou_ambiguous_lowcontent`) failed as designed — traced to reranker-signal collapse on zero-topical-content queries. Report: `eval_reports/2026-08-03_thank_you_appreciation.md`.
- **Informational Email** (`info_*`, 8 cases): all 6 RCM services, including a CLOSED terminal-status case. 7/7 clear-case accuracy. The 1 hard case (`info_ambiguous_archive_boundary`) failed for a more nuanced reason: a confident, content-grounded choice that didn't match a ground truth later found to be under-specified. Report: `eval_reports/2026-08-03_informational_email.md`.
- **Broken Thread Headers** (`broken_headers_*`, 8 cases): all 6 RCM services, every quote/forward pattern `recommender/preprocessing.py`'s stripping logic handles, each body verified against real `clean_text()` output before being finalized. **8/8 passed** — the first iteration with zero failures, though the hard case's rigor came with a caveat (subject-line matching did most of the work). Report: `eval_reports/2026-08-03_broken_thread_headers.md`.
- **Archive/No-Action** (`archive_*`, 8 cases): a brand-new cold "no action needed" email deciding attach-vs-archive from scratch. 6/7 clear-case accuracy at the time — **the benchmark's first clear-case failure** (`archive_c4_claims_selfresolved`), traced to confirmed `qwen3:4b` non-determinism (not a defect), reported as-observed rather than hidden by re-running. Report: `eval_reports/2026-08-03_archive_no_action.md`.
- **Corpus Coverage Audit → Stage 0 + Stage 1** (3 + enrichment of 7 tickets): a from-scratch, quantitative audit of the corpus *independent of the benchmark* (`CORPUS_COVERAGE_AUDIT.md`) found 3 real cross-customer lookalike pairs already in the corpus but never tested (Stage 0, zero corpus risk), and that 18% of tickets had no agent reply ever recorded (Stage 1, enriched the 7 non-frozen ones — `PM1`/`PM7` deliberately excluded, see §6a). Full re-run: **48/48 clear-case accuracy, zero regression**, and `archive_c4_claims_selfresolved` now passes. A different hard case (`info_ambiguous_archive_boundary`) produced a *third* different wrong answer across observations, extending the non-determinism finding to the **reranker itself**, not just the LLM. Report: `eval_reports/2026-08-03_corpus_stage0_stage1.md`.

Headline numbers for all five logged in `data/sample_dataset/EVAL_HISTORY.md`. **Process note**: each iteration produces four deliverables — (1) new eval cases (and/or corpus changes) (2) an evaluation report (overall + category-specific metrics), (3) a failure analysis tracing any failed case to its actual layer — or, when nothing failed, an honest look at whether a "hard" case was actually as rigorous as designed, (4) an `EVAL_HISTORY.md` entry. **When a clear case fails, don't re-run until it passes and report only that — report the observed result, then trace root cause independently.**

**Dashboard wired to real eval data (2026-08-03).** The Evaluation page (`dashboard/src/routes/EvaluationPage.tsx`) and its backing endpoint (`GET /api/evaluation/status`, `api/services/evaluation_service.py`) read every `data/sample_dataset/eval_results_*.json` file, summarize each via the shared `recommender/eval_reporting.py` module (also used by `scripts/run_eval.py`'s console output, so the two can't drift apart), and show headline stat tiles, a per-category breakdown, hard-case results, a full per-query table, and a run-history trend. Only runs saved with `--output` show up — see §6a above for exactly how.

**Proposed, NOT yet implemented or approved**: "Iteration — Noisy/Informal Writing Style," 9 queries testing spelling mistakes, lowercase, missing punctuation, texting abbreviations, and grammar mistakes as isolated (not combined) variations, each against a ticket not previously used in the benchmark. Full query text exists in conversation history but **has not been written into `eval_queries.py` yet**. This is a 4th, orthogonal axis (surface-form robustness) that doesn't live inside any of the 3 named benchmark dimensions — decide whether it becomes a standing 4th dimension or a cross-cutting modifier before implementing it.

**Next action, if resuming this thread**: per the user's explicit direction, treat the current state (56 queries, 100% clear-case accuracy, 158-interaction corpus, zero regression) as a **stable baseline** and decide whether Stage 2 (or another corpus stage) is actually needed before proceeding — don't default back into another benchmark iteration or another corpus stage without that review.

## 7. Manager feedback loop (built, working, separate from the eval benchmark)

`recommendation_feedback` table (`recommender/models.py`) + `POST /api/feedback` / `GET /api/feedback` + Accept/Reject buttons on the Playground's recommendation card (reject can optionally specify the actually-correct ticket). This is the **production-style** ground-truth mechanism (real manager verdicts on real traffic over time), distinct from the eval benchmark (**synthetic**, known-answer regression queries run on demand). `scripts/compute_metrics.py` computes accuracy/precision/recall/F1/confusion-matrix and a confidence-calibration check from whatever's been recorded in that table — useful once there's real usage history, not a substitute for the eval benchmark.

## 8. Known limitations (reported, not silently patched)

- **Non-determinism at temperature 0, now confirmed at two separate stages, not one.** `qwen3:4b`'s decision layer has shown non-determinism across identical re-runs — expected on a small local "thinking" model, not a bug. Originally observed only on hard/disambiguation cases; confirmed 2026-08-03 (`archive_c4_claims_selfresolved`) that it can also flip a *clear*-difficulty case when retrieval/reranking hand the decision layer a rank order that doesn't cleanly favor the correct candidate. **Further confirmed the same day** (`info_ambiguous_archive_boundary`, see `data/sample_dataset/eval_reports/2026-08-03_corpus_stage0_stage1.md`) that the **reranker's own cross-encoder scores** — not just the LLM's conclusion — vary run-to-run on near-zero-content queries with multiple similar candidates: three separate observations of that one query produced three different final answers. Treat any single run of this query *shape* (low content, multiple structurally-similar candidates) as one noisy sample, not a stable measurement.
- Reranker (`BAAI/bge-reranker-base`) runs on CPU (`config/recommender_config.yaml`); GPU is available and unused if latency becomes a priority.
- The LLM decision step is the dominant latency cost (often 30s-3min locally) due to qwen3's default chain-of-thought "thinking" mode; never disabled, since it may matter for decision quality on hard cases — an open, un-executed option if speed becomes the priority.
- The dashboard's Evaluation page (`/api/evaluation/status`) is wired to real data from `data/sample_dataset/eval_results_*.json` — see §6d. Recall@K/MRR/NDCG against a large *labeled ground-truth* set (true benchmark-scale model comparison across embedding models, distinct from this 56-query regression suite) is still not built — there's no such labeled dataset yet.
- The corpus's long-running-conversation coverage (tickets with many interactions spanning weeks) is concentrated in a single customer (`pinehill_ophtho`, per `CORPUS_COVERAGE_AUDIT.md` Dimension 5) — any pipeline behavior specific to long threads has only ever been exercised against that one customer's data.

## 9. If you're a new Claude session picking this up

Read this file fully, then check `git log`/`git status` for anything that's changed since. The single most likely next task is finishing §6d above. Don't re-litigate the locked architecture (§2) or propose redesigning `recommender/` — that decision was made deliberately and repeatedly reconfirmed. Don't touch the legacy `app/`/`generation/`/`pilot/` track unless explicitly asked.
