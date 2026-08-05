# Production Readiness Roadmap

**Supersedes the prioritization (not the factual record) of `CORPUS_EXPANSION_ROADMAP.md` and `BENCHMARK_COVERAGE_REVIEW.md`, effective 2026-08-04.**

**See also `CORPUS_REALISM_STANDARDS.md`** (added 2026-08-05) — the detailed *how* for authoring any future corpus/benchmark content (length distributions, tone/style/sender diversity, long-email variety, business complexity tiers). This roadmap tracks *what/when*; that document governs *how*.

**See also `CORPUS_SCENARIO_COVERAGE_STRATEGY.md`** (added 2026-08-05) — answers a third question neither of the above covers: for each RCM service, what distinct production *capabilities* need multiple realistic variations, which already exist, which are missing, prioritized by production frequency/business impact. Read that document before picking which ticket to expand next — it found a real gap (standalone Payment Posting overpayment/refund scenario) that reorders Task 1B's stage sequence (see Stage 1C, inserted below).

**Philosophy change**: this project's goal is a recommendation system fit for integration into a production RCM ticket application, not an academic benchmark. Every task below is filtered through one question — *"if this application goes live tomorrow, what emails will it actually receive, and does the pipeline handle them?"* — and re-ranked by production impact, not by benchmark-taxonomy completeness. `CORPUS_COVERAGE_AUDIT.md`, `BENCHMARK_COVERAGE_REVIEW.md`, `NOISE_FLOOR_FINDINGS.md`, and `EVAL_HISTORY.md` remain the authoritative record of what's been measured — this document only changes what gets prioritized next and why. Same standing process as before: propose/approve a task (or sub-batch), execute, full re-run, review results before the next one.

---

## Task 1 — Corpus depth + long-form incoming emails + validation (Priorities 1+2+3, one combined workstream)

**Status: DONE (2026-08-05).** Executed with two corrections found mid-task (see the report): `E5` was swapped for `E4` after existing eval cases turned out to require `E5` stay a same-day, patient-still-waiting scenario incompatible with a multi-week saga; `P2`'s arc was redesigned to deepen without ever resolving, since two existing eval cases require it to stay mid-investigation. Also added the extra length-*distribution* requirement (short/medium/long mix, not just long) per follow-up direction. Result: **63/63 clear-case accuracy (100%), zero regression**; new `length_style_distribution` category 9/9 at 0.98 avg. confidence, highest of any category. Reranker token-truncation risk (flagged below) measured directly and ruled out for now, with headroom quantified, not just assumed. Full detail: `eval_reports/2026-08-05_length_style_distribution.md`.

**Why these three are one task, not three**: a realistic long incoming email ("following up on our last several exchanges about this denial...") is only realistic if the ticket it targets actually *has* that history. Depth (P1) and email length (P2) are two halves of the same realism gap, and validation (P3) is mandatory the moment either changes. Splitting them into separate efforts would mean building unrealistic long emails against thin tickets, or thin emails against rich tickets — neither tests what production traffic actually looks like.

**Current state, quantified** (from `CORPUS_COVERAGE_AUDIT.md` + direct inspection today):
- Only 5/50 tickets exceed 6 interactions, concentrated in 3 customers (`pinehill_ophtho`, `valley_womens_health`, `harborview_bh`); 3 of 6 RCM services (payment posting, eligibility, charge entry) have **zero** tickets with real conversational depth.
- Every incoming email in `eval_queries.py` (62 cases) is short — a single paragraph, no greeting/signature/quoted-history/multi-question structure. **There is currently no long-form (10-20+ line) incoming email anywhere in the benchmark.**

### 1A — Deepen 3 tickets, with deliberate length variety (not uniform depth)

| Ticket | Customer | Service (currently zero deep coverage) | Target depth | Narrative shape (deliberately not another denial→appeal→win, to diversify workflow shape too) |
|---|---|---|---|---|
| `P2` | `coastal_derm` | Payment Posting | ~5 interactions | Short reconciliation: ERA gap flagged, one provider-rep escalation, corrected same cycle |
| `E5` | `brightpath_urgent` | Eligibility | ~12 interactions | Multi-step eligibility mystery: wrong DOB, then a plan change discovered, then a coordination-of-benefits question — nobody's "wrong," it's just genuinely complicated |
| `G2` | `riverside_family_medicine` | Charge Entry | ~15-18 interactions | Iterative documentation-driven coding: codes sent, mismatch with documentation, correction round, entered, then a *second* round when the remittance flags a bundling conflict |

