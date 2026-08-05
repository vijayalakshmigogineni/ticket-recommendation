# AI Recommendation Service — End-to-End Architecture & Integration Compliance Review

**Scope**: `recommender/` (the recommendation pipeline) and `api/` (its HTTP surface) — the two packages that constitute the "AI Recommendation Service" implementation. `dashboard/` (the internal debug UI) and the dataset/eval scripts (`seed_data.py`, `eval_queries.py`, `compute_metrics.py`, `run_eval.py`) are excluded — they are explicitly self-declared debug/dev tooling, not production integration surface. `scripts/init_db.py` and `scripts/run_indexing.py` are included, since they implement the offline-indexing half of the architecture.

**Compared against**: `RECOMMENDATION_SERVICE_INTEGRATION_CONTRACT.md`, the two architecture diagrams, and `RECOMMENDATION_SERVICE_INTEGRATION_DECISIONS.md` (the answered Q&A). No code changes made. No fixes proposed. This is an assessment only.

---

## Executive summary — the one finding everything else follows from

**This implementation was built and validated entirely as a standalone prototype, against its own self-invented schema and its own self-owned database — it has never been pointed at, or built against, the actual production data model or integration contract.** Every module inherits consequences from this one fact. Five concrete, high-severity findings fall out of it directly:

1. **No `interaction_id`-based entrypoint exists anywhere.** Per the Contract and Decisions #2/#4, `POST /recommend-ticket` is called by Main App *after* it has already created the `Interaction` row — the AI Service's real job is to look up that existing row and reason over it. This codebase's actual entrypoint (`IncomingEmail` / `RunRequest`) instead takes raw subject/body/sender-email fields directly as request payload. There is no code path anywhere that accepts an `interaction_id` and reads the corresponding row from a shared database.
2. **`POST /index-interaction` does not exist.** Decision #2 requires the AI Service to expose this as a real endpoint, called asynchronously whenever Main App creates/updates an interaction. The only indexing mechanism that exists is `scripts/run_indexing.py` — a manually-run batch job that full-scans for pending rows. No HTTP route, not even a stub, exists under this or any similar name.
3. **The deterministic auto-attach short-circuit excludes terminal (RESOLVED/CLOSED) tickets — directly contradicting Decision #5** ("all statuses... will be equally eligible"). This is not a gap, it's an active contradiction of an explicit decision, isolated to `thread_detection.py`.
4. **Embeddings are stored as a column on the same table as the content**, not in a separate, AI-owned table. Diagram 2 explicitly models `interaction_embeddings` as its own table under "AI TABLES (Used by AI Service)," distinct from the Main-App-owned `interactions` table. This codebase's `Interaction.embedding` column lives directly on the one table that plays the role of both.
5. **There is no authentication anywhere.** Decision #1 confirms the AI Service authenticates like any other client, via Bearer JWT. `api/main.py`'s own docstring self-describes this build as "No auth: trusted, local-only engineering tool" — every route is open, by explicit design, for the debug tool this was built as.

None of the above are implementation bugs in the sense of "wrong code" — the code does what it was scoped to do (a correctness-verification prototype over a small hand-authored dataset, which was the original, explicit brief). They are compliance gaps relative to a production integration contract this codebase predates and was never measured against until now.

---

## Module-by-module review

### `recommender/config.py`
- **Consistent with production?** Partially. Sensible settings layer, but `database.url` points at a standalone, AI-owned Postgres instance (port 5433 in this environment) rather than the shared copy-of-production database Decision #11 specifies.
- **Assumptions**: that the service owns and fully controls the schema of the one database it points at.
- **Correct?** No — contradicts Decision #11 (shared DB) and Decision #6 (a third Alembic chain *in that same shared database*).
- **Violates production architecture?** By omission — never designed against a shared-DB model at all.
- **Missing for production integration**: any notion of which Alembic chain this service's own tables belong to; any config for JWT/service-account credentials.

### `recommender/db.py`
- **Consistent?** Internally fine; inherits config.py's finding.
- **Assumptions**: that `Base.metadata` should include every table this service touches — production tables and AI-owned tables alike, undifferentiated.
- **Correct?** No — the integration architecture requires a hard ownership line: Main App owns/migrates Client/Ticket/Interaction/User; only the AI's own two new tables belong to this service's migration chain.
- **Violates?** Structurally, yes — no separation exists between "tables I read" and "tables I own."
- **Missing**: a read-only connection mode for production-owned tables, distinct from a migration-capable connection for the AI's own tables.

