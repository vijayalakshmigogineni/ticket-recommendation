# Benchmark Generation — Execution Roadmap

Status: **Active.** This is the execution plan for turning the three finalized design docs (`benchmark_dataset_spec.md`, `generation_prompts.md`, `generation_qa_checklist.md`) into an actual, frozen benchmark dataset. Those docs specify *what* to generate and *how to validate it*; this doc specifies *what to build and run, in what order, with what gate before moving on*.

**Naming note:** `PROJECT_PLAN.md` uses "Phase 1–10" for the whole project (Dataset Design, Synthetic Dataset Generation, Embedding Model Selection, …). Everything below is execution detail *inside* `PROJECT_PLAN.md` Phase 1 (Dataset Design) and Phase 2 (Synthetic Dataset Generation) — the "Phase" numbers in this doc are a separate, local numbering, not a re-numbering of the project roadmap.

## Overview

| # | Phase | One-line purpose | Gate to pass |
|---|---|---|---|
| 1 | Database & Schema Preparation | Bring `app/` in line with the Category/Issue Type taxonomy | Migration applies cleanly, round-trip insert works |
| 2 | Orchestration Scaffolding & Pilot Manifest | Fix *what gets generated* before generating it | Manifest covers every pilot-recipe target |
| 3 | Pilot Dataset Generation | Execute Templates 1–5 manually per the manifest | Output counts match manifest, all JSON valid |
| 4 | Pilot QA Validation | Run the QA checklist gate over pilot output | Zero unresolved FAILs, agreement rate computed |
| 5 | Pilot Review, Refinement & Prompt Freeze | Human go/no-go on template quality | Explicit sign-off; docs flipped to Frozen |
| 6 | Automated Generation Pipeline Build | Turn frozen templates into a scripted pipeline | Smoke-test batch reproduces pilot quality unattended |
| 7 | Full-Scale Dataset Generation | Run the pipeline to spec scale, in batches | All §1 scale targets hit or justified |
| 8 | Full-Scale QA Validation & Distribution Audit | QA gate + human review at full scale | Zero unresolved FAILs, FLAG queue + 10% sample reviewed |
| 9 | Benchmark Freeze & Release | Lock v1, hand off to Phase 3+ (Embedding Model Selection) | Dataset reproducible from a frozen export |

```
1 Database Prep → 2 Manifest → 3 Pilot Generation → 4 Pilot QA
                                                          ↓
                              6 Pipeline Build ← 5 Review & Freeze
                                     ↓
                    7 Full Generation → 8 Full QA → 9 Freeze & Release
```

Phases 1–5 are the "pilot" milestone the project has been building toward (small, manual, cheap to redo). Phases 6–9 only start once Phase 5 has explicitly signed off — building automation against unstable prompts means rebuilding it later, so this gate is real, not a formality.

---

## Phase 1 — Database & Schema Preparation

**Purpose.** `app/enums.py`/`app/models.py` still reflect the retired 7-category taxonomy (`claim_denial`, `prior_auth`, `documentation_request`, `insurance_verification`, `new_service_request`, `general_enquiry`, `payment_posting`) and have no `issue_type` column — this is the follow-up debt flagged when the docs were realigned. Nothing downstream can generate valid rows until this lands.

**Inputs:** `benchmark_dataset_spec.md` §2 (Category → Issue Type table, the "default v1 controlled vocabulary"); current `app/enums.py`, `app/models.py`, `alembic/versions/817ec074e0f5_initial_schema.py`.

**Outputs / concrete changes:**
- `TicketCategory` enum values replaced with the 6 operational teams: `CLAIMS`, `PAYMENT_POSTING`, `PRIOR_AUTHORIZATION`, `ACCOUNTS_RECEIVABLE`, `ELIGIBILITY`, `CHARGE_ENTRY`.
- New `IssueType` enum — recommend a **single flat enum** (~60 values across all categories) plus a `CATEGORY_ISSUE_TYPES: dict[TicketCategory, list[IssueType]]` lookup used for validation. This matches how `TicketCategory`/`MessageIntent` are already unconstrained relative to each other at the DB level — the category↔issue_type relationship is enforced in code (and by the QA gate), not a DB constraint.
- `Ticket.issue_type: Mapped[IssueType]` column added (non-nullable).
- New Alembic revision (chained off `817ec074e0f5`) covering both the enum value change and the new column. Since no real data exists yet, this can drop/recreate rather than needing a data-preserving migration.
- **Re-examined decision, not a new column:** the previously-flagged "`EvalQuery` needs a field for the attach/no-match business action" is **not actually needed** — `should_match` (bool) + `correct_ticket_id` (nullable) already fully encode it (`should_match=true` → attach; `should_match=false` → no OPEN ticket matches, the `hard_negative` case). Recorded here so this doesn't get carried forward as open debt indefinitely.