Selection avoided `metro_cardiology`/`pinehill_ophtho` (fragile/already-concentrated) and `ggi_gastro` (hosts the 3-way near-duplicate set) — same reasoning that caught the `C4`/`E2` collision last time.

### 1B — Long-form incoming emails as new eval queries against a *mix* of new-and-already-validated deep tickets

4-6 new cases, 10-20+ lines each, containing only meaningfully-contributing content (full issue recap, dates, claim/patient references, a payer-response summary, an explicit question, a follow-up ask, an attachment reference, greeting/signature) — against `P2`/`E5`/`G2` (new) **and** at least one of `A6`/`C8`/`A3` (already-validated) — deliberately, so a failure can be attributed to *email length* rather than *ticket novelty*.

1. **Why it matters in production**: real AM/payer/client correspondence is frequently long — full history recaps, multiple questions, attachment references. This is the input shape most different from anything currently benchmarked, and currently completely untested.
2. **Pipeline components exercised**: embedding (does a long query dilute signal), keyword+ANN retrieval, context builder (ticket history + long incoming email combined — real truncation risk), **reranker** (cross-encoders typically have hard token limits — a long ticket history plus a long incoming email is the first realistic scenario that could actually hit one), LLM decision (confidence calibration on dense input).
3. **Changes**: corpus (yes, 3 tickets deepened) + benchmark (yes, new queries) + pipeline code (none expected, *unless* truncation testing below reveals a real defect — that becomes its own follow-up task, not bundled in here).
4. **Effort**: Medium — 3 realistic multi-week arcs to draft, 4-6 long, information-dense eval emails.
5. **Validation**: standard full re-run + the same-customer-pool spot-check the `C4` incident taught us to do proactively, **plus a new check specific to this task**: inspect actual token counts hitting the context builder and reranker for the long-email cases — silent truncation could still produce a "correct" benchmark answer by luck while masking a real production defect that a short-email benchmark could never surface.
6. **Production impact**: highest of anything proposed here — directly answers whether the pipeline degrades on the input shape most likely to differ from what's been tested so far.

---

## Task 1B — Multi-customer corpus depth expansion (2026-08-05, supersedes the single-new-customer proposal)

**Status: PROPOSED, not approved.** Redirected from an earlier proposal (one new customer, one very-long ticket) after explicit direction: expand *multiple* existing customers instead of concentrating in one, cover all 6 services with multi-week depth spread across several customers, vary depth tiers (6/10/15/20+) rather than uniform length, and add tone/style diversity (frustrated, urgent, thankful, confused, concise, very detailed) that the stored corpus currently has *zero* of (confirmed 2026-08-05: 0/93 customer-side interactions show any casual/frustrated/urgent marker).

**Ground truth, computed directly from `seed_data.py` (not estimated):**

| Customer | Tickets | Status |
|---|---|---|
| `coastal_derm`, `riverside_family_medicine`, `valley_womens_health`, `harborview_bh`, `pinehill_ophtho` | — | Already deepened (prior passes) |
| `metro_cardiology` | C3, A2, G4, E1 | **All 4 tickets are the entire candidate pool for `info_ambiguous_archive_boundary`** (deliberately ambiguous hard case) — excluded from this push |
| `lakeside_peds` | P1, A4, E3 | **All 3 tickets are the entire candidate pool for `archive_ambiguous_lakeside`** — excluded from this push |
| `painmed_pa` | PM1-PM7 | Frozen original 21-query baseline — excluded per the standing Stage-1 (2026-08-03) decision, needs separate explicit approval to revisit |
| `ggi_gastro`, `brightpath_urgent`, `sunridge_ortho`, `summit_neurology` | — | Available, with specific tickets to avoid noted per-stage below |

This means only 4 customers are actually safe to add to this pass without deliberately disturbing an existing hard-case construct or the frozen baseline — a real constraint, not a shortfall in effort.

Service depth count going in: Claims 2 (`C8`, `C4`), Prior Auth 2 (`A6`, `A3`), AR 1 (`R2`), Payment Posting 1 (`P2`), Eligibility 1 (`E4`), Charge Entry 1 (`G2`). Stages below prioritize giving AR/Payment Posting/Eligibility/Charge Entry a genuine second customer before adding a third to Claims/Prior Auth, which already have two.

