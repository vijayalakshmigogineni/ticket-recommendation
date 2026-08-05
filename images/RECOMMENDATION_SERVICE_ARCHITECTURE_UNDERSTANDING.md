# AI Recommendation Service — Architecture Understanding

Third companion file to `RECOMMENDATION_SERVICE_INTEGRATION_CONTRACT.md` (authoritative on production) and `RECOMMENDATION_SERVICE_INTEGRATION_DECISIONS.md` (the Q&A decisions log). This file is the synthesized understanding built from studying the Contract plus both architecture diagrams (`ChatGPT Image Jul 30, 2026...png` — the AI Recommendation pipeline itself; `ChatGPT Image Aug 1, 2026...png` — the service integration/boundary diagram), **updated to reflect the answered decisions**, not the original pre-answer assumptions. No architecture review, code review, or implementation has happened yet — this is comprehension only.

---

## Production application architecture

One running FastAPI app ("unified-backend") over one shared Postgres database (Neon), written to by two independent Alembic migration chains: `alembic_rbac` (users, roles, permissions, categories, and — non-obviously — notifications) and `alembic_ticketing` (clients, tickets, interactions, attachments, SLA/escalation tables). Ticketing routes are mounted unprefixed at the app root; RBAC routes under `/api/v1`. Every route requires a Bearer JWT from `POST /api/v1/auth/login` — there is no service-to-service API key or machine-credential path.

Core entities: **Client** (a company, never an individual — the unit of "customer" for everything), **Interaction** (the single unified timeline row for every email/reply/note/attachment event), **Ticket** (the work item), **User** (internal staff, with the RBAC "Client" role additionally used to present client companies as pseudo-user rows via a merged-identity mechanism on `/api/v1/users`), **Attachment** (keyed to an Interaction, never directly to a Ticket), a five-table SLA family, **Notification** (with the only real push channel in the system — a per-user SSE stream), two separate audit-log tables (ticketing-domain vs. RBAC-domain), and lookup tables (`categories`, `roles`, `permissions`, `ticket_relations`).

No ML/recommendation infrastructure exists in production today — confirmed no pgvector extension, no embedding columns, no feedback/recommendation-log table, no ML dependency in the backend's own requirements.

## Ticket lifecycle

`OPEN → IN_PROGRESS → PENDING → WAITING_FOR_CLIENT → RESOLVED → CLOSED` — not strictly linear, a ticket can revisit several states before closing. Created only via `POST /tickets/from-interaction` (no blank-ticket path exists). **RESOLVED is not terminal** — its Resolution SLA clock keeps running; only **CLOSED** is terminal, reachable back to OPEN only via a dedicated Reopen action. A ticket's priority can be permanently force-bumped to CRITICAL by the escalation workflow (confirmed: never reverts, and confirmed separately exploitable via the ordinary priority-change endpoint too — a known production gap, not a recommendation-service concern).