**Dependencies:** none — this is the first executable step.

**Success criteria:**
- `alembic upgrade head` applies cleanly against the local `rcm_tickets` Postgres instance.
- A throwaway insert (`Ticket(category=CLAIMS, issue_type=CLAIM_DENIAL, ...)`) round-trips correctly; an intentionally mismatched pair (e.g. `category=CLAIMS, issue_type=AUTHORIZATION_DENIED`) is rejected by the validation helper (not the DB) — confirming Phase 4/8's QA rule check has something real to call.
- No remaining references to the 7 retired category values anywhere under `app/`.

**Artifacts:** updated `app/enums.py`, `app/models.py`; new Alembic revision file; a small `app/validation.py` (or similar) helper exposing `issue_type_valid_for_category()`, reused later by the automated QA gate (Phase 6/8) instead of reimplementing it.

---

## Phase 2 — Orchestration Scaffolding & Pilot Manifest

**Purpose.** `generation_prompts.md` is explicit that category/issue_type/status/difficulty/style must be *orchestrator-assigned*, never left to the generating model, or the spec's distributions silently drift. For the pilot, the orchestrator is a human — but a human still needs a fixed, deterministic assignment plan to follow, not ad hoc choices made while pasting prompts. This phase produces that plan.

**Inputs:** `generation_prompts.md`'s pilot recipe (5 customers, ~25 tickets avg 5/customer range 3–7, ~20 eval queries); `benchmark_dataset_spec.md` §2 category weights, §4 difficulty-tier weights, §5 style-tag distributions.

**Outputs:** a pilot manifest enumerating, before any LLM call is made:
- 5 customer `temp_id`s (`cust_1`…`cust_5`), one explicitly flagged to receive a disambiguation-tier sibling pair (same category, semantically similar issue types).
- Per-customer ticket assignments: `temp_id`, `category`, `issue_type`, `status` — every category appears ≥1×, Claims/Payment Posting somewhat more often (matches their higher spec weight), one sibling pair present.
- Per-ticket target message count (sampled 2–15, avg ~5, per spec §1).
- ~20 eval-query assignments: `difficulty_tier`, target/near-miss/candidate ticket reference(s), independently-sampled `tone`/`length_bucket`/`noise_level` — aim for ≥2–3 per tier so Phase 5's review can judge each tier, not just the average.

**Dependencies:** Phase 1 (the manifest must only reference valid category/issue_type values).

**Success criteria:** manifest fully covers the pilot recipe's counts; every difficulty tier has ≥2 entries; ≥1 disambiguation pair and ≥1 hard_negative near-miss pairing defined; every category appears at least once.

