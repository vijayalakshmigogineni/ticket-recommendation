# Production-Aligned Synthetic RCM Environment — Discovery Checklist

Status: **Discovery — no design decisions made yet.** This document is the
information-collection plan for a scope change: this project is no longer
generating one benchmark dataset for one recommendation model. It is
becoming the **shared synthetic operational environment** multiple
automation projects and AI systems (built by different interns) will treat
as ground truth — populating the real application's PostgreSQL schema as if
it had been operating for months, with research artifacts (benchmarks, eval
sets, ground-truth labels, QA reports) derived from it but kept structurally
separate.

Nothing here proposes a schema, a generation strategy, or a distribution.
Every item below is a question, or a request for an artifact you already
have (schema files, migrations, an ERD, a wiki page). Answer in whatever
form is fastest for you — pasted DDL, a linked doc, a screenshot of an ERD,
or just prose; I'll turn it into something structured either way.

## What we already know (so you don't need to re-explain it)

Earlier in this project you shared a technical reference for the real
`unified-backend`/`shared_models` app, described as unverified and
truncated. From it, and from decisions made since, we already have:

- Sender-based customer identification (`From` address → `Client.inbox_email`), not recipient-based.
- A `clients` table with `name`, `inbox_email`, `account_manager_id`, `is_active`.
- Ticket status has (at least) 6 values: `OPEN`, `IN_PROGRESS`, `PENDING`, `WAITING_FOR_CLIENT`, `RESOLVED`, `CLOSED`.
- No `issue_type` concept in production — category is the only classification axis on a ticket.
- Tickets always originate from an `Interaction`; `ticket_type` was described as a plain unconstrained string.
- No ML/embedding infrastructure exists yet in the real app.

**Phase 1 below asks you to confirm whether this is still accurate and complete, or superseded** — treat everything above as provisional, not settled, since the original reference was explicitly flagged as unverified and truncated.

---

## Phase 1 — Foundation & Scope

*Answer this first — it determines how much of the rest even applies.*

### 1.1 Application purpose & business domain
- **What**: What does the real application actually do, end to end? Ticketing is one piece — what else does it handle? (billing/claims submission, payment posting, client portal, reporting/analytics, EHR/clearinghouse integrations, etc.)
- **Why needed**: Everything downstream (schema, workflows, volumes) is scoped by what the app actually is. Designing for "a ticketing system" when the real app is "a full RCM operations platform with ticketing as one module" produces a synthetic environment that's wrong at the foundation.
- **How it shapes generation**: Determines which entities need to exist at all, and which of the "specialized artifacts" (recommendation benchmark, others) map to which slice of the environment.
- **Mandatory.**