### `recommender/models.py` — highest-impact single file
- **Consistent?** No, substantially. Point-by-point:
  - `Customer` ≈ production's `Client`, but missing `account_manager_id`, `is_active`. Correctly avoids modeling an individual sender as its own entity — genuine, confirmed alignment with §12.7.
  - `Ticket.status` enum values (`OPEN/IN_PROGRESS/PENDING/WAITING_FOR_CLIENT/RESOLVED/CLOSED`) **exactly match** production's real `ticket_status_enum` — a genuine, confirmed point of correctness. `category` as a free string similarly mirrors production's unconstrained `ticket_type`. But there's no `agent_id`, `current_priority`, `closed_by`, or any of the escalation-derived fields.
  - `Interaction.interaction_type` has 4 invented values (`CUSTOMER_EMAIL`, `AGENT_REPLY`, `INTERNAL_NOTE`, `SYSTEM_EVENT`) — production's 6 real values are `EMAIL, REPLY, INTERNAL_NOTE, ATTACHMENT, SLA_PAUSED, SLA_RESUMED` (direction, e.g. agent vs. customer, is a *separate* column in production, not baked into the type). `SYSTEM_EVENT` doesn't exist in production at all. No `direction`, `parent_interaction_id`, or `payload` (JSONB) column exists here — content lives in flat `raw_content`/`clean_content` string columns instead.
  - `RecommendationFeedback` is this codebase's own invention, intended to play the role of `recommendation_logs`, but it denormalizes a full copy of the email (subject/body/sender_email) rather than referencing a real `interaction_id` — because no real `interaction_id` concept exists anywhere to reference (see Executive Summary #1).
- **Assumptions**: that a simplified 3-4-entity schema is sufficient to stand in for the real 15+-entity production schema.
- **Correct?** No.
- **Violates?** By replacement, not contradiction — it's a different, self-contained schema, not a modification of production's.
- **Missing**: `payload`/JSONB content modeling, `direction`, `parent_interaction_id`, any table-ownership/chain separation.

### `recommender/ollama_client.py`
- **Consistent?** Yes — no production-app dependency at all; talks only to Ollama, which both diagrams describe as an independent, shared model-serving layer.
- **Assumptions**: an Ollama endpoint is reachable at a configured host. Matches both diagrams.
- **Correct?** Yes.
- **Violates?** No.
- **Missing**: nothing required by the diagrams.

### `recommender/preprocessing.py`
- **Consistent?** Partially. The text-cleaning logic itself (HTML stripping, quoted-history/signature removal) doesn't contradict anything in the Contract. But `preprocess_incoming_email(subject, body, sender_email)` assumes a single flat body string handed directly to it.
- **Assumptions**: that "the email body" is always one string. Production's real `Interaction.payload` shape is JSONB and **varies by `interaction_type`** — `EMAIL` carries separate `body`/`html_body` fields, `REPLY` carries a `message` field instead of `body` at all.
- **Correct?** No — the two real payload shapes aren't both accounted for.
- **Violates?** No direct contradiction, just an unmodeled case.
- **Missing**: an adapter from `Interaction.payload` (branching on `interaction_type`) into this function's flat signature. Nothing in the codebase performs this mapping today.

### `recommender/customer_identification.py`
- **Consistent?** Yes, and notably well — the exact-match-on-sender-address mechanism mirrors production's real, documented lookup direction (§12.7: every client shares one inbox, so only the sender side distinguishes them) almost exactly.
- **Assumptions**: `Customer.inbox_email` is unique and pre-lowercased — matches production's real `clients.inbox_email` constraint.
- **Correct?** Yes, as logic. Pointed at the wrong table for a real integration (this codebase's own `Customer`, not production's `clients`) — but the *mechanism* is correct and could be re-pointed without changing its logic.
- **Violates?** No.
- **Missing**: nothing algorithmic; only the data source needs to change in a real integration.

