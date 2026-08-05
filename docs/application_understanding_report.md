# Application Understanding Report

Status: **Verification checkpoint — no design decisions in this document.** Produced after reading `RCM_APPLICATION_KNOWLEDGE_BASE.md` in full, as the sole source of truth for the real application. Purpose: confirm understanding before any synthetic-environment design begins. Where the source document itself flags something as unverified, assumed, or a live-state-only observation, that caveat is carried forward here rather than resolved.

---

## 1. Business domain

A **Revenue Cycle Management (RCM) support ticketing system**. One company (the RCM operator) runs this application to handle inbound support traffic from its own clients — physician practices, clinics, billing departments — about claims, prior authorizations, payment posting, and patient billing. This is **single-tenant from the application's own perspective**: one deployment, one operating company, with `clients` representing that company's customer base (not a multi-tenant SaaS serving multiple RCM operators). This directly resolves a question I'd raised in the earlier discovery checklist.

The core business fact shaping everything downstream: **a client is a company, not a person.** Every client has exactly one shared inbox address; any number of real humans at that company can send mail that lands in one shared pool. There is no per-contact entity at all — if an individual staff member's identity matters, it lives only inside free-text message content, never as a modeled row. Patient-level detail behaves the same way: no patient entity exists; patient references, if present, are free text inside interaction bodies.

Two workflows are bolted together: **triage** (inbound email → shared pool → an agent decides reply-only / attach-to-ticket / create-ticket) and **ticket work-tracking** (once a ticket exists — assignment, replies, notes, attachments, status/priority, two independent SLA clocks, an escalation ownership chain).

## 2. Application architecture

- One FastAPI backend (`unified-backend/`) serves two frontends: a ticket workspace embedded inside a larger Next.js shell (which itself owns auth/RBAC/org admin), and a separate standalone Vite/React ticketing frontend.
- One physical Postgres database (Neon), but **two independently-versioned Alembic migration chains** write to it — `alembic_rbac` (users/roles/permissions/categories) and `alembic_ticketing` (tickets/interactions/SLA/escalation). This is a real architectural seam, not a detail: the two domains evolve on separate schema-history tracks even though they share a physical database and cross-reference each other's tables via plain UUID FKs.
- **Auth is centralized, ticketing is verify-only.** `app.rbac` is the sole JWT issuer (HS256); `app.ticketing` has no login/signup/refresh endpoint of its own, only verifies tokens. The token itself carries the caller's *effective* flat permission list and any ticket-scoped overrides, computed at login/refresh — not re-derived from the DB on every request (a 30-second, per-process, `(user_id, permission_version)`-keyed cache sits in front of that).
- **Real-time delivery is in-process, not brokered.** Notifications push via Server-Sent Events through an in-memory per-process pub/sub keyed on `user_id` — explicitly a single-process assumption (no Redis), the same tradeoff called out for the permission cache. Scaling to multiple workers would need a shared broker; not attempted today.
- **External integrations**: Microsoft Graph for both inbound intake (webhook/poller) and outbound send (`sendMail` API, with a mock provider fallback); a separate, simpler SMTP path (or log-only fallback) exclusively for internal system notification emails (SLA/escalation alerts) — these are two deliberately distinct outbound paths, not one.
- **No ML/embedding/vector/recommendation infrastructure exists anywhere in the real codebase** — confirmed by the source document's own repo-wide search. The only "recommendation"-shaped feature is a deterministic, non-ML thread-matching heuristic (exact `conversation_id`/message-header re-matching), not content similarity. This matters directly for this project's own prior work — see §10.

## 3. Major entities

**RBAC domain**: `users`, `roles`, `categories`, `permissions`, `role_permissions` (join), `audit_logs` (RBAC-native), `user_permission_overrides`, `permission_requests`, `reporting_manager_teams`.

**Ticketing domain**: `clients`, `interactions`, `tickets`, `attachments`, `ticket_relations`, `ticket_audit_logs`, `resolution_slas`, `first_response_slas`, `ticket_escalations`, `escalation_handling_slas`, `sla_policies`, `sla_breach_notifications`, `notifications`. Two more exist but weren't deep-dived in the source document: `ticket_edit_access_requests`, `mail_folders`.

