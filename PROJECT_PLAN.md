# RCM Ticket Recommendation System — Project Plan

Living document. Updated as decisions are made. This is the source of truth for project state (memory holds only the high-level summary).

## Problem

Clients email an RCM organization about existing or new issues. Account Managers manually decide: new ticket / attach to existing ticket / reply / archive. Follow-up emails about existing issues are often misclassified as new tickets, creating duplicates and wasting manager time.

## Scope (deliberately narrow)

Build a **recommendation system**, not an automation system:

> Given a new incoming email, recommend the most likely existing ticket it belongs to, with a confidence score. Manager approves or rejects. No auto-create, auto-reply, or auto-archive logic.

Pipeline (refined): Incoming email → Identify customer (deterministic lookup, not ML) → Fetch that customer's OPEN tickets → Take each ticket's N most recent message interactions (N configurable, default 10) → Embed incoming email → Compare against that filtered message-level embedding pool → Top-K similar messages → Group by ticket_id → Ticket score = MAX similarity among its retrieved messages (baseline; scoring strategy pluggable) → Recommend highest-scoring ticket + score → Manager decision.

## Environment

- Windows 11, VS Code, Python, FastAPI, PostgreSQL
- Local GPU: RTX 3050, 4GB VRAM — fine for inference with small/medium embedding models; likely insufficient for fine-tuning larger models or large-batch contrastive training → use Google Colab for those steps (flagged per-phase below).
- No historical email data available → synthetic dataset required (Phase 1–2).

## Roadmap & Status

| Phase | Title | Status |
|---|---|---|
| 1 | Dataset Design | **In Progress** (spec ✅, schema ✅ + migrated to local Postgres `rcm_tickets`, generation prompt templates ✅; manual pilot generation next) |
| 2 | Synthetic Dataset Generation | Not started |
| 3 | Embedding Model Selection | Not started |
| 4 | Vector Database | Not started |
| 5 | Similarity Search | Not started |
| 6 | Evaluation | Not started |
| 7 | Embedding Model Comparison | Not started |
| 8 | Fine-tuning | Not started |
| 9 | FastAPI Integration | Not started |
| 10 | Production Architecture | Not started |

## Decisions Log

_Format: Phase — Decision — Rationale — Date_