### `recommender/thread_detection.py`
- **Consistent?** The matching algorithm (`conversation_id → in_reply_to → references`, first hit wins) matches production's real `find_thread_root` walk order exactly — genuine alignment. But:
- **Violates production architecture — confirmed, direct contradiction of Decision #5.** `_non_terminal_ticket_for_interaction` explicitly excludes `TERMINAL_TICKET_STATUSES` (RESOLVED, CLOSED) from auto-attach eligibility. Decision #5 states all statuses, explicitly including reopening a closed ticket, must be equally eligible.
- **Also in tension with Decision #3**: this module runs as the pipeline's *primary*, load-bearing first gate (`pipeline.py` returns immediately on a match), whereas Decision #3 frames the AI Service's own thread-detection as an optional, removable safety-check layer, since Main App is expected to have already ruled this out before ever calling the recommendation endpoint.
- **Assumptions**: that this service is responsible for primary thread-matching at all.
- **Missing**: any accommodation for the reopening-a-closed-ticket case at this layer.

### `recommender/retrieval/keyword_search.py`, `ann_search.py`, `hybrid.py`
- **Consistent?** The retrieval *mechanism* (customer-scoped keyword + ANN, merged via RRF) matches diagram 1's "Hybrid Retrieval" box closely. Correctly performs **no status filtering** — which, on reflection, is actually the *correct* half of Decision #5 compliance (unlike thread_detection.py, these queries don't exclude RESOLVED/CLOSED tickets' interactions).
- **Assumptions**: that the embedding vector and searchable content live as columns on the same `interactions` row being queried.
- **Correct?** No — contradicts the read/write ownership boundary. Diagram 2 explicitly separates embedding storage into its own AI-owned `interaction_embeddings` table, precisely so the AI Service never needs schema-level access to a Main-App-owned table.
- **Violates?** Structurally, yes.
- **Missing**: a join-based query against a separate `interaction_embeddings` table (joining back to `interactions`/`tickets`/`clients`), rather than a single-table scan.

### `recommender/retrieval/debug_search.py`
- **Consistent?** Not applicable — explicitly debug-dashboard-only per its own docstring, never called by the real pipeline. No production-integration relevance.

### `recommender/grouping.py`
- **Consistent?** Yes — matches diagram 1 step 6 closely (max/top-k-avg/recency weighted scoring), and correctly performs no status-based exclusion, consistent with Decision #5.
- **Assumptions/Correctness/Violations**: none identified; this module's logic doesn't depend on which underlying schema it's fed.
- **Missing**: nothing required by the diagrams.

### `recommender/context_builder.py`
- **Consistent?** Matches diagram 1 step 7's description (matched interaction + neighbors, literal text, lightweight metadata header) closely — including a genuinely useful, already-present detail: the header includes `Status: {ticket.status.value}`, meaning the LLM *does* see ticket status as visible context even for RESOLVED/CLOSED candidates, which meaningfully supports Decision #5's reopening scenario already.
- **Assumptions**: `_SENDER_LABEL` maps this codebase's own 4 interaction types, not production's real 6 (+9 synthesized). Assumes `clean_content` is a flat string (same root assumption as preprocessing.py).
- **Correct?** No, for the same type-mismatch reason as models.py.
- **Missing**: handling for `ATTACHMENT`/`SLA_PAUSED`/`SLA_RESUMED` interaction rows, and for the 9 synthesized types, none of which map onto this module's label dictionary today.

### `recommender/reranker.py`
- **Consistent?** Yes, functionally — cross-encoder architecture matches. Model choice (`bge-reranker-base`) differs from the diagram's example (`bge-reranker-large`), but the diagram phrases it as an example, and the deviation is self-disclosed in the code's own docstring as a deliberate hardware tradeoff, not an oversight.
- **Assumptions/Violations**: none — this module operates on plain text pairs with zero schema dependency, and is genuinely portable regardless of the other findings in this report.
- **Missing**: nothing.

### `recommender/decision.py`
- **Consistent?** The decision mechanics (structured JSON: should_attach/candidate_index/confidence/explanation) match diagram 1 step 9. The system prompt's scope — deciding attach-or-not only, never re-classifying category — is correctly aligned with Decision #8.
- **Assumptions**: that a `DecisionResult` with no `interaction_id` field is sufficient output.
- **Correct?** No, relative to Decision #7 — logging "the top recommendation + reasoning" implies a real interaction identity to log it against, which doesn't exist here (same root cause as the Executive Summary's finding #1).
- **Missing**: an `interaction_id` field on the output; anywhere upstream that would supply one.