**Not modeled as real entities at all** (worth stating explicitly, since their absence is itself information): no patient entity, no individual client-contact entity, no claim/payer/payment entity — this application tracks *support work about* those things, never the underlying billing data itself.

## 4. Relationships (in my own words, to check understanding)

- A **User** holds exactly one **Role** and optionally one specialization **Category**. Two independent self-referencing reporting lines exist on `users` (`manager_id` → an Account Manager, `teamlead_id` → a Team Lead) plus a third, separate many-to-many relationship (`reporting_manager_teams`, Account Manager ↔ Category) that layers an *optional* HR responsibility onto an Account Manager without being a role or implied by holding one. A fourth, wider-still relationship — any Account Manager may hand ticket work to any Team Lead company-wide — exists purely as a business rule in the assignment/transfer code, with no dedicated table at all.
- A **Client** (company) is owned by exactly one Account Manager and has exactly one `inbox_email`.
- An **Interaction** is the single, polymorphic timeline row for every email, reply, internal note, and attachment event — inbound or outbound. It optionally belongs to a **Ticket** (NULL until triaged/promoted) and optionally to a **Client**; it threads to other interactions via `parent_interaction_id`/`conversation_id`/`message_id` matching, independent of ticket assignment.
- **A Ticket cannot exist without a founding Interaction** — there is no path in the codebase to create a "blank" ticket. This is a hard generation-order constraint, not a preference.
- An **Attachment** belongs only to an Interaction, never directly to a Ticket — reaching "this ticket's attachments" always means joining through its interactions.
- **ResolutionSLA** is 1:1 with a **Ticket** for its whole lifetime. **FirstResponseSLA** is 1:1 with a thread-*root* **Interaction**, not the ticket — which is why a ticket itself carries no "time to first response" column of its own; that measurement belongs to the pre-ticket mail item.
- **TicketEscalation** sits on top of, but never mutates, ResolutionSLA's own clock fields — a separate ownership hand-off chain. **EscalationHandlingSLA** sits on top of *that* again, and — as of a 2026-07-20 redesign — is now explicitly a **dual-write mirror**, not the authoritative source for stage/timing; the real stage counter and clock-restart logic live directly on `ticket_escalations` and `resolution_slas`.
- **SLAPolicy** is a small, global, priority-keyed config table (4 rows) — not owned by any ticket, client, or category.
- **TicketRelation** is a symmetric, purely manual "these two tickets are related" link (one relationship stored as two mirrored rows) — the closest thing to an existing recommendation feature, and it's entirely human-authored.
- The RBAC permission system (roles/permissions/overrides/requests) is orthogonal to all ticketing business content — it governs who may see or do something, never the business data itself.

## 5. Business workflows (as I understand them)

**Inbound email intake**: Graph delivers a message → duplicate check on `message_id` → client resolution by matching sender/recipient against `clients.inbox_email` (unmatched mail routes to Site Lead rather than being rejected) → deterministic thread match (`conversation_id` → `in_reply_to` → `references`, walked to the true root) → if matched onto an already-ticketed thread, auto-attached, done, no further steps; if not, a new pool Interaction is created (`ticket_id=NULL`, `status=PENDING`) and a First Response SLA clock starts → the item sits in the shared pool until an agent acts (reply-and-archive / attach-to-existing-ticket / create-ticket). Creating a ticket copies the founding interaction's client onto the new ticket, moves *every other* interaction already on that same thread onto the new ticket in one batch (not just the one clicked), completes the First Response clock with reason `TICKET_CREATED`, and starts the Resolution SLA clock.

