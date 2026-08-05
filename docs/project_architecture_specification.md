# Project Architecture Specification

Status: **Architectural blueprint — no synthetic-world design, no generator design, no technology choices, no implementation.** This document defines the layer structure of the whole thesis project, now that its scope has expanded from "one benchmark dataset" to "a shared, production-aligned synthetic RCM environment serving multiple consumer projects." Everything here sits above and governs the documents that come next (§5).

---

## 1. Overall Project Architecture

Your example layering (Production Application → Synthetic Operational World → Shared Dataset → Research Layer → Benchmark Layer → AI Recommendation Layer → Future Automation Layer) gets the right entities on the table, but I'd restructure it before adopting it — it mixes two different *kinds* of things (data artifacts vs. the processes/systems that act on them) into one flat list, and it treats "Benchmark Layer" and "AI Recommendation Layer" as parallel siblings when they're not — a benchmark is something the recommendation system *uses*, not a separate layer standing next to it.

Here's the structure I'd actually build, and why each distinction matters:

```
┌─────────────────────────────────────────────────────────────┐
│  0. Production Reference Layer                               │
│     The real application. We never write to it or generate   │
│     into it — we capture our understanding of it as          │
│     versioned documents (KB, understanding report, and        │
│     eventually a formal schema mirror). This is the CONTRACT  │
│     everything below is validated against.                    │
└───────────────────────────┬────────────────────────────────┘
                             │ (informs, doesn't feed data into)
┌───────────────────────────▼────────────────────────────────┐
│  1. Generation Engine  (process, not data)                   │
│     Code that produces synthetic data against the Production  │
│     Reference contract: sampling/distribution logic, content  │
│     generation, business-rule/state-machine simulation, QA    │
│     validation, resumable state tracking.                     │
└───────────────────────────┬────────────────────────────────┘
                             │ produces
┌───────────────────────────▼────────────────────────────────┐
│  2. Synthetic Operational Dataset  ("the shared world")       │
│     The actual populated, production-schema-shaped data:      │
│     clients, users, interactions, tickets, attachments, SLA/  │
│     escalation state, notifications, audit logs. ONE shared,  │
│     versioned artifact — not split or duplicated per consumer.│
└──────────┬───────────────────────────────────┬──────────────┘
           │ extracted from                     │ extracted from
┌──────────▼──────────────┐          ┌──────────▼──────────────┐
│ 3. Research / Derived    │  ...     │ 3. Research / Derived    │
│    Artifact Layer         │          │    Artifact Layer        │
│    (per consumer purpose: │          │    (a different          │
│    benchmark + ground     │          │    consumer's own        │
│    truth for the          │          │    artifacts)             │
│    recommendation project)│          │                           │
└──────────┬───────────────┘          └──────────┬───────────────┘
           │ used by                              │ used by
┌──────────▼───────────────┐          ┌──────────▼───────────────┐
│ 4. Consumer System:       │          │ 4. Consumer System:       │
│    Ticket Recommendation  │   ...    │    (a future intern's     │
│    (this project's        │          │    automation project)    │
│    original purpose)      │          │                           │
└────────────────────────────┘          └────────────────────────────┘
```

**Why this differs from your example, concretely:**

- **Production Application isn't a layer *we* build** — it's external. What we actually own is layer 0, our *captured understanding* of it (documents, eventually a formal schema mirror). That's a meaningfully different thing from the real app, because our capture can go stale or be wrong — we already hit this once this session (the original schema reference was self-described as truncated and unverified, and this week's full knowledge base contradicts it on at least one concrete fact — see §4). Naming layer 0 as *our reference*, not *the real system*, keeps that risk visible instead of hiding it.
- **"Generation Engine" and "Synthetic Operational Dataset" are not the same layer.** One is code, one is data. They have different lifecycles — the engine changes as we improve it; the dataset changes when we run it. Your example's "Synthetic Operational World" conflated the two.
- **"Research Layer," "Benchmark Layer," and "AI Recommendation Layer" aren't three parallel layers — they're one pattern repeated per consumer.** A benchmark is a *derived artifact* a specific consumer (the recommendation system) needs for evaluation; it's not architecturally distinct from "research metadata" or "generated analytics" some other intern's project might derive from the same shared dataset. I've collapsed these into one layer type (§2 below) that repeats once per consumer, rather than a fixed enumerated list.
- **"Future Automation Layer" isn't a layer — it's a cardinality.** There will be N consumer systems over time; the ticket recommendation project is the first instance of that pattern, not a special case standing apart from "future" ones. Reserving a dedicated layer for hypothetical future work bakes in an asymmetry that isn't real — every future intern project is structurally identical to this one: reads the shared dataset, derives its own research artifacts, produces its own output.
- **The data flow is a hub, not a pipeline** — see §3.