- **Phase 1 — Embedding unit = message-level, aggregated to ticket (Approach B)**, not one-vector-per-ticket and not an evolving summary vector. Rationale: follow-ups usually mirror one specific prior message, not a thread average; message-level preserves that signal and is explainable (can show manager *which* prior email matched). Evolving-summary approach deferred to Phase 10 as a possible later evolution. — 2026-07-22
- **Phase 1 — Search scope = tenant-filtered**: identify customer from incoming email (deterministic, non-ML lookup) → restrict candidate pool to that customer's OPEN tickets only → within each ticket, most recent `MAX_RECENT_INTERACTIONS` messages (default 10, configurable, not hardcoded). Closed tickets excluded from baseline scope (extend later). — 2026-07-22
- **Phase 1 — Ticket scoring = pluggable strategy interface; baseline implementation = MAX similarity.** Confirmed: do not lock in MAX. Strategies to compare later: Max, Average, Weighted Average, Top-k Voting, Reciprocal Rank Fusion. This comparison is itself a research deliverable of **Phase 6 (Evaluation)** — needs the labeled eval set (Phase 1 labeling strategy) to score each strategy against. — 2026-07-22
- **Phase 1 — Sender scope confirmed**: store `sender_type` (client/manager) on every message; baseline comparison pool = client-authored messages only, filterable via config. — 2026-07-22
- **Environment strategy**: VS Code + local RTX 3050 (4GB) is primary/default for all phases except fine-tuning. **Google Colab reserved specifically for Phase 8 (Fine-tuning)**, and optionally for benchmarking larger embedding models in Phase 7 if local VRAM is too tight. Rationale: embedding *inference* (small sentence-embedding models) is cheap and fits comfortably in 4GB; contrastive fine-tuning needs larger batch sizes (more in-batch negatives → better gradient signal) which 4GB can't comfortably give. Colab is treated as an ephemeral training environment only — trained artifacts get downloaded and served locally, never served from Colab itself. — 2026-07-22
- **Phase 1 — Benchmark dataset spec finalized**, written up at `docs/benchmark_dataset_spec.md` (scale, category/intent distributions, 6 difficulty tiers, style variation, ground-truth schema). Ticket corpus and eval-query set treated as two distinct generation targets. — 2026-07-23
- **Phase 1 — Schema implemented** in `app/` (SQLAlchemy 2.0 + Alembic, Postgres via psycopg2): `Customer`, `CustomerEmail` (normalized sender→customer lookup table, unique on `email_address`), `Ticket` (composite index on `customer_id, status` — the pipeline's core filter), `Message` (index on `ticket_id, created_at` for the "most recent N" query; includes reserved-but-unused `claim_number`/`patient_id`/`payer`/`date_of_service`), `EvalQuery` (separate table for benchmark ground truth, not part of the production model). No embedding column yet — deferred to Phase 3/4. Shared `app/enums.py` mirrors the category/intent/difficulty/style vocab from the benchmark spec so generation code and schema can't drift apart. — 2026-07-23
- **Phase 1 — Generation workflow = hybrid, prompts-first**: design the 5 generation prompt templates (customer, ticket seed, conversation, eval query, ground-truth label) → hand-run them through an LLM to produce a small manual pilot (~20–30 tickets, no API pipeline yet) → review realism/diversity/labels → freeze prompts → only then build the automated batch-generation pipeline. Rationale: validates the actual prompts before investing in automation, rather than automating first and discovering prompt problems at scale. Templates written up at `docs/generation_prompts.md`; ground-truth labeling is a deliberately separate *blind* pass (Template 5 doesn't see Template 4's intended answer) so label agreement rate becomes a free QA signal on top of the spec's existing 10% manual spot-check. — 2026-07-23
- **Phase 1 — Automated Generation QA gate designed**, written up at `docs/generation_qa_checklist.md`: every generated item gets a PASS/FLAG/FAIL verdict from a mix of deterministic rule checks (enum validity, referential integrity, leakage-scan, structural ordering), one batch-level statistical check (realized distributions vs. spec targets), and two new LLM judges (ticket/conversation consistency; distractor realism) — deliberately not nine separate judge calls, since most checks are cheaper and more reliable as plain code, and "does ground truth match"/"is the difficulty tier satisfied" reuse the existing Template 5 blind-judge mismatch rather than re-litigating it. FAILs auto-regenerate; FLAGs go to the front of the manual review queue, turning the spec's flat 10% spot-check into a risk-weighted one. — 2026-07-23
- **Phase 1 — Realigned taxonomy + docs to the finalized business workflow.** `docs/benchmark_dataset_spec.md` and `docs/generation_prompts.md` now open with the real AM-first process (informational/general-query emails never become tickets; most ticket follow-ups arrive via automatic email threading with no AI involved; retrieval is only invoked for a new independent email that broke threading and must be checked against OPEN tickets). `TicketCategory` reframed as operational-team ownership (Claims, Payment Posting, Prior Authorization, Accounts Receivable, Eligibility, Charge Entry, weighted 25/18/16/15/14/12) with a new nested **Issue Type** concept (closed enum per category, 8–11 values, default v1 vocabulary — extensible later without changing the template/QA structure). `hard_negative` and `same_customer_disambiguation` tiers kept exactly as designed, just reframed/clarified: hard_negative measures "correctly find no OPEN match" within the in-scope retrieval decision (not a ticket-creation judgment); disambiguation siblings now require same category **and semantically similar** (not identical) issue types, since category alone is now too coarse to guarantee difficulty. Old categories `documentation_request`/`new_service_request`/`insurance_verification`/`general_enquiry` retired — folded into issue types or dropped (general_enquiry → no ticket at all, per the new Case 1). **Follow-up debt**: `docs/generation_qa_checklist.md` realigned to the new taxonomy (2026-07-24, see next entry) — remaining debt is `app/enums.py`/`app/models.py`, which still need a real `IssueType` enum, updated `TicketCategory` values, and an `EvalQuery` field capturing the attach/no-match business-action distinction. — 2026-07-24
- **Phase 1 — `docs/generation_qa_checklist.md` realigned** to the Category/Issue Type taxonomy: category enum list updated to the 6 operational teams; new rule check for issue_type validity; sibling-distinctness check split into a mechanical rule (facts differ) plus a new semantic **Judge 1** question ("sibling pairing plausibility" — same category, similar-not-identical issue type, e.g. claim_denial vs. claim_rejection_clearinghouse is plausible, claim_denial vs. documentation_request_from_payer is not); Judge 1's category-fit question extended to category-*and*-issue_type fit; `hard_negative`/disambiguation distractor rules updated to the issue_type-aware definitions; batch-level statistical check now tallies `issue_type` too. QA architecture unchanged — still 2 judges, same PASS/FLAG/FAIL gate, same rule-vs-judge division of labor. — 2026-07-24

## Open Questions

- **Closed-ticket lookback**: baseline ignores closed tickets entirely (per user decision). Recommend modeling this as `CLOSED_TICKET_LOOKBACK_DAYS = 0` (configurable) rather than a hard exclusion, so "reopen if replied within N days of closing" can be added later without re-architecting. Not yet confirmed.
- **Unknown/unidentified customer fallback**: what happens when the deterministic customer-lookup fails (new sender, forwarded email, shared inbox)? Not yet decided — needs a synthetic-data category in Phase 2 either way.
- **Vector store for MVP**: since retrieval is pre-filtered to one customer's open-ticket messages (small candidate set, likely dozens–low hundreds), a full ANN vector DB may be unnecessary for the baseline — `pgvector` in the existing Postgres instance could suffice with exact cosine similarity over the filtered set. Revisit properly in Phase 4; noted early since it shapes how "modular vector store" should be abstracted.
- **Confidence score calibration**: raw cosine similarity (e.g. 0.94) is not a calibrated probability. "94% confidence" as shown to managers will need calibration work in Phase 6 (Evaluation) before the number can be trusted at face value.
(none currently blocking)