**Ticket status**: `OPEN → IN_PROGRESS → PENDING → WAITING_FOR_CLIENT → RESOLVED → CLOSED`, explicitly **not** a strict linear path — a ticket can revisit several of these before closing. `WAITING_FOR_CLIENT` pauses the Resolution SLA clock; anything else resumes it. `RESOLVED` does **not** stop the clock — only the dedicated `CLOSED` action does (the generic status-change endpoint explicitly refuses to set `CLOSED` directly). `CLOSED` blocks nearly everything except Reopen, which resets to `OPEN` and never resurrects the completed SLA clock or recreates an escalation.

**Priority**: `LOW/MEDIUM/HIGH` are human-selectable; `CRITICAL` is intended to be system-set only, exactly once, the moment a ticket's first escalation is created, and never reverts on its own — though §19.2 of the source flags a (project-memory, not re-verified-today) confirmed gap where the manual change-priority path had no enforcement blocking a human from forcing or reversing it.

**Escalation**: triggered by a Resolution SLA reaching the 150%-elapsed (`ESCALATED`) threshold, or a manual escalate action. Starting level is *relative to whoever currently owns the ticket* (one level above them, since re-notifying the current owner achieves nothing) and walks `TEAM_LEAD → MANAGER → SITE_LEAD` until it finds a level with at least one real owner. Creating an escalation also bumps the ticket to CRITICAL and computes an acknowledgment window from the *original* (pre-CRITICAL) priority's policy. Acknowledging by itself only stops the ack-timeout; only actual acceptance (via assignment/claim, or the dedicated confirm-assignment action) restarts the Resolution SLA clock at a fresh, stage-scoped window and starts the handling-stage clock. An unacknowledged escalation auto-advances a level when its ack window lapses; an accepted-but-not-resolved one advances again when its handling-stage window lapses. Closing happens only when the Resolution SLA clock itself completes.

**The escalation freeze**: while a ticket has an active, not-yet-accepted escalation, *every* actor — including supervisors — is blocked from acting on it, since every possible owner of that escalation is itself a supervisor. This is wired into note/reply/status-change, but §19.2 flags (again, as unverified project memory) that close/reopen/attachment-upload don't pass the repositories needed to run this check at all.

**Assignment vs. transfer are two different rule sets for two different moments**: the ticket-creation-time "Assigned To" picker is narrowly category/ownership-scoped per role; reassigning an *existing* ticket (`transfer_agent`) uses a wider, differently-shaped eligibility rule — most notably, any Account Manager/Site Lead/Super Admin may hand a ticket to *any* Team Lead company-wide, unconditionally, not scoped to matching category. This is stated explicitly as a deliberate business rule, not an oversight.

**Notifications and audit logging are both pure side effects** of the workflows above — nothing independently authors a notification or an audit row; they're always triggered by some other action (status change, SLA threshold crossing, escalation event, permission change, etc.), each with its own defined recipient-resolution rule.

## 6. Business constraints

- No FK/CHECK constraint ties `Ticket.ticket_type` to `categories` at all — only a frontend dropdown enforces the 7 canonical values; the schema itself accepts any string up to 50 characters.
- No `IssueType` concept exists anywhere — category is the only classification axis on a ticket. (This directly confirms a decision this project already made independently, before this document existed.)
- Real validation is layered unevenly: Pydantic field-length constraints exist at the API boundary (titles, messages, notes), but **no custom cross-field validators exist on any Ticket/Interaction/Attachment/Client schema** — the actual business rules (permission gates, ownership checks, escalation freeze, assignment eligibility) live in the service layer, not the schema layer.
- Real, DB-enforced invariants are a short, specific list: at most one non-CLOSED escalation per ticket; at most one "open" handling-SLA row per escalation; at most one active draft interaction per (thread, agent); global uniqueness on `message_id`/`inbox_email`/role name/permission name/category name; true 1:1 uniqueness on `resolution_slas.ticket_id` and `first_response_slas.interaction_id`.
- **Generation-order constraint**: a ticket cannot exist before its founding interaction. Any synthetic generator must build interactions first.
- Attachment limits: max 10 files/upload, 25MB/file, an explicit allow-listed extension/MIME set.
- A specific, named list of ticket fields are always system-derived (never human-typed): `ticket_id`, `version`, timestamps, `current_status` (always starts OPEN), `created_by`, `client_company_id` (copied from the founding interaction), `client_id` (always NULL), `closed_at`/`closed_by`, CRITICAL priority, `custom_fields` (always `{}` in practice).