## 2. Separation of Responsibilities

| Kind of data | Belongs in | Why |
|---|---|---|
| **Production-mirrored data** | Not generated data at all — it's the *schema and business-rule contract* (layer 0) that layer 2's data must satisfy. | It's a specification, not a dataset. Confusing "the schema" with "a dataset shaped like the schema" is exactly how the original truncated reference caused drift earlier this session. |
| **Synthetic operational data** | Layer 2, the shared dataset. | This is the "months of realistic operation" — clients, interactions, tickets, SLA/escalation state, notifications, audit logs. Read by every consumer as *context*, never owned by any one of them. |
| **Benchmark-specific artifacts** | Layer 3, scoped to the recommendation project specifically. | An eval-query set with ground-truth labels only means something in the context of one system being measured — it's not part of "the world," it's a test harness built by looking at the world. |
| **Research metadata** | Layer 3, per consumer. | QA reports, generation provenance (which model, which prompt version, which seed produced a given record), reviewer notes — describes *how an artifact was produced*, not business reality. Never belongs in layer 2, or a consumer querying "real" operational data would see research bookkeeping mixed into it. |
| **Evaluation data** | Layer 3, per consumer. | Same reasoning as benchmark artifacts — it's specific to measuring one system, not a fact about the operational world. |
| **Generated analytics** | Layer 3, per consumer (whichever project needs it) — **unless** it's descriptive of the *dataset generation process itself* (e.g. "did we hit our target category distribution"), in which case it's research metadata about the Generation Engine, not about any one consumer, and lives alongside layer 1, versioned with the engine run that produced it. | Analytics can mean two different things — "insights about the synthetic business" (a consumer concern, layer 3) vs. "did the generator do its job" (an engine-quality concern) — worth keeping these apart rather than filing both as one undifferentiated bucket. |

**The one governing rule underneath all of this**: layer 2 must be queryable/usable *without* any layer-3 artifact existing. If a consumer's benchmark table got dropped tomorrow, the operational dataset should be completely unaffected — that's the actual test of whether the separation is real, not just naming convention.

## 3. Data Flow

Not a strict pipeline — a **hub with independent spokes**. Your example ("Production Understanding → Synthetic World → Generated Operational Dataset → Benchmark Extraction → Model Evaluation → AI Recommendation System") reads as one serial chain ending at the recommendation system. That's an accurate description of *this project's own* path through the architecture, but it's the wrong shape for "a shared source for multiple projects" — it implies every future intern project has to wait behind benchmark extraction and model evaluation, which isn't true and shouldn't be designed as if it were.

The actual flow:

```
Production Reference (layer 0)
        │
        ▼
Generation Engine run (layer 1) — one versioned, seeded, reproducible execution
        │
        ▼
Synthetic Operational Dataset (layer 2) — ONE shared artifact, produced once per engine run
        │
        ├──────────────────────────┬───────────────────────────┐
        ▼                          ▼                           ▼
Recommendation project's    Some other intern's         A third project's
research layer (layer 3):   research layer (layer 3):   research layer (layer 3):
benchmark + ground truth    e.g. an SLA-breach           e.g. workload-analytics
        │                   predictor's training set          training data
        ▼                          ▼                           ▼
Recommendation system        That project's model        That project's output
(layer 4)                    (layer 4)                    (layer 4)
```

Each spoke runs independently, on its own schedule, without coordinating with the others — that independence is the entire point of a *shared* dataset. The only thing that has to be centrally coordinated is layer 1→2 (one engine run, one dataset, one version), because if every project generated its own copy of "the operational world," it stops being shared and the whole premise of this scope change is undone.