### 1.2 Multi-tenancy / organizational model
- **What**: Is this a single RCM company serving many client medical practices (what we've assumed so far), or a multi-tenant SaaS platform serving many *RCM companies*, each with their own clients? Is there an org/workspace concept above `clients`?
- **Why needed**: Changes the entire schema shape — a single extra tenancy layer affects nearly every foreign key and every "realistic distribution" question later.
- **How it shapes generation**: Determines whether the synthetic environment needs one tenant or many, and whether cross-tenant isolation needs to be modeled.
- **Mandatory.**

### 1.3 Full module/feature inventory
- **What**: A list of the application's major modules/screens/features, even just names (e.g. "Ticketing", "Client Management", "Reporting Dashboard", "Billing", "User Admin").
- **Why needed**: Tells us what other entities (beyond tickets/messages/clients) the synthetic environment needs to populate for other teams' projects to have something to build against.
- **How it shapes generation**: Scopes Phase 2 onward — no point requesting deep schema detail on a module nobody's building against yet.
- **Mandatory.**

### 1.4 Authoritative schema source
- **What**: Is the `unified-backend`/`shared_models` reference from earlier still the right source? Can you provide the **full, untruncated** version — actual schema files, migration history, an ERD export, or direct read access/dump — rather than a pasted excerpt?
- **Why needed**: A pasted, truncated, self-described "unverified" reference is not something to build a shared multi-team environment on. This needs to be a real, checkable artifact.
- **How it shapes generation**: This *is* the target schema the synthetic data must populate — everything in Phase 2 depends on having the real, complete version.
- **Mandatory.**

---

## Phase 2 — Core Schema

*Only after Phase 1 tells us the real scope.*

### 2.1 Complete table definitions
- **What**: Every table: columns, types, nullability, defaults, primary keys, foreign keys, unique constraints, check constraints, indexes. Raw DDL, Alembic/migration files, or an exported schema (`pg_dump --schema-only`) are all fine — prefer these over hand-written prose, since prose transcription introduces drift.
- **Why needed**: This is the literal target the synthetic data must satisfy. Every constraint here becomes a rule the generator must never violate.
- **How it shapes generation**: Directly determines table structure, valid value ranges, and referential integrity rules in the generator.
- **Mandatory.**

### 2.2 Enums / controlled vocabularies
- **What**: Every enum type used anywhere in the schema (ticket status, category, roles, priority levels, channel types, etc.) with its exact member values.
- **Why needed**: Enum drift (our synthetic category taxonomy vs. the real one) has already bitten this project once this session — worth getting authoritative values up front rather than correcting later.
- **How it shapes generation**: Every enum column's sampling distribution is built from this list.
- **Mandatory.**

### 2.3 Entity relationship map
- **What**: If you have an ERD (even a rough one), share it. Otherwise, a written list of "X has many Y", "Y belongs to one Z", "M has many-to-many with N via join table J" for the major entities.
- **Why needed**: Foreign-key cardinality (one ticket has many messages; does a message belong to exactly one ticket, or can it span tickets during reassignment?) determines generation order and referential rules.
- **How it shapes generation**: Determines the dependency order the generator must build entities in (customers → tickets → messages, etc., extended to whatever new entities exist).
- **Mandatory.**

### 2.4 Reference / lookup tables
- **What**: Static vocabulary tables — payer lists, procedure/CPT code sets, denial reason codes, U.S. states, timezones, or anything else that's a fixed lookup table rather than generated data.
- **Why needed**: These need to be *loaded*, not *generated* — synthetic data should reference real lookup values, not invent parallel ones.
- **How it shapes generation**: Becomes static seed data the generator treats as fixed input, not something sampled/varied.
- **Mandatory if such tables exist** — flag if none do.

### 2.5 Required seed data
- **What**: What must exist before the application can function at all — system/admin accounts, default roles, a default "unassigned" bucket, required config rows, feature flags, etc.
- **Why needed**: Distinguishes "data the synthetic environment must always contain regardless of scenario" from "data that varies per generated scenario."
- **How it shapes generation**: Becomes a fixed bootstrap step that runs before any randomized/scaled generation.
- **Mandatory.**

---

## Phase 3 — Entity Lifecycles

### 3.1 Lifecycle of every major entity
- **What**: For each core entity (ticket, client, user, interaction/message, whatever else Phase 1 surfaces): its valid states, valid state transitions, and what triggers each transition (user action, system rule, timeout).
- **Why needed**: "Months of realistic operating history" means entities need to have moved through real state histories, not just landed in a final state. A ticket that's been `CLOSED` for 3 months should have a plausible trail of how it got there.
- **How it shapes generation**: Directly drives the "temporal behavior" work in Phase 6 — state-transition timestamps become the actual history.
- **Mandatory.**

### 3.2 Ticket lifecycle (authoritative version)
- **What**: The full, current, production version of ticket lifecycle — supersedes anything assumed in this project so far (our "Case 1/2A/2B" model was our own construction, not confirmed production behavior). What statuses exist, what each means operationally, who can change status, what's required to close a ticket, can a closed ticket reopen, etc.
- **Why needed**: This is the single most load-bearing workflow in the whole environment — most other projects (including the original recommendation benchmark) key off it directly.
- **How it shapes generation**: Replaces this project's own assumed ticket-lifecycle model with the real one.
- **Mandatory.**

### 3.3 Client hierarchy
- **What**: Can a client have multiple locations/sub-accounts? Multiple billing contacts with different roles? Is there a parent/child organization structure (e.g. a hospital group with multiple practice locations)?
- **Why needed**: Changes the `Customer`/`Client` entity from flat to hierarchical, which affects nearly every downstream volume assumption (tickets per *location* vs. per *client group*).
- **How it shapes generation**: Determines whether "customer" in synthetic data is a single flat entity or a tree.
- **Mandatory.**

### 3.4 User roles & permissions
- **What**: What user roles exist (Account Manager, Supervisor, Admin, billing specialist, etc.)? What can each role do? Is there a client-facing portal with its own user accounts?
- **Why needed**: Realistic "who did what" audit trails and assignment logic both depend on knowing the real role set, not an assumed one.
- **How it shapes generation**: Populates a `users`/`roles` entity set and determines who can plausibly appear as the actor in generated audit/assignment records.
- **Mandatory.**

---

## Phase 4 — Workflows & Business Rules

### 4.1 Communication workflows
- **What**: What channels bring communication in (email only, or also phone/fax/portal upload)? How does email threading actually work in production (References/In-Reply-To headers, subject-line matching, something else)? Can one interaction span multiple channels?
- **Why needed**: This project already spent significant effort on an assumed email-threading model (Case 1/2A/2B) that was never confirmed against real behavior — this is the chance to correct it authoritatively.
- **How it shapes generation**: Directly determines what "broken threading" means in the real system, which is central to any retrieval-style benchmark built on top of this environment.
- **Mandatory.**

### 4.2 Operational / assignment rules
- **What**: How are tickets assigned to a specific Account Manager? Round-robin, specialty/category-based routing, manual assignment, client-to-AM pinning? Can tickets be reassigned, and under what conditions?
- **Why needed**: "Realistic operational data" includes realistic assignment patterns, not random distribution across AMs.
- **How it shapes generation**: Drives the assignment field's sampling logic and the realism of per-AM workload distributions.
- **Mandatory.**

### 4.3 SLA & escalation rules
- **What**: Response-time targets (by category/priority?), what counts as an SLA breach, what happens on breach (auto-escalation, notification, reassignment), escalation chain (who escalates to whom).
- **Why needed**: "SLA activity and escalations" was explicitly named as required synthetic content — can't generate realistic SLA histories without the real rules.
- **How it shapes generation**: Becomes a derived-field generator (breach flags, escalation records) computed from ticket timestamps against real SLA thresholds.
- **Mandatory if SLA tracking exists in the app** — flag if it doesn't yet (still a good synthetic environment to have if it's *planned*, not yet built).