## 7. Core operational data (accumulates as the business "runs")

`clients`, `interactions`, `tickets`, `attachments`, `ticket_relations`, `resolution_slas`, `first_response_slas`, `ticket_escalations`, `notifications`, `ticket_audit_logs`, `audit_logs` (RBAC-native), `user_permission_overrides`, `permission_requests`.

I'm placing `users` here too, but with a caveat noted in §10 — it has reference-table-like stability (small, slow-changing roster) that sits uneasily alongside high-volume operational data like interactions.

## 8. Reference / seed data (small, fixed, rarely changing)

`categories` (7 fixed rows, fixed UUIDs), `roles` (6 fixed rows), `permissions` (51 fixed rows), `role_permissions` (the grant matrix — changes only when RBAC policy itself changes), `sla_policies` (4 rows — though see §10, this one is a partial exception), `reporting_manager_teams` (small, assignment-style, not volume-scaling data).

## 9. Derived / system data (computed, non-authoritative, or a side-effect ledger rather than an independently meaningful business record)

- The explicitly-named query-time-only Ticket fields that must **never** be modeled as stored columns at all: `is_escalated`, `escalation_level`, `escalation_status`, `escalation_ack_due_at`, `is_escalation_owner`, `escalation_pending_acceptance`, `resolution_sla_tier`, and the five denormalized `*_name` fields, plus `related_tickets`.
- `escalation_handling_slas` — a real, persisted table, but explicitly described as a "dual-write mirror only" as of the 2026-07-20 redesign; the authoritative stage/timing data lives on `ticket_escalations`/`resolution_slas` instead. Generating this table's rows to *look* consistent with the authoritative fields, without treating it as a source of truth, seems like the right read — flagged in §10 as worth confirming rather than assumed.
- `sla_breach_notifications` — an idempotency ledger, not a business record with independent meaning; exists purely so the sweep doesn't re-fire the same threshold twice.
- `attachments.scan_status` — a confirmed inert stub, always `"pending"`, never read or written by any code path. Functionally vestigial rather than "derived," but not a real signal either way.
- `notifications` — persisted, but 100% a side effect of other events; nothing independently authors one.

## 10. Ambiguities and missing information

I'm splitting these into three groups: what the source document itself already flags (I'm not re-deriving these, just carrying them forward), what I'm additionally surfacing from my own reading, and the one question specific to this project's own prior work.

### Already flagged by the source document itself (§21, §19) — restating, not resolving
- No real scale/volume numbers exist anywhere to anchor client count, tickets/client, messages/ticket, or users/role.
- No real category/priority/status distribution weights exist.
- Time span to simulate (single snapshot vs. multi-month history) is unspecified.
- Whether SLA/escalation state needs to exist in the synthetic environment at all depends on who's consuming it — not yet known.
- Whether to model the four confirmed-but-unverified enforcement gaps (§19.2: CRITICAL-priority reversal, `manual_escalate` missing an ownership check, three call sites skipping the escalation freeze entirely, an acknowledge-without-assign stall state) as *present* or *fixed* — the source document itself says this is 9-day-old project memory, not re-verified against current code, and a remediation plan existed but wasn't confirmed implemented.
- The live `sla_policies` MEDIUM row's actual current values are unknown even to the source document's author — described as having gone through at least three undocumented edits (migrated `2880/7200` → an earlier unlogged `20/20` → a 2026-07-13 demo edit to `2/2` → possibly, but not confirmedly, reverted back to `20/20`). This is a live-database fact no static document can resolve.
- Whether synthetic users need real, working login credentials.
- PHI/compliance posture for generated content (no real PHI/company identities — stated as a strong recommendation, not an enforced constraint).