**For recommendation purposes**: all six statuses — including CLOSED — are equally eligible candidates for attachment (Decision #5), since an incoming email may legitimately be about reopening a closed ticket.

## Interaction lifecycle

The atomic conversational-content unit, existing both before and after a ticket exists (`ticket_id` nullable, NULL while unticketed). Six real, persisted `interaction_type` values: `EMAIL, REPLY, INTERNAL_NOTE, ATTACHMENT, SLA_PAUSED, SLA_RESUMED`. A further nine type labels (`STATUS_CHANGE, PRIORITY_CHANGE, AGENT_TRANSFER, CLAIM, TICKET_CLOSED, TICKET_REOPENED`, three `EDIT_ACCESS_*`) appear on the ticket-timeline API but are **synthesized at read time from audit-log rows** — not real, independently-queryable interactions (Decision #10, confirmed).

`ticket_id` linkage happens either at insert time (thread already ticketed) or later, in one batch, when a thread's root gets promoted to a ticket — stamping the root and every reply chained to it via `parent_interaction_id` simultaneously.

**For the offline indexing pipeline**: only `EMAIL` (customer-side) and `REPLY` (both directions — client and agent) get embedded (Decision #10). Internal notes, attachments, and SLA-pause events are excluded.

## Email workflow

Microsoft Graph delivers a message → mapped into an `Interaction` → duplicate-checked by `message_id` → Client resolved by matching the sender address against `clients.inbox_email` (unmatched → routes to a Site Lead, never dropped) → deterministic thread match attempted (`conversation_id → in_reply_to_message_id → references`, first hit wins, walked to the true root). If that matches an already-ticketed thread, the pipeline stops there entirely — no pool item, no ticket creation, and (per Decision #3) no AI involvement is assumed necessary, though the AI Service may still re-verify as an optional, removable safety layer. If it doesn't match, the `Interaction` sits in the shared Mail/Inbox pool (`status=PENDING`) until an agent acts, **and** — per Decision #4 — a recommendation is generated automatically at that point, not on agent demand.

## Communication model

Interaction `direction` (`INBOUND/OUTBOUND/INTERNAL`) is set explicitly per call site, never inferred. Threading today is **purely deterministic, header/id-based** — production has no subject/body similarity matching anywhere; that gap is exactly what the recommendation service is being built to fill for the subset of emails that don't thread-match. Individual sender identity is never a modeled entity — only free text inside `Interaction.payload` (`from_name`/`from_email`) — and per Decision #9, sender identity has **no influence** on recommendation logic for now (explicitly flagged as a deferred decision, since two different senders at the same client company could legitimately be emailing about unrelated issues).

## Event flow

No domain-event bus, webhook system, or subscription API exists. The only real-time push mechanism is a per-user SSE notification stream, not designed for service-to-service use. Per Decision #14, the AI Service is designed against today's reality — the two synchronous API hooks below — with no expectation of an event bus arriving; this is an explicitly revisitable decision, not a permanent architectural constraint.

## API integration

The AI Recommendation Service will expose **two new endpoints** (Decision #2 — these do not exist today and are not part of the Main App's current route inventory):
- `POST /index-interaction` — called asynchronously by Main App whenever an interaction is created or updated (offline indexing trigger).
- `POST /recommend-ticket` — called automatically for an independent incoming email once Main App has determined no deterministic thread match exists (Decision #4).

The AI Service authenticates to the rest of the system **exactly like any other client** — a Bearer JWT from the same login endpoint, no special service account (Decision #1, confirmed directly from the Contract, correcting an earlier assumption that a direct-DB-bypass model was implied by the architecture diagram). Visibility/scoping for anything the AI Service surfaces comes entirely from that same authentication and Main App's existing API rules — no separate visibility logic needed in the AI Service itself (Decision #13).

## Shared database architecture

One physical Postgres database, shared between Main App and the AI Service. For development specifically, a **separate copy** of the production database is used as that common/shared instance (Decision #11) — Main App's real deployment has its own production database distinct from this dev-shared copy. The AI Service's own two new tables (`interaction_embeddings`, `recommendation_logs`) will live in this same shared database via a **third Alembic chain**, for now (Decision #6) — alongside the existing `alembic_rbac`/`alembic_ticketing` chains that Main App already owns.

## Recommendation service responsibilities

Per the architecture diagram: preprocessing → embedding generation → offline indexing (only `EMAIL`/`REPLY` types, per above) → hybrid retrieval (keyword + ANN/vector) → grouping interactions by candidate ticket with a weighted score → per-candidate context building → cross-encoder reranking → LLM decision with an explanation and confidence → the recommendation is surfaced to an Account Manager, who accepts, rejects, or picks a different candidate — the AI Service never attaches anything itself. Only the **top** recommendation (ticket + LLM reasoning) is logged to `recommendation_logs`, not every candidate considered (Decision #7). Category/team-routing is not something the recommendation flow needs to determine — attaching to an existing ticket inherits that ticket's already-assigned category, including for informational/thank-you-style emails that get attached rather than archived (Decision #8).

## Integration boundaries

**Main App**: business logic and sole owner/writer of every real production table (clients, tickets, interactions, users, attachments, SLA family). **AI Service**: reads those same tables (via the shared database) and writes only to its own two new tables — never to a production table directly, and explicitly never repurposing `ticket_relations` as a recommendation-output store (the Contract's own explicit warning). **Database**: the shared source of truth for both. **Ollama**: the model-inference engine (embedding, cross-encoder, and chat/LLM models) shared by the AI Service.

---

## Still open / explicitly deferred (not blocking, but not resolved)

- Expected data volume, retention policy, and re-embedding strategy at real production scale — no concrete numbers yet, only a stated reliability goal (Decision #12).
- Whether the existing `recommender/` prototype's simplified schema gets reconciled with production's real schema, or remains an independent proof-of-concept (Decision #15 — deferred).
- Whether sender-identity weighting, the AI Service's own thread-detection safety layer, and the "no event bus" design constraint remain as-is or get revisited (Decisions #9, #3, #14 — all explicitly provisional).

No architecture review, code review, or implementation performed as part of producing this document.