**Artifacts:** `pilot/manifest.json` (or a spreadsheet, if that's easier to hand-edit) + a short README on how to follow it while running Phase 3. Can be produced by a small deterministic weighted-sampling script (removes human sampling bias, cheap to write) or by hand at this scale — either is fine; the manifest's existence is what matters, not how it was produced.

**Open item to resolve here, not defer:** `PROJECT_PLAN.md`'s open question on the "unknown/unidentified customer" fallback needs at least a placeholder decision before Phase 7 (full generation) — for the pilot it can be skipped, but flag it now so it isn't forgotten until full-scale generation is already underway.

---

## Phase 3 — Pilot Dataset Generation

**Purpose.** Execute the 5 templates manually against the Phase 2 manifest — this is the actual "generate the pilot" step the project has been working toward.

**Inputs:** Phase 2 manifest; the 5 prompt templates in `generation_prompts.md`.

**Steps:** Template 1 once (batch of 5 customers) → Template 2 once per customer (5 calls, each batching that customer's ticket assignments) → Template 3 once per customer (5 calls) → Template 4 per eval-query scenario (batchable by customer) → Template 5 per eval query (blind pass, using the anonymized/randomized candidate list convention from the template).

**Outputs (raw, pre-QA):** ~5 customer profiles, ~25 ticket seeds, ~25 message threads, ~20 eval query emails, ~20 independently-judged labels.

**Dependencies:** Phase 2 (manifest must exist).

**Success criteria:** output counts match the manifest; every output parses as valid JSON against its template's schema; `temp_id`s are unique and cross-referenced consistently (e.g. every `ticket_temp_id` in a Template 3 output matches a real Template 2 `temp_id`).

**Artifacts:** raw JSON per template, e.g. `pilot/raw/customers.json`, `pilot/raw/tickets.json`, `pilot/raw/conversations.json`, `pilot/raw/eval_queries.json`, `pilot/raw/labels.json`.

---

## Phase 4 — Pilot QA Validation

**Purpose.** Run the full `generation_qa_checklist.md` gate over Phase 3's raw output: deterministic rule checks (§1–§6), the batch-level statistical tally, and both LLM judges (Judge 1 — ticket/conversation/sibling consistency; Judge 2 — distractor realism).

**Inputs:** Phase 3 raw JSON; `generation_qa_checklist.md`'s rule tables and judge prompts.

**Outputs:** a PASS/FLAG/FAIL verdict per item, with reasons; Judge 1 output per ticket (incl. the sibling-pairing-plausibility answer where applicable); Judge 2 output per distractor; the Template-4-vs-Template-5 agreement diff (this is simultaneously the ground-truth-match check *and* the difficulty-tier-conformance check); the batch-level realized-distribution tally.

**Dependencies:** Phase 3.

**Success criteria** *(the pilot-scale numeric thresholds below are being set for the first time in this roadmap — not previously fixed in the spec/QA docs — adjust if a different bar is wanted)*:
- Every FAIL is either regenerated-and-repassed, or (if the rule itself looks wrong on inspection) escalated to Phase 5 as a template issue rather than silently overridden.
- FLAG rate recorded; treat >40% as a signal the templates need real rework before Phase 5, not just minor tuning.
- **Ground-truth agreement rate** (Template 4's intended `matched_label`/tier vs. Template 5's independently-judged answer) computed — this is the single most important pilot metric. Proposed bar: ≥90% agreement, with every disagreement individually explainable (either a genuine ambiguity worth keeping, or a real generation drift worth fixing).
- Distribution tally computed; no category/tier should sit at zero where the manifest intended ≥1 (pilot scale is too small to expect the tally to hit spec percentages exactly).

**Artifacts:** `pilot/qa_report.json` (verdicts + reasoning per item) and a short human-readable summary table (PASS/FLAG/FAIL counts per artifact type, agreement rate, distribution tally).

---

## Phase 5 — Pilot Review, Refinement & Prompt Freeze

**Purpose.** This is the "review and refine, then freeze" step from the project's original hybrid workflow decision. A human reviews the Phase 4 output — FLAGged items first (highest-value use of review time, per the QA doc's own risk-weighted design), then a smaller random PASS sample — judging realism, diversity, conversation flow, and label quality, and decides whether template wording needs to change.

**Inputs:** Phase 4 QA report + raw pilot data; human judgment.

**Outputs:** one of two outcomes —
- **(a) Templates frozen as-is** — proceed to Phase 6, or
- **(b) A specific, itemized list of wording changes** needed in `generation_prompts.md`/`generation_qa_checklist.md`, triggering a loop back to Phase 3 for a fresh small batch (only re-running what changed, not the full pilot).

**Dependencies:** Phase 4.

**Success criteria:** an explicit, recorded human sign-off — this is a go/no-go gate, not a passive review. Concretely: the Phase 4 agreement rate is judged acceptable; a manual spot-check of a conversation/eval-query sample reads as realistic; no unresolved FAIL pattern points at a systemic template bug.

**Artifacts:** a "Pilot Review Findings" entry in `PROJECT_PLAN.md`'s decision log (consistent with how this project already tracks decisions, rather than a new standalone file); on freeze, the `Status:` line in `generation_prompts.md` and `generation_qa_checklist.md` flips from "Draft — pending pilot validation" to "Frozen (v1)" with the freeze date.

---

## Phase 6 — Automated Generation Pipeline Build

**Purpose.** With templates validated and frozen, build the scripted pipeline that executes them programmatically — the final step of the project's original hybrid workflow ("build the automated pipeline that simply executes those validated prompts repeatedly").

**Inputs:** frozen templates + QA checklist (Phase 5 output); Phase 1's schema/validation helper; an LLM API (Claude API is the natural default given this project's tooling — Messages API with forced tool-use/structured output per template's JSON schema).

**Outputs — a working pipeline with at least these pieces:**
- **Orchestrator module** — implements the stratified sampling logic that Phase 2 did by hand: category/issue_type/status assignment per spec §2 weights + floor, difficulty-tier/style sampling per §4/§5 weights. This replaces the manual manifest process, not just scales it up.
- **Generation module** — wraps each of the 5 templates as a callable function, with retry/backoff and structured-output validation against that template's JSON schema.
- **QA module** — implements `generation_qa_checklist.md`'s rule checks (reusing Phase 1's `issue_type_valid_for_category()` helper), the two LLM judge calls, and verdict aggregation into PASS/FLAG/FAIL.
- **Ingestion module** — maps `temp_id`s to real DB rows (`Customer`, `Ticket`, `Message`, `EvalQuery`) and writes to Postgres, reading each generated object's `production_fields` only — `generation_metadata` is dropped at this boundary, never inserted.