**One deliberate omission, stated rather than left implicit**: there is no feedback edge from layer 4 back into layer 2. A recommendation system's actual outputs (accepted/rejected suggestions) do not get written back into the synthetic world to influence future generation. This keeps the architecture acyclic, reproducible, and easy to reason about — a closed loop (where consumer output becomes new operational history) is a real, valid idea for later, particularly for an RL-style project, but it's a substantial additional design problem (versioning, non-reproducibility, which consumer's feedback "wins") that shouldn't be assumed into the baseline architecture. If a future consumer genuinely needs that, it's an explicit extension to design when it comes up, not a default.

**One structural question this raises but doesn't answer** (flagged for §5, not decided here): is layer 2 a single, continuously-live database multiple projects query concurrently, or a versioned, reproducible *specification* that can be (re-)materialized into fresh instances (one canonical shared instance most projects use, plus the ability to spin up others — a small one for fast iteration, a large one for load testing)? Given this project's own generation engine is already seed-driven and config-driven, the second shape is a natural extension rather than a new idea — but which one becomes "the" shared dataset different teams actually point at is a governance decision (§5, D2), not something to settle here.

## 4. Existing Work Assessment

### Remains unchanged
- `generation/state.py` — the SQLite resume/retry store. Fully schema-agnostic; tracks unit status by opaque ID regardless of what the unit represents.
- `generation/llm_client.py` — the Ollama client wrapper. A pure LLM-call abstraction, has no knowledge of what schema it's generating content for.
- `app/database.py` — engine/session boilerplate, schema-agnostic.

### Should be refactored (methodology kept, content/specifics rewritten)
- `generation/config.py`, `generation/sampling.py` — the *patterns* (YAML-driven scale/distribution config, weighted stratified sampling, structural sampling constraints like forcing a coupled field for a given tier) are sound and reusable engineering. The concrete fields (built around the old Customer/Ticket/Message shape) need to expand to the real entity set.
- `generation/qa/rules.py`, `generation/qa/gate.py` — the *architecture* (deterministic rule checks + LLM judges + a PASS/FLAG/FAIL gate, FAIL-regenerates/FLAG-queues-for-review) is exactly the right shape for validating a much larger, more interconnected state machine. The specific rules need to check the real schema's actual constraints (the partial unique indexes, the generation-order constraint, SLA clock arithmetic, the escalation freeze rule) instead of the old schema's.
- `generation/pipeline.py`, `generation/cli.py` — the orchestration pattern (stage-by-stage, QA-gated, resumable, per-item retry granularity distinct from per-call batching) holds up. It will need substantially more stages for the real entity set, and the stage list itself needs redesigning.
- `docs/generation_prompts.md` — the *methodology* (orchestrator assigns every sampling decision, never the LLM; a deliberately blind independent labeling pass; explicit anti-leakage rules) carries forward. The five templates themselves are built around entities that no longer match production and need to be redesigned against the real one.
- `docs/generation_qa_checklist.md` — same relationship as the rules file above: keep the checklist's *shape*, rewrite its specific checks.
- `docs/benchmark_dataset_spec.md` — will need a full rewrite once the shared operational dataset's real corpus shape (Interaction-based, not Message-based) is settled, but the underlying benchmark *design thinking* (six difficulty tiers, orthogonal style-tag sampling, a blind ground-truth pass) doesn't need to be rediscovered, only re-grounded.

### Should be replaced
- `app/models.py`'s `Customer`, `Ticket`, `Message` and their supporting production-mirror enums (`TicketCategory`, `SenderType`) — the real schema is different enough in *kind*, not just detail, that adapting these in place isn't the right move. Most notably: there is no `Message` table in production at all (the real `Interaction` is one polymorphic table covering email/reply/note/attachment together); `ticket_type` is an unconstrained string in production, not an enum with a foreign key.
- The current Alembic migration chain (built for the old schema) and `generation/ingest.py` (writes to the old schema specifically) — both need to be rebuilt once the new schema mirror is finalized (§5, D1).
- `docs/execution_roadmap.md` — scoped entirely to the old, narrower "one benchmark" objective; superseded by the document sequence in §5.

**One concrete, worth-naming discrepancy surfaced by this assessment**: this project's `TicketCategory` enum removed `patient_calling` earlier this session, on the basis that the category was "confirmed... slated for removal from production." The new, more authoritative knowledge base document lists **Patient Calling** as one of the 7 *current* production categories, with full issue-type detail, and no mention of deprecation. These two claims directly conflict. I'm not resolving this here — flagging it as a fact to reconcile (with you, or against the source system directly) before the new schema mirror (§5, D1) locks in a category list. Separately, and reassuringly: `TicketStatus`'s six values were independently arrived at earlier this session and match the knowledge base's `ticket_status_enum` exactly — a case where prior work held up under the new, authoritative check rather than needing correction.

### Should remain research-only
- `app/models.py`'s `EvalQuery` (and `DifficultyTier`/`Tone`/`LengthBucket`/`NoiseLevel`) — confirmed by the knowledge base itself: no ground-truth/eval-query concept exists anywhere in production. This table was always correctly scoped as a research artifact, never a production mirror, and that doesn't change with the new schema — it just moves conceptually into layer 3, sitting *beside* the new production-mirror tables rather than mixed among them.
- `pilot/` — the hand-authored pilot dataset was built and QA-reviewed entirely against the old schema. It's superseded as a structural template, but not worthless: the domain-realistic *content* in it (payer names, CARC-style denial phrasing, RCM vocabulary, realistic thread pacing) is exactly the kind of material worth mining when designing the new Interaction-content generation templates.

### Should become part of the production-aligned synthetic environment
- Not code or files, but two things worth carrying forward deliberately: the **domain-realism content** already validated in the pilot and prompt templates (payer names, denial/CARC-style reasoning, RCM terminology density), and the **generation principles** proven out this session — orchestrator-controlled sampling, blind independent ground-truth derivation, a QA gate that regenerates on FAIL and queues FLAGs for review, resumable state-tracked execution. None of these are schema-specific; all of them scale up to the bigger environment unchanged in spirit.

## 5. Future Design Documents

Recommended order, each depending on the ones before it:

**D1 — Production Schema Mirror Specification.**
*Purpose*: translate the knowledge base's prose/table descriptions into an exact, implementable schema contract — the literal target the generator populates.
*Why needed*: nothing downstream (scale, content, QA rules) can be designed against an approximate or ambiguous schema; this project already paid that cost once with the original truncated reference.
*Finalizes*: table-by-table structure for both the RBAC and ticketing domains; resolution of the Patient Calling discrepancy and any other fact conflicts found while doing this closely; which fields are truly derived/query-time-only (never stored); how to treat non-authoritative tables like `escalation_handling_slas` (generate for realism, never as a source of truth); whether the real app's two-migration-chain structure is mirrored or collapsed.

**D2 — Data Governance & Separation Specification.**
*Purpose*: settle the physical/logical boundary between the shared operational dataset and every consumer's research artifacts, and how multiple concurrent projects actually access the shared data.
*Why needed*: this is the direct implementation of your own stated requirement ("these research artifacts must remain separate") — it's infrastructure-shaping and should be decided before content/scale design, not after.
*Finalizes*: separate schemas vs. separate databases vs. another mechanism; whether layer 2 is one continuously-live shared instance or a versioned, re-materializable specification (and if the latter, what "the" canonical shared instance means for day-to-day use by other projects); read/write access rules per consumer (research layers should only ever read layer 2, never write to it).

**D3 — Synthetic World Content, Scale & Temporal Specification.**
*Purpose*: the operational-world-wide analog of the old benchmark spec — realistic volumes and distributions across the *entire* entity set, not just tickets and eval queries.
*Why needed*: every open scale/volume/distribution question flagged in the Understanding Report lives here — none of it can be assumed.
*Finalizes*: client/user/interaction/ticket counts and ratios; whether the roster grows over the simulated period or is fixed from day one; business-hours/timezone activity patterns; escalation frequency and level distribution; whether to include realistic "mess" (drafts, hidden interactions, occasional off-canon `ticket_type` values) or stay uniformly clean.

**D4 — Generation Methodology Specification.**
*Purpose*: decide, entity by entity, what's LLM-authored content versus what's deterministically simulated.
*Why needed*: this is a genuinely new distinction the old project never had to make, because every old entity was prose the LLM wrote. Here, interaction email/note text is authored content, but SLA clocks, escalation state transitions, audit log rows, and notification records are *business-logic simulation* — computed from the rules in the knowledge base, not generated by a model. Conflating these would either waste LLM calls simulating arithmetic or under-specify the actual state-machine correctness the environment needs.
*Finalizes*: which entities get which treatment; template/prompt design for the authored ones; simulation-rule design for the derived ones (mirroring the real SLA/escalation math precisely).

**D5 — Operational-World QA & Validation Framework.**
*Purpose*: the expanded analog of the old QA checklist, validating the real schema's actual constraints across a much more interconnected state machine.
*Why needed*: the real schema's hard invariants (one active escalation per ticket, one open handling-SLA row per escalation, the generation-order constraint, SLA clock arithmetic, the escalation-freeze rule) are all things a generator could silently violate without a dedicated check.
*Finalizes*: the rule/judge split for the new entity set; what a FAIL vs. FLAG means at this larger scale; how simulation-derived entities (D4) get validated differently from authored content.

**D6 — Recommendation-System Benchmark Extraction Specification.**
*Purpose*: this project's *own* layer-3 design — how the ticket-recommendation benchmark specifically gets derived from the shared operational dataset now that the corpus is Interaction-shaped rather than Message-shaped.
*Why needed*: this is where the original benchmark work actually resumes, now correctly positioned as one consumer's derived artifact rather than the whole project.
*Finalizes*: the redesigned difficulty-tier/ground-truth scheme against real Interaction threads; how "OPEN tickets only" scoping and the message-intent-vs-ticket-association distinction (already settled earlier this session) map onto the real schema.

**D7 — Generation Pipeline Technical Design** *(explicitly after all of the above, not now)*.
The engineering equivalent of this project's earlier Phase-6 planning — concrete module design for the (by then substantially larger) generation engine. Deliberately last: technology and implementation choices are out of scope until D1–D6 have fixed *what* is being built.