### Stage 1 — `ggi_gastro` (3 tickets; avoid `R5`/`R6`/`R7`, the existing 3-way AR near-duplicate)
| Ticket | Service | Target depth | Tone / shape |
|---|---|---|---|
| `A5` | Prior Authorization | ~10 | Urgent→relieved (endoscopy scheduling pressure); complication is a misrouted request, not a denial |
| `C7` | Claims | ~6 (short tier) | Matter-of-fact, concise — incorrect POS code, corrected, closed |
| `G5` | Charge Entry | ~14-15 (long tier) | Routine→frustrated (units keep coming back wrong across resubmissions)→thankful at resolution; multi-date complexity |

Production validation: tests whether deepening unrelated tickets in a pool that *also* hosts a deliberate structural-difficulty construct (`three_way_ar`) leaves that construct intact — a proactive version of the check the `C4`/`E2` incident taught us to do reactively.

### Stage 1C — Payment Posting overpayment/refund storyline (inserted 2026-08-05, per `CORPUS_SCENARIO_COVERAGE_STRATEGY.md`)

That strategy document's single highest-priority finding: overpayment/refund (a real, compliance-sensitive scenario — providers have actual regulatory obligations to refund overpayments) has **zero standalone Payment Posting representation** — it currently only exists as a supporting sub-thread inside `G5`'s draft. Checked all Payment Posting tickets for a safe home: `P1` (excluded customer), `P5`/`P6`/`P7` (hard case / near-duplicate pair, avoid), `PM3` (frozen) — none of the 4 customers available for Task 1B (`ggi_gastro`, `sunridge_ortho`, `summit_neurology`, `brightpath_urgent`) even *has* a safe Payment Posting ticket in its pool. The only realistic options are: (a) add a genuinely new ticket to `harborview_bh` (currently 3 tickets, only 1 deep — the least-concentrated already-touched customer) or `riverside_family_medicine` (currently 4 tickets, 1 very deep), or (b) a new customer. **Recommendation: (a), `harborview_bh`**, since it keeps this addition inside the already-established set rather than reopening the "new customer" question this stage deliberately moved away from — open for adjustment.

### Stage 2 — `brightpath_urgent` (1 ticket; avoid `P6`/`P7` near-duplicate pair and `E5`, per Task 1's finding)
| Ticket | Service | Target depth | Tone / shape |
|---|---|---|---|
| `C6` | Claims | ~12 | Frustrated→cooperative; a batch of claims with *different* denial reasons across multiple dates, reviewed case-by-case, staged/partial resolution |

Production validation: tests retrieval/context-building when a ticket's own history references multiple claim numbers/dates rather than one — realistic risk of over-triggering on any single cited claim number.

### Stage 3 — `sunridge_ortho` (2 tickets; avoid `A1`, the cross-customer guard partner of `PM4`)
| Ticket | Service | Target depth | Tone / shape |
|---|---|---|---|
| `R4` | Accounts Receivable | ~10 | Patient, professional, mild urgency late — slow aged-balance follow-up across multiple contact attempts, gives AR its 2nd deep customer |
| `G3` | Charge Entry | ~6 (light touch, already RESOLVED) | Add 2-3 believable steps, not a new saga |

Production validation: `R4`'s realistic short check-ins ("any update on the Aetna balance?") test whether near-zero-content queries fail only when a pool is *genuinely* ambiguous (the known, documented case) versus failing generally (which would be a real, more general defect) — a cleaner signal because this pool isn't already fragile.

### Stage 4 — `summit_neurology` (1 ticket only; avoid `P5` [hard case + cross-customer guard], `E7` [already-established fast-resolution premise], `A7` [same reason])
| Ticket | Service | Target depth | Tone / shape |
|---|---|---|---|
| `C5` | Claims | ~8 | Professional, concerned→satisfied; same CO-45 fee-schedule theme as its cross-customer guard partner `C1`, deepened without copying its exact wording |

Production validation: tests whether retrieval still discriminates correctly between a cross-customer lookalike pair once one side has meaningfully more history than the other — a deliberate, controlled version of the exact depth-asymmetry failure mode the `C4`/`E2` incident surfaced by accident.

### Benchmark validation (every stage, per `CORPUS_REALISM_STANDARDS.md`)
After each stage's corpus change: 4-6 new eval cases targeting only that stage's tickets, deliberately varied length (one-liner to 15+ lines) and tone (at least one frustrated/urgent/casual case per stage, not all professional) — then full re-run + sibling-pool spot-check before moving to the next stage. Same per-stage discipline as Task 1, now mandatory going forward.