### `recommender/pipeline.py`
- **Consistent?** This is where Executive Summary finding #1 is concretely located: `IncomingEmail` takes raw subject/body/sender_email/threading-header fields directly, with no `interaction_id`-based entrypoint at all.
- **Assumptions**: that the caller will always hand over full email content synchronously, rather than a reference to an already-stored row.
- **Correct?** No, relative to the integration architecture's `POST /recommend-ticket` contract (called *after* Main App has already created the Interaction).
- **Violates?** Yes — this is the central finding of the whole review.
- **Missing**: an `interaction_id`-accepting entry point; a lookup against a shared database's `interactions` table; any outbound call to Main App's own API.

### `recommender/pipeline_trace.py`
- **Consistent?** Same findings as `pipeline.py` (it's a parallel, instrumented orchestration of the same stages) — but explicitly self-declared debug/dashboard-only, so lower stakes than `pipeline.py` itself.

### `recommender/indexing.py` + `scripts/run_indexing.py`
- **Consistent?** No — this is Executive Summary finding #2. `run_indexing` is a full-table batch scan for rows missing an embedding or on a stale model version, invoked manually via a CLI script. Diagram 2 specifies `POST /index-interaction`, an async, per-interaction webhook Main App calls on every create/update.
- **Assumptions**: that indexing can happen as an offline batch sweep rather than an event-driven, per-interaction call.
- **Correct?** No, relative to Decision #2.
- **Violates?** By complete absence, not contradiction — no endpoint exists under this name or any equivalent.
- **Missing**: the entire async/webhook indexing surface; embedding storage in a separate table (same finding as the retrieval modules); filtering keyed to production's real `EMAIL`/`REPLY` type names rather than this codebase's own (Decision #10's embeddable-type list, translated, is `EMAIL` + `REPLY`, which is close in spirit to this module's `EMBEDDABLE_INTERACTION_TYPES = {CUSTOMER_EMAIL, AGENT_REPLY}` but not the same literal values).

### `scripts/init_db.py`
- **Consistent?** No — and this is worth flagging distinctly from the passive gaps above, because it's **actively destructive if ever pointed at a real shared database.** `DROP_AND_RECREATE=1` drops and recreates *all* tables, including ones that would, in a real integration, be owned and migrated exclusively by Main App (Client/Ticket/Interaction/User-equivalents). Even without that flag, `Base.metadata.create_all()` unconditionally attempts to create every table this codebase defines, with no concept of "these three tables are not mine to create."
- **Assumptions**: full, unshared ownership of the target database's schema.
- **Correct?** No.
- **Violates?** Yes, actively — this is the one module in the review that could cause real damage if run against a shared/copied production database rather than a fully standalone one.
- **Missing**: a mode that only manages the AI-owned tables (`interaction_embeddings`, `recommendation_logs`-equivalent) and leaves production-owned tables untouched.

### `api/main.py`
- **Consistent?** No — Executive Summary finding #5. CORS is locked to the dashboard's dev origin (`localhost:5173`), and there is no authentication layer of any kind. The module's own docstring self-describes this as intentional: "Internal debug/evaluation dashboard API... No auth: trusted, local-only engineering tool."
- **Assumptions**: a trusted, single-user, local-only caller.
- **Correct?** No, relative to Decision #1.
- **Violates?** Yes, by explicit design (self-disclosed, not accidental).
- **Missing**: JWT verification; the two endpoints Decision #2 requires under their real names (`/index-interaction`, `/recommend-ticket` don't exist — the closest analogs, `/api/run` and the indexing *script*, differ in both name and calling convention).

### `api/deps.py`, `api/errors.py`
- **Consistent?** Generic FastAPI plumbing (DB session dependency, exception handlers), no production-specific content. `errors.py`'s own docstring repeats the same "trusted, no-auth" framing as `main.py` — internally consistent with itself, inconsistent with Decision #1.
- **Missing**: nothing beyond the auth gap already noted at the app level.

### `api/routers/customers.py`, `tickets.py`, `interactions.py` (+ services)
- **Consistent?** These expose this codebase's own `Customer`/`Ticket`/`Interaction` tables read-only (plus a debug-only customer-creation endpoint). Resource naming drifts from the Contract's real terminology (`customers` here vs. production's `clients`) — cosmetic, but a real terminology mismatch if this naming were ever carried into a real integration.
- **Assumptions**: that this service's own tables are an acceptable stand-in for the real `clients`/`tickets`/`interactions` tables.
- **Correct?** No, for the same schema reasons as `models.py`.
- **Violates?** The customer-*creation* endpoint specifically: in a real integration, client onboarding is `POST /clients` on Main App, owned by Main App — an AI service ever writing to a production-shaped client/customer entity would cross the read/write ownership boundary. Today it only writes to this codebase's own standalone table, so it isn't a live violation yet, but it's a pattern that must not carry forward as-is.
- **Missing**: nothing beyond the schema/ownership points already covered.

### `api/routers/run.py`, `api/services/run_service.py`, `api/schemas/run.py`
- **Consistent?** No — this is the HTTP-layer manifestation of Executive Summary finding #1. `RunRequest` (confirmed directly: `subject`, `body`, `sender_email`, `message_id`, `conversation_id`, `in_reply_to`, `reference_message_ids`, `now`) takes raw email content as request fields; there is no `interaction_id` field anywhere in this schema.
- **Assumptions/Correctness/Violations/Missing**: identical to `pipeline.py`'s entry, since this is purely a thin HTTP wrapper around it.

### `api/routers/search.py`, `feedback.py` (+ services/schemas)
- **Consistent?** `/api/search/vector` is explicitly debug-only exploration, no production relevance. `/api/feedback` is this codebase's own manager-feedback loop — conceptually parallel to `recommendation_logs`' intent, but its actual shape (a denormalized copy of subject/body/sender_email, no `interaction_id` reference) diverges from Decision #7's framing (top recommendation + reasoning, implicitly keyed to a real interaction) for the same root-cause reason as everywhere else: no real `interaction_id` concept exists to key off.
- **Missing**: an `interaction_id` field; alignment with whatever `recommendation_logs`' real schema turns out to be.

### `api/routers/system.py`, `evaluation.py` (+ services)
- **Consistent?** Yes, and out of scope for integration compliance either way — these are purely introspective (status/settings/index-info) or an explicit, self-declared stub (`{implemented: false}`). No claims made that could be non-compliant.

---

## Summary table

| Module | Consistent w/ production? | Violates architecture? | Missing for production integration? |
|---|---|---|---|
| `config.py` / `db.py` | Partial | By omission | Shared-DB model, chain separation |
| `models.py` | No | By replacement | Real entity shapes, `payload` JSONB, `direction` |
| `ollama_client.py` | Yes | No | Nothing |
| `preprocessing.py` | Partial | No | Payload-shape adapter (EMAIL vs REPLY) |
| `customer_identification.py` | Yes (logic) | No | Only the data source, not the logic |
| `thread_detection.py` | Partial | **Yes — contradicts Decision #5** | Reopened-ticket handling; primacy vs. Decision #3 |
| `retrieval/*` (keyword/ANN/hybrid) | Mostly yes | Yes (storage model) | Separate `interaction_embeddings` table |
| `grouping.py` | Yes | No | Nothing |
| `context_builder.py` | Mostly yes | No | Real type/label mapping, attachment handling |
| `reranker.py` | Yes | No | Nothing |
| `decision.py` | Mostly yes | No | `interaction_id` on output |
| `pipeline.py` / `run.py` (API) | **No — central finding** | **Yes** | `interaction_id`-based entrypoint entirely |
| `indexing.py` / `run_indexing.py` | No | By absence | `/index-interaction` endpoint entirely |
| `init_db.py` | No | **Yes — actively destructive if misapplied** | Ownership-scoped schema management |
| `api/main.py` | No | Yes, by explicit design | Auth layer, real endpoint names |
| `routers/customers.py` etc. | No | Not yet (pattern risk only) | Real entity alignment |
| `routers/search.py`, `feedback.py` | Partial | No | `interaction_id` reference |
| `routers/system.py`, `evaluation.py` | Yes (out of scope) | No | Nothing |

No fixes proposed or implemented. This report reflects the codebase as of this review only.
