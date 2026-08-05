# Corpus Scenario Coverage Strategy

**Purpose**: answer a different question than `CORPUS_REALISM_STANDARDS.md` (which governs *how* a ticket should read) or `PRODUCTION_READINESS_ROADMAP.md` (which tracks *what/when*). This document answers: **for each RCM service, what are the distinct production capabilities the recommendation system needs to handle, how many realistic variations of each does the corpus need to give real confidence, which already exist, and which don't.** Established 2026-08-05, per explicit direction to build a representative production dataset rather than a set of isolated high-quality tickets.

**Method**: every "already covered" claim below is checked directly against the actual current ticket list (`seed_data.py`, re-verified this session), not assumed. Variation-count targets are informed by production frequency/business impact, not by symmetry across services — a high-volume, low-drama scenario (routine eligibility check) doesn't need the same variation count as a low-volume, high-impact one (multi-week prior-auth appeal).

**Constraint carried over from `PRODUCTION_READINESS_ROADMAP.md` Task 1B**: `metro_cardiology` and `lakeside_peds` are excluded (every ticket in each is the entire candidate pool for a deliberately-ambiguous hard case); `painmed_pa` (PM1-PM7) is the frozen baseline. Scenario gaps that could only be filled by touching those customers are noted as such rather than silently skipped.

---

## Charge Entry

