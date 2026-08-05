# AI Recommendation Service — Integration Decisions Log

Companion to `RECOMMENDATION_SERVICE_INTEGRATION_CONTRACT.md` (the authoritative description of the production ticketing app) and the two architecture diagrams in this same folder. That contract describes what production **already has**; this file records decisions **made about the not-yet-built AI Recommendation Service** during the initial study/Q&A pass over those documents — before any architecture review, code review, or implementation began.

Format: Question — Decision — Status.

---

**1. How does the AI Service authenticate to read production data?**
Decision: exactly like any other client — a Bearer JWT from `POST /api/v1/auth/login`. No service account or machine-credential path exists today, and none is being added as a special case.
Status: **Confirmed** (directly per the Integration Contract's own §0/§14 statement — this corrected an initial assumption that direct DB access might bypass this).

**2. Do `POST /index-interaction` / `POST /recommend-ticket` already exist?**
Decision: no — these are **new endpoints the AI Service itself must expose**, for the Main App to call. Not present anywhere in the Main App's existing route inventory.
Status: **Confirmed**.

**3. Does the AI Service's own thread-detection step duplicate Main App's?**
Decision: assume Main App already performs deterministic thread-matching *before* ever calling the recommendation service. The AI Service's own thread-detection stays in as an optional safety-check/verification layer for now, not a load-bearing dependency.
Status: **Provisional** — explicitly callable-out for removal later if it proves redundant.

**4. What triggers `POST /recommend-ticket`?**
Decision: automatic — a recommendation is generated as soon as a qualifying (unthreaded) email arrives, not on-demand by agent action.
Status: **Confirmed**.

**5. Which ticket statuses are eligible recommendation candidates?**
Decision: **all** of them — OPEN, IN_PROGRESS, PENDING, WAITING_FOR_CLIENT, RESOLVED, and CLOSED are equally eligible. Rationale: an incoming email can legitimately be about reopening a closed/resolved ticket, so status must not be used to prune the candidate pool.
Status: **Confirmed** — this corrected an initial assumption that CLOSED tickets might be excluded.

**6. Where do the two new AI-owned tables live?**
Decision: in the same shared database, via a **third Alembic chain** (alongside the existing `alembic_rbac` and `alembic_ticketing`), for now.
Status: **Confirmed, for now**.

**7. What exactly gets written to `recommendation_logs`?**
Decision: only the **top** recommendation — the recommended ticket plus the LLM's reasoning/explanation. Not a log of every candidate considered.
Status: **Confirmed**.

**8. How does ticket `category` interact with the attach-only recommendation flow?**
Decision: `category` represents which team/queue handles a ticket, assigned once at ticket creation — it is not something the recommendation flow needs to determine, since attaching to an *existing* ticket inherits that ticket's already-assigned category. This also applies to informational/thank-you-style emails that get attached to an existing ticket rather than archived — no category decision is needed there either.
Status: **Confirmed** — consistent with the recommendation service's scope being "attach or not," never ticket classification/triage.

**9. Does individual sender identity (within the same Client company) influence recommendation?**
Decision: **no, not for now.** Assume different individual senders at the same client company may legitimately be emailing about different, unrelated issues — sender identity has no bearing on retrieval or ranking today.
Status: **Provisional / explicitly deferred** — flagged by the user as a decision to revisit later, recorded here specifically for that reason.

**10. Are the 9 synthesized interaction types relevant, and what gets embedded?**
Decision: confirmed the 9 synthesized types (`STATUS_CHANGE`, `PRIORITY_CHANGE`, etc.) are reconstructed from audit logs at read time, not real interactions — not part of the embedding/retrieval surface. Offline indexing embeds only customer mail (`EMAIL`) and replies (`REPLY`, both client-side and agent-side) — matching production's real `interaction_type` values, not internal notes/attachments/SLA-pause events.
Status: **Confirmed**.

**11. Which database does the AI Service read/write during development?**
Decision: Main App's real deployment has its own production database; for development, a **separate copy of that same production database** is used as the common/shared database for both the Main App dev instance and the AI Service.
Status: **Confirmed, for the development phase**.

**12. Expected data volume / retention / re-embedding policy at scale?**
Decision: no specific numbers yet — the stated goal is simply that "the system should be reliable to use."
Status: **Open / directional only** — worth a concrete answer before any capacity-sensitive design decision, but not blocking at this stage.

**13. How does role-based visibility scoping apply to AI recommendations?**
Decision: visibility comes entirely from authentication and Main App's existing API rules — no separate visibility logic in the AI Service.
Status: **Confirmed**.

**14. Is a real event-emission mechanism planned?**
Decision: no — there is no event bus today. Design against the two synchronous API hooks (`/index-interaction`, `/recommend-ticket`) as the only integration mechanism for now.
Status: **Confirmed, for now** — explicitly left open to revisit later if needed.

**15. Should the recommendation service reconcile with the existing `recommender/` prototype's simplified schema, or does that stay independent?**
Status: **Deferred — no decision yet.**

---

*This log should be updated (not silently overwritten) whenever any "for now"/"provisional"/"deferred" item above is revisited or firmed up, so the reasoning trail stays intact.*