### 4.4 Notifications
- **What**: What events trigger a notification, to whom, via what channel (email, in-app, SMS)? Is there a notification log/history table?
- **Why needed**: Determines whether notifications are a real persisted entity to populate or purely ephemeral/out of scope for synthetic data.
- **How it shapes generation**: If persisted, becomes another entity generated off the same event timeline as tickets/SLA.
- **Optional** — lower priority than 4.1–4.3, reasonable to defer to a later phase of your answers.

### 4.5 Audit logging
- **What**: What actions get audited? At what granularity (every field change, or just major state transitions)? Retention period? Is there a dedicated audit table, or is it reconstructed from other tables' timestamps?
- **Why needed**: "Audit history" was explicitly named as required synthetic content.
- **How it shapes generation**: Determines whether audit records are a first-class generated entity or a derived view over other generated timestamps.
- **Mandatory if a real audit table exists** — otherwise optional/deferrable.

---

## Phase 5 — Supporting Content

### 5.1 Attachments & documents
- **What**: What file types are supported, how are they stored (DB blob, S3/blob storage with a DB pointer, something else), size limits, are they scanned/processed, can a message have multiple attachments?
- **Why needed**: Determines whether synthetic attachments are actual generated files, metadata-only stand-ins, or out of scope entirely.
- **How it shapes generation**: If metadata-only, this is a fast, low-risk addition; if real files matter to downstream consumers, it's a much bigger content-generation problem.
- **Optional for the first pass** — reasonable to defer until the core entities are settled.

### 5.2 Any other entities not yet covered
- **What**: Anything Phase 1.3's module inventory surfaces that doesn't fit the categories above — payment records, claims data, EHR-sync records, invoices, whatever else exists.
- **Why needed**: Catch-all to avoid discovering a whole missing subsystem after design starts.
- **Mandatory to at least list; detail can come later.**

---