**Dependencies:** Phase 5 — building this against unstable prompts means rebuilding it after every wording change, which is exactly what the pilot was designed to avoid.

**Success criteria:**
- End-to-end run on a small smoke-test batch (e.g. 2 customers) completes unattended and produces pilot-comparable quality (spot-check against Phase 3/4 pilot results).
- QA gate correctly auto-regenerates a deliberately-broken test case (inject an invalid category/issue_type pairing) — confirms the FAIL→regenerate loop actually works, not just that it's described in the QA doc.
- Ingestion round-trips: generate → insert → query back → matches what was generated.

**Artifacts:** a new `generation/` package (orchestrator/generation/qa/ingestion modules) with a CLI entrypoint (e.g. `python -m generation.run --batch-size N`); unit tests for the sampling logic and rule-based QA checks (pure functions — testable without any LLM calls).

---

## Phase 7 — Full-Scale Dataset Generation

**Purpose.** Run the automated pipeline to the spec's full target scale.

**Inputs:** Phase 6 pipeline; `benchmark_dataset_spec.md` §1 scale targets (40 customers, ~200 tickets, ~1,000 messages, ~350 eval queries), §2/§4/§5 distribution targets.

**Outputs:** the full raw dataset, generated in batches — recommend batching by customer cohort (e.g. 5–10 customers per batch, the same granularity the pilot used) so QA can run incrementally rather than as one giant end-of-run step, and so a bad batch is cheap to isolate and regenerate.

**Dependencies:** Phase 6. Also: the "unknown/unidentified customer" open question flagged in Phase 2 must be resolved by now — it can no longer be skipped once real scale is being generated.

**Success criteria:** scale targets met or explicitly documented as an intentional adjustment (40 customers; ~200 tickets at the 65/35 open/closed split; ~1,000 messages; ~350 eval queries); category floor (≥20/category) and difficulty-tier percentages (§4) hit within reasonable tolerance; ≥10 customers carry a valid disambiguation-tier sibling pair.

**Artifacts:** full dataset persisted in the `rcm_tickets` Postgres instance; a per-batch generation log (what was generated, QA verdict counts, regeneration counts) for auditability later.

---

## Phase 8 — Full-Scale QA Validation & Distribution Audit

**Purpose.** The full-scale counterpart to Phase 4 — but since Phase 6's pipeline already runs the QA gate inline per batch, this phase is the *aggregate rollup and human sign-off*, not a from-scratch re-run.

**Inputs:** Phase 7's full dataset + the QA verdicts already recorded per batch.

**Outputs:** a final QA report across the whole dataset; human review of the FLAG queue (front of the queue, per the QA doc's risk-weighted design) plus the 10% random PASS sample called for in the spec's QA note; any final regenerations this surfaces.

**Dependencies:** Phase 7.

**Success criteria:** zero unresolved FAILs; the full FLAG queue reviewed; the 10% PASS sample reviewed with no systemic issue found; final realized distributions (category, issue_type, difficulty tier, style tags) documented against spec targets, with any deltas explicitly justified rather than silently accepted.

**Artifacts:** `qa_report_full.md`/`.json`; a distribution-audit table (realized % vs. target % per dimension), written so it can be dropped directly into the eventual release notes.

---

## Phase 9 — Benchmark Freeze & Release

**Purpose.** Lock the dataset as "Benchmark v1" — the stable input every later project phase (3: Embedding Model Selection, 4: Vector Database, 5: Similarity Search, 6: Evaluation, …) builds against.

**Inputs:** Phase 8 sign-off.

**Outputs:**
- A frozen dataset snapshot (e.g. `pg_dump` or an exported Parquet/CSV set) plus a version tag.
- All four docs (spec, prompts, QA checklist, this roadmap) flipped to `Status: Frozen (v1)` with the freeze date.
- A release note: final counts, realized distributions, and any deviations from the original spec targets.
- `PROJECT_PLAN.md` updated: Phase 1 (Dataset Design) marked complete in the roadmap table; Phase 2 (Synthetic Dataset Generation) marked as the now-active phase.

**Dependencies:** Phase 8.

**Success criteria:** the dataset is reproducible from the frozen export (a fresh restore matches); no further changes to templates/QA rules happen without an explicit version bump (v1.1/v2) — this is exactly what the "default v1 controlled vocabulary, extensible later" framing already built into the spec was for; downstream phases can begin against a stable, versioned dataset rather than a moving target.

**Artifacts:** the DB snapshot/export + version tag; updated `Status:` lines across all four docs; the `PROJECT_PLAN.md` roadmap-table and decision-log updates.