| # | Scenario | Target variations | Covered by | Status |
|---|---|---|---|---|
| 1 | Simple correction caught before billing | 2 | `G1` (thin), `G5` draft (as one thread among several) | Partial — need one genuinely *short*, single-issue version distinct from `G5`'s complexity |
| 2 | Correction discovered after payer rejection (NCCI/bundling edit) | 1-2 | `G2` (deep, modifier-25/NCCI saga) | **Covered** |
| 3 | Multiple patients/dates affected by the same root cause | 1-2 | `G5` draft | **Covered** (pending commit) |
| 4 | Template/configuration default issue (systemic root cause) | 1-2 | `G5` draft | **Covered** (pending commit) |
| 5 | Recurring issue over several weeks | 1-2 | `G5` draft | **Covered** (pending commit) |
| 6 | Urgent correction before claim submission (deadline pressure) | 1 | — | **Missing** |
| 7 | Correction requiring payer refund/overpayment recoupment | 1-2 | `G5` draft (as a sub-thread, not the ticket's own focus) | Partial — no ticket where this *is* the main storyline |
| 8 | Ongoing coding-clarification / uncertain-CPT dialogue | 1 | `G7` (pinehill, "which CPT code applies") | **Covered** |
| 9 | Duplicate charge entry | 1 | `G4` (metro — excluded customer) | **Missing in a safe customer** |

**Priority**: #6 and #7-as-primary-storyline are the real gaps; #9 is structurally missing a safe home. Charge Entry is otherwise strong once `G5` lands.

## Claims

| # | Scenario | Target variations | Covered by | Status |
|---|---|---|---|---|
| 1 | Denial for missing information (auth #, modifier, NPI) → resubmit | 2-3 | `PM1`, `C3` (excluded customer), `C7` (Stage 1 target) | Partial — mostly thin/frozen/excluded; `C7` fixes this |
| 2 | Denial for medical necessity → appeal with clinical documentation | 1-2 | `C8` (deep) | **Covered** |
| 3 | Timely filing dispute → proof of original submission | 1 | `C4` (deep) | **Covered** |
| 4 | Clearinghouse/EDI technical rejection (invalid NPI, etc.) | 1 | `C2` | **Covered** |
| 5 | Batch of claims denied for one systemic reason, reviewed case-by-case | 1-2 | `C6` (Stage 1 target) | Pending Stage 1 |
| 6 | Contractual rate/fee-schedule dispute (CO-45 style) | 2 | `C1`, `C5` (Stage 1 target) — deliberately a cross-customer lookalike pair | **Covered** |
| 7 | Duplicate claim submission confusion | 1 | — (only payment-side duplicate exists, `P4`) | **Missing** |
| 8 | Claim stuck in processing, no denial yet (pure status-check) | — | Covered structurally by existing short follow-up eval cases across services | Not a corpus gap — this is a query-shape, not a ticket-shape |
| 9 | Coordination-of-benefits affecting claim adjudication order | 1 | — (COB exists only on the eligibility side, `E4`) | **Missing from Claims specifically** |

**Priority**: #1 is highest-frequency in real RCM traffic and is fixed by Stage 1's `C7`; #7 and #9 are real but lower-frequency gaps, worth a future ticket each, not urgent.

## Prior Authorization

| # | Scenario | Target variations | Covered by | Status |
|---|---|---|---|---|
| 1 | Standard request → approved quickly, no drama | 1-2 | `A7` | **Covered** |
| 2 | Denied for insufficient documentation → appeal with clinical notes | 2 | `A6` (deep) | **Covered** |
| 3 | Auth expired before procedure date | 1 | `A2` (excluded customer) | **Missing in a safe customer** |
| 4 | Auth obtained but not attached to claim submission | 1-2 | `A3` (deep), `PM1` | **Covered** |
| 5 | Urgent/expedited request under scheduling pressure | 1-2 | `A4` (excluded customer), `A5` (Stage 1 target) | Pending Stage 1 |
| 6 | Peer-to-peer review required before determination | 1 | `A6` (deep) | **Covered** |
| 7 | Approved but for wrong/insufficient units or scope | 1 | — | **Missing** |
| 8 | Denied for lack of conservative-treatment documentation (MRI-pattern) | 2 | `A1`/`PM4` — deliberate cross-customer lookalike pair | **Covered** |

**Priority**: #7 is a genuine, currently-unrepresented pattern (mirrors Charge Entry's units issue but on the authorization side, e.g. approved for 1 session when 3 are needed) — worth a future ticket. #3 needs a safe customer, not urgent given `A5` covers a related pressure-scenario.

## Eligibility

| # | Scenario | Target variations | Covered by | Status |
|---|---|---|---|---|
| 1 | New patient, plan not found on portal → manual verification | 1-2 | `E1` (excluded customer), `PM5` (frozen) | **Missing in a safe customer** |
| 2 | Coverage terminated retroactively, discovered after service | 1 | `E2` | **Covered** |
| 3 | Wrong plan on file → update and resubmit | 1 | `E3` (excluded customer) | **Missing in a safe customer** |
| 4 | Secondary/COB not verified before visit | 1-2 | `E4` (deep) | **Covered** |
| 5 | Walk-in/same-day urgent verification | 1 | `E5` | **Covered** (deliberately kept short/urgent, per Task 1's finding) |
| 6 | Coverage change mid-relationship (aged into Medicare, new employer plan) | 1-2 | `E4` (deep) | **Covered**, one example only |
| 7 | Insurance card reissued/renewed → re-verification | 1 | `E6` | **Covered** |
| 8 | Payer portal outage/lag causing false "inactive" read | 1 | `E7` | **Covered** |

**Priority**: the best-covered service overall. #1 and #3 are only missing because their existing examples live in excluded customers — genuine gaps, but low urgency since 6 of 8 scenarios already have a safe example.

## Payment Posting

| # | Scenario | Target variations | Covered by | Status |
|---|---|---|---|---|
| 1 | Payment posted to wrong patient (name-similarity mixup) | 1 | `P1` (excluded customer) | **Missing in a safe customer** |
| 2 | ERA total doesn't reconcile with line items | 1-2 | `P2` (deep, deliberately unresolved) | **Covered** |
| 3 | Underpayment/bundling question on a procedure | 2 | `P6`/`P7` — deliberate near-duplicate pair | **Covered** |
| 4 | Duplicate payment/ERA import, double-posted | 1 | `P4` (thin) | Partial |
| 5 | Check/paper payment received but not yet posted | 1 | `P3` (thin) | Partial |
| 6 | Contracted-rate mismatch | 2 | `P5`, and its cross-customer guard partner | **Covered** (but `P5` is a hard case, handle with care) |
| 7 | Overpayment discovered → refund process to payer | 1-2 | Only exists as a *sub-thread* inside `G5`'s draft (charge_entry) | **Missing as its own Payment Posting storyline** |

**Priority**: **#7 is the standout gap** — overpayment/refund is compliance-sensitive (providers have real regulatory obligations to refund overpayments) and currently has zero standalone Payment Posting representation, only a supporting role in a charge_entry ticket. #4/#5 are thin but at least exist.

## Accounts Receivable

| # | Scenario | Target variations | Covered by | Status |
|---|---|---|---|---|
| 1 | Routine aging-balance follow-up with one payer | 2 | `R1` (thin), `R5`/`R6`/`R7` (deliberate 3-way near-dup) | **Covered** |
| 2 | Patient balance dispute (patient/insurer disagree on what's owed) | 1-2 | `R2` (deep) | **Covered** |
| 3 | Write-off request for small/uncollectible balances | 1 | `R3` (thin) | Partial |
| 4 | Payment plan setup and installment tracking | 1 | `R2` (deep) | **Covered** |
| 5 | Multi-payer aged-balance triage (several payers, one ticket) | 1 | — | **Missing** |
| 6 | Long-stalled case escalated to payer provider relations | 1-2 | `R4` (Stage 1 target) | Pending Stage 1 |
| 7 | Partial payment received, balance remains open | 1 | — (exists as an *element* inside `R2`, not its own arc) | Partial |
| 8 | Balance turns out to be a billing error, not a real balance | 1 | — | **Missing** |

**Priority**: #5 (multi-payer triage) is a genuinely complex, currently-unrepresented ticket shape and a good candidate for a future "highly complex" tier ticket. #8 is a realistic, low-effort addition (a phantom balance caused by our own coding mistake, not a real patient/payer dispute).

---

## Cross-service priority ranking (by production frequency × business impact, not completeness)

1. **Charge Entry #6/#7, Payment Posting #7 (overpayment/refund as its own storyline)** — highest priority. Compliance-sensitive (real regulatory refund obligations), currently has *zero* standalone representation despite appearing as a side-element in `G5`. A dedicated Payment Posting ticket centered on this would close a real gap, not just add volume.
2. **Claims #1 (missing-info denial → resubmit)** — highest-frequency real-world pattern; already scheduled to improve via Stage 1's `C7`.
3. **AR #5 (multi-payer triage)** — lower frequency but meaningfully different complexity shape than anything currently in the corpus; good "highly complex tier" candidate for later.
4. **Prior Auth #7 (approved but wrong units/scope)** — real pattern, lower frequency, no urgency.
5. **Claims #7/#9, Eligibility #1/#3, Payment Posting #1/#4/#5, AR #8** — genuine but lower-priority gaps, several already blocked on excluded customers rather than needing new design work.

## Recommended sequencing

Finish Stage 1 as already scoped (`G5`, `A5`, `C7` — all three already map to real gaps above: `G5`→Charge Entry #3/#4/#5, `A5`→Prior Auth #5, `C7`→Claims #1), then insert a new **Stage 1C**: one Payment Posting ticket in a safe, not-yet-concentrated customer, centered on the overpayment/refund storyline (#7), before continuing to Stages 2-4. This directly closes the single highest-priority gap this analysis found, rather than proceeding on the original Stage ordering blind to it.

## Communication-pattern assignment for the immediate queue (added 2026-08-05, per `CORPUS_REALISM_STANDARDS.md`'s frequency tiers)

Business-scenario coverage and communication-style coverage are two different axes — this maps the near-term queue against both, deliberately, rather than by accident:

| Ticket | Business gap closed | Primary communication pattern(s) | Tier |
|---|---|---|---|
| `G5` (done, pending commit) | Charge Entry #3/#4/#5 | Long initial description, medium updates, one-liners, clarification, attachment reference, customer correction, frustrated escalation, **manager intervention** (first in the corpus), thank-you, closing | Mix of all 3 — deliberately the richest single example |
| `A5` | Prior Auth #5 (urgent/expedited) | **Urgent request** (Tier 3, justified by genuine scheduling pressure) → status recap → short closing | Mostly Tier 1, one deliberate Tier 3 moment |
| `C7` | Claims #1 (missing-info denial) | Tier 1 only (quick status recap, short close) — short/simple by design, no manufactured drama | Tier 1 only |
| Stage 1C (Payment Posting overpayment/refund) | Payment Posting #7 | **Attachment-referenced** (EOB/remittance showing the overpayment, Tier 2) + status recap; tone should be concerned/procedural rather than frustrated, to avoid repeating `G5`'s escalation arc immediately | Tier 1 + Tier 2, deliberately no Tier 3 (keeps escalation/manager-intervention rare, not a per-ticket default) |

Going forward, every new ticket proposal should include this same two-axis check (business scenario + communication pattern + tier) before drafting, not after.