## Phase 6 — Scale, Distribution & Temporal Realism

### 6.1 Data volumes & realistic distributions
- **What**: In the real (or realistically-expected) production system: how many clients, how many tickets/day or /month, messages per ticket, active AMs, tickets per AM, etc. Real numbers if you have them (even rough production estimates); target numbers if the app is pre-launch.
- **Why needed**: This project's existing benchmark spec invented its own scale (40 customers, ~200 tickets) with no grounding in real volumes — this is the chance to anchor it to something real.
- **How it shapes generation**: Directly sets the scale parameters for the synthetic environment (this project's `config/generation_config.yaml` becomes real-world-grounded instead of an assumption).
- **Mandatory.**

### 6.2 Temporal behavior
- **What**: What should "months of operating history" actually look like — steady-state volume, ramping growth (as if the client base grew over time), seasonality (e.g. billing cycles, open-enrollment spikes), business-hours-only activity vs. 24/7?
- **Why needed**: A synthetic environment that's supposed to look like "operating for months" needs a real shape to that history, not uniformly-random timestamps.
- **How it shapes generation**: Determines the time-series generation model (flat random vs. a growth/seasonality curve) underlying every entity's timestamps.
- **Mandatory.**

### 6.3 Business constraints & validation rules
- **What**: Field-level validation (formats, required combinations) and cross-field business rules the real application enforces (e.g. "a ticket can't close with an unresolved SLA breach", "a client can't be archived with open tickets").
- **Why needed**: These are exactly the rules a QA gate over the synthetic data needs to check — if the real app would reject a state, the synthetic data shouldn't produce it.
- **How it shapes generation**: Becomes the deterministic QA rule set for the operational-data layer (this project already has a QA-rules pattern from the benchmark work — same concept, wider scope).
- **Mandatory.**

---

## Phase 7 — Shared-Environment Governance (new, implied by the scope change)

*Not on your original list, but directly implied by "single shared source... derived artifacts must remain separate" — needs answering before any physical design.*

### 7.1 Operational vs. research separation mechanism
- **What**: How should "operational" data (mirrors production, shared by everyone) and "research" artifacts (benchmarks, eval sets, QA reports — specific to one project) be kept separate? Options to choose between (or specify another): separate Postgres schemas in one DB, entirely separate databases, a tagging/scoping column, separate instances per project reading from a shared read replica.
- **Why needed**: This is a concrete architecture decision, not a detail — it determines the physical structure of everything built from here on, and it's explicitly the constraint you named ("must remain separate").
- **How it shapes generation**: Determines whether the existing `EvalQuery`/QA-report artifacts from this project's earlier work get migrated into a research-only schema, and how future artifacts should be scoped.
- **Mandatory.**

### 7.2 Other consumers' requirements
- **What**: Who else is building on this shared environment, and what do their projects need from it? Even a one-line description per project ("intern X is building an SLA-breach predictor, needs realistic SLA histories") helps avoid designing something that only serves this project's original recommendation benchmark.
- **Why needed**: A "shared" environment designed by only looking at one consumer's needs isn't actually shared — it's this project's dataset with a new name.
- **How it shapes generation**: Surfaces requirements (entities, volumes, history depth) this project wouldn't otherwise think to ask about.
- **Mandatory if other projects already exist**; optional/deferrable if this project is the first consumer and others are still hypothetical.

### 7.3 Disposition of existing work
- **What**: The benchmark spec, prompt templates, QA checklist, and pilot data already built this session (`docs/benchmark_dataset_spec.md`, `pilot/`, the `generation/` pipeline) — should these be reconciled into the new shared environment as the "recommendation benchmark" research artifact once the operational layer exists, retired, or something else?
- **Why needed**: Avoids either silently abandoning finished work or silently assuming it carries forward unchanged into a differently-scoped project.
- **Mandatory.**

---

## How to send this back

Everything above is designed to be answered **in phase order, incrementally** — Phase 1 alone is enough to start scoping Phase 2's request precisely instead of guessing. Paste, link, attach, or describe in prose, whichever is fastest; exact DDL/schema exports are preferred over hand-transcribed prose wherever you have them, specifically to avoid re-introducing the kind of drift this project already hit once with the truncated schema reference.