### Additional ambiguities I'm surfacing
1. **Direct-to-schema seeding vs. simulating through real application code paths.** The document describes the real Graph-based intake and Graph/SMTP-based dispatch mechanisms in detail. It's not stated whether the synthetic environment should generate rows *as if* they'd arrived through that pipeline (directly inserting plausibly-shaped Interaction/Ticket/etc. rows), or should actually drive the real service layer (e.g., a mock Graph provider) so business logic executes for real. This changes the entire shape of the generator — a data-authoring script vs. a simulation harness.
2. **Whether the reference/config tables should themselves drift over the simulated history.** `sla_policies` is explicitly editable live (§10.4/§19.3 of the source), not just a one-time seed. Should a multi-month synthetic history include a policy edit partway through (mirroring how the real system's admin UI is actually used), or should reference data stay constant for the whole period?
3. **Whether the user roster and client roster are fixed for the whole simulated period, or grow/change over it.** Realistic "months of operation" could mean new hires, deactivations, and new client onboarding happening throughout the window — or a fixed cast present from day one. Not stated either way, and it materially affects whether ticket/interaction volume should show growth over time or stay flat.
4. **Attachment content.** Column-level limits and types are specified, but not whether synthetic attachments need real (fake) file bytes in an actual object-storage backend, or just metadata rows referencing plausible-but-nonexistent `storage_key`/`bucket_name` values.
5. **Whether to include realistic "mess"** — draft interactions never sent, soft-deleted (hidden) interactions, orphaned/edge-case referential states — or whether the environment should be uniformly clean. This is a real tension with this project's own established approach so far (QA-gated, clean synthetic data) versus what "production-aligned" would actually look like in a real system that's been running for months.
6. **Escalation volume/distribution** specifically (not just the general category/priority/status weights already flagged) — no guidance on what fraction of tickets should ever reach `ESCALATED`, at what level distribution, or how often the confirmed acknowledge-without-assign stall state should appear if it's being modeled at all.
7. **`owner_ids` cardinality at the Team Lead level** — the demo seed shows exactly one Team Lead per category, but the document doesn't state whether that's a hard 1:1 rule or just how the seed happens to be shaped; this affects whether an escalation's `owner_ids` at TEAM_LEAD level is always a singleton or can be a real set.
8. **Whether more than one Site Lead is a realistic condition to generate** — the document's own wording ("Site Lead(s)") is plural, and escalation/notification fan-out logic already accounts for multiple, but the demo seed has exactly one.
9. **Business hours / timezone.** All timestamp columns are timezone-aware, but no business timezone or activity-hours pattern (vs. 24/7 uniform activity) is specified.
10. **Whether `ticket_type` should include occasional off-canon values**, given the schema itself enforces nothing — the source document's own recommendation is to sample from the 7 real values anyway "for realism," but that's advice, not a resolved fact; a genuinely production-aligned environment arguably should have *some* drift, which is a judgment call, not something derivable from the document.

### Specific to this project's prior work
This document changes the picture from earlier in this project significantly, and I want to name that directly rather than let it pass quietly: this project's existing `app/models.py` (`Customer`/`Ticket`/`Message`/`EvalQuery`) is a simplified schema built from an earlier, partial, self-described-as-truncated reference. The real schema is substantially different in shape — there is no `Message` table at all (the real equivalent, `Interaction`, is a single polymorphic table covering email/reply/note/attachment-event together, with no per-message `intent_type` concept at all); ticket categorization is an unconstrained string in production, not the enum this project built; there is no ground-truth/eval-query concept in production at all (confirmed — this project's `EvalQuery` table is correctly understood as a research-only bolt-on, never a production mirror). This document doesn't say what should happen to the existing `generation/` pipeline, `app/models.py`, or the benchmark spec docs already built — that's still the open "disposition of existing work" question from the earlier discovery checklist (Phase 7.3), now with a much more concrete, and much larger, gap to reconcile than when that question was first raised.

---

**I have not proposed any schema, generation strategy, or design decision in this document — this is purely a comprehension check, per the instruction. Flagging the items in §10 as things to resolve before design begins, not attempting to resolve them here.**