1. **Why this happens in production**: batch claim denials, multi-week AR chases, prior-auth routing delays, and asymmetric-depth lookalike tickets are all routine RCM billing-office reality.
2. **Pipeline stages exercised**: retrieval/grouping under multi-entity content (Stage 2), near-zero-content queries against a *non-fragile* pool (Stage 3), depth-asymmetric cross-customer discrimination (Stage 4), and structural-construct stability under unrelated depth changes (Stage 1).
3. **Production risk reduced**: each stage targets a specific, previously-unverified way the pipeline could quietly misbehave as the corpus grows, rather than adding volume for its own sake.
4. **Deploy-confidence impact**: closes the "only one customer has real depth" pattern for good — after this, AR/Payment Posting/Eligibility/Charge Entry each have 2 customers with real multi-week history, not 1.

---

## Task 2 — Attachment-referenced / insufficient-content emails ("see attached EOB")

1. **Why it matters in production**: EOBs, denial letters, and ERAs are routinely attached, not pasted into the email body — "see attached EOB, please advise" carries almost no retrievable text signal, and is a completely realistic, common message.
2. **Pipeline components exercised**: retrieval under near-zero signal (already known from noise-floor data to be where non-determinism concentrates), and the **decision layer specifically** — there's currently no output category between "confidently attach" and "decline to attach" for "this needs a human because the email itself doesn't contain enough information."
3. **Changes**: benchmark (new cases) + **pipeline code** (real — this needs a small design decision on what "flag for mandatory human review" means as an output, not just new test data) + corpus (probably none).
4. **Effort**: Medium-high — needs a short design decision before eval cases can even define expected behavior (same category of upfront design as Task 3, just smaller in scope).
5. **Validation**: new eval queries containing only "see attached X"-style content, checked against whatever new decision semantics get built.
6. **Production impact**: high — a confidently-wrong guess on a contentless email is a worse production outcome than an honest "needs human review," and this exact input shape will happen routinely in production traffic.

---

## Task 3 — Customer identification robustness (design discussion required first, per your instruction)

Flagging only, not designing inline, since you asked for a design discussion first. What's confirmed by reading `customer_identification.py` just now: matching is a single exact, case-insensitive equality check against one `Customer.inbox_email` string — no multi-sender support, no domain matching, no "different sender at a known org" handling. The real design question worth raising when we have that discussion: domain-wide matching is safe for a practice's own custom domain but actively dangerous if any customer's inbox happens to be a shared consumer domain (gmail.com, etc.) — that tradeoff needs to be resolved before schema changes, not discovered after.

---

## Task 4 — Writing-style variety ("Noisy Writing" — already designed, never implemented)

Already scoped in `BENCHMARK_COVERAGE_REVIEW.md` as a proposed-but-unbuilt iteration: typos, casual/texting tone, all-lowercase/all-caps, abbreviations, bullet-list formatting.

1. **Why it matters**: real senders type on phones, skip capitalization, abbreviate — routine production traffic.
2. **Pipeline components exercised**: embedding robustness to surface noise. Customer identification is unaffected by construction (sender-email match, not content-based), worth confirming explicitly rather than assuming.
3. **Changes**: benchmark only — pure eval-query addition, zero corpus/pipeline risk. The safest task in this entire roadmap.
4. **Effort**: Low.
5. **Validation**: standard full re-run.
6. **Production impact**: Medium — real, but embeddings are generally typo-tolerant, so the marginal value is lower than Tasks 1-2. Worth doing because it's nearly free, not because it's high-stakes.

---

## Task 5 — Multiple concurrent tickets / limited-context disambiguation

**Deprioritized.** Answering your own test directly: does this significantly improve production-readiness confidence beyond what's already measured? No — `three_way_ar`, `near_dup_p6_p7`, and several disambiguation hard cases already exercise "customer has multiple similar open tickets, email has limited distinguishing content." A genuinely new pattern here would need a new kind of ambiguity, not another near-duplicate pair, and none has been identified. Revisit only if a specific production scenario surfaces one.

---

## Recommended sequencing

~~Task 1~~ (done, 2026-08-05) → **Task 1B** (multi-customer depth expansion, 4 stages, proposed above) → **Task 2** (attachment/insufficient-content handling) → **Task 3 design discussion** (customer identification) → **Task 4** (noisy writing, cheap, can slot in anytime relative to the others) → Task 5 stays deprioritized.

Ready to proceed with Task 1B Stage 1 (`ggi_gastro`) on your go-ahead.
