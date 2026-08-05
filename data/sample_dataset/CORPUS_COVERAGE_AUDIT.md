# Corpus Coverage Audit

**Purpose**: a point-in-time, quantitative audit of `seed_data.py` (the ticket/interaction corpus itself), done *independently of* `eval_queries.py`, specifically to answer a question the benchmark-coverage work cannot: is the underlying data realistic and structurally rich enough to keep teaching us something, or has decision-coverage work (4 iterations, 53 queries) been running against a corpus that's now the limiting factor? Companion to `BENCHMARK_COVERAGE_REVIEW.md`, which audits the benchmark; this document never references eval queries except in the final "why can't a query fix this" column, by design.

**Method**: every number below was computed directly from `seed_data.py`'s `TICKETS`, `INTERACTIONS`, and `CUSTOMERS` structures — no estimates, no recall from memory. See the analysis commands in this session's history for exact reproduction.

**Corpus size**: 50 tickets, 151 interactions, 12 customers, 6 RCM service categories.

---

## Dimension 1 — Category (Service) Distribution

| Category | Tickets |
|---|---|
| Claims | 9 |
| Prior Authorization | 9 |
| Accounts Receivable | 8 |
| Charge Entry | 8 |
| Eligibility | 8 |
| Payment Posting | 8 |

**Assessment: balanced.** An 8-9 spread across 6 categories is about as even as a 50-ticket corpus can be. This dimension is healthy and not a priority for expansion.

## Dimension 2 — Ticket Status Distribution

| Status | Tickets |
|---|---|
| OPEN | 13 |
| IN_PROGRESS | 13 |
| RESOLVED | 12 |
| CLOSED | 4 |
| PENDING | 4 |
| WAITING_FOR_CLIENT | 4 |

**Assessment: adequate, mildly skewed toward the active states.** OPEN/IN_PROGRESS/RESOLVED cover 76% of the corpus; the three "in-between" states (PENDING, WAITING_FOR_CLIENT, CLOSED) are thinner at 4 each. Not severe, but CLOSED — the one truly *terminal* status, and the one every "does the system correctly consider closed tickets" eval case depends on — has the fewest tickets of any status. Every CLOSED ticket in the corpus is now individually load-bearing for at least one eval case (C2, C7, E2, G6).

## Dimension 3 — Customer Distribution

| Customer | Tickets | Total Interactions | Avg Interactions/Ticket |
|---|---|---|---|
| painmed_pa | 7 | 14 | 2.0 |
| ggi_gastro | 6 | 24 | 4.0 |
| brightpath_urgent | 5 | 15 | 3.0 |
| riverside_family_medicine | 4 | 9 | 2.3 |
| sunridge_ortho | 4 | 12 | 3.0 |
| metro_cardiology | 4 | 8 | 2.0 |
| summit_neurology | 4 | 16 | 4.0 |
| pinehill_ophtho | 4 | 28 | **7.0** |
| valley_womens_health | 3 | 6 | 2.0 |
| lakeside_peds | 3 | 8 | 2.7 |
| coastal_derm | 3 | 7 | 2.3 |
| harborview_bh | 3 | 4 | **1.3** |

**Assessment: uneven, and the unevenness is concentrated, not spread out.** Ticket *counts* per customer (3-7) are reasonably close. But interaction *richness* per customer varies by more than 5x — `pinehill_ophtho` averages 7 interactions/ticket while `harborview_bh` averages 1.3. This isn't a category-level pattern (see Dimension 6) — it's specifically that one customer happens to carry almost all of the corpus's conversational depth.

**Category coverage per customer**: every customer except `painmed_pa` is missing 2-3 of the 6 service categories entirely (e.g., `valley_womens_health` has only claims/prior_auth/eligibility; `harborview_bh` has only AR/charge_entry/payment_posting). This is realistic on its own terms (a real specialty practice wouldn't generate every ticket type), but it does mean most customers' retrieval candidate pools are both small (3-4 tickets) and category-narrow — capping how much cross-category confusion risk can even exist within most single-customer pools.

## Dimension 4 — Interaction-Depth Distribution

| Interactions per ticket | # of tickets | % of corpus |
|---|---|---|
| 1 | 9 | 18% |
| 2 | 12 | 24% |
| 3 | 12 | 24% |
| 4 | 12 | 24% |
| 5 | 3 | 6% |
| 9 | 1 | 2% |
| 10 | 1 | 2% |

Average: 3.0 interactions/ticket. Median: 3.

**Assessment: the single biggest realism gap in the corpus.** 18% of all tickets (9 of 50: `A3`, `C4`, `E1`, `G1`, `P3`, `P4`, `PM1`, `PM7`, `R4`) have **exactly one interaction — a customer email with no recorded agent reply at all.** That's not "a ticket with a short history," that's a ticket that, as authored, has never been touched by staff. A production ticket that's been assigned a `category` and is sitting in the system almost always has *some* staff-side trace (an acknowledgment, a status change, a note) — a same-day, one-and-done, agent-never-responded ticket is the least realistic shape a ticket can take, and it's currently the single largest interaction-depth bucket in the corpus.

**[Pre-Stage-1 snapshot — see the Update note at the end of this document.]** As of Stage 1 (2026-08-03), 7 of these 9 (`A3`, `C4`, `E1`, `G1`, `P3`, `P4`, `R4`) have each been enriched with one agent reply; `PM1`/`PM7` remain untouched by design (frozen baseline). The table above and this paragraph describe the audit's original, pre-enrichment finding and are left as-written for the audit trail.

## Dimension 5 — Long-Running Conversation Coverage

Only 2 of 50 tickets (4%) exceed 5 interactions: `A6` (10 interactions, pinehill_ophtho, WAITING_FOR_CLIENT) and `C8` (9 interactions, pinehill_ophtho, IN_PROGRESS).

**Both belong to the same customer.** Combined with Dimension 3's finding, this means: **"long-running ticket with evolving context" is not a corpus-wide capability being tested — it's a property of two specific tickets belonging to one specific customer.** No other customer has anything resembling a long, multi-week, status-churning thread. If the pipeline has any weakness specific to long conversation histories (e.g., context-builder truncation, recency-weighting decay behaving oddly over many interactions, embedding drift across a long thread), the corpus currently offers exactly two data points to find it with, both confounded with the same customer.

## Dimension 6 — Structural Retrieval Challenges

**Currently exploited by the eval benchmark** (3 constructs):

| Construct | Tickets | Type |
|---|---|---|
| Cross-customer lookalike | C1 (riverside_family_medicine) / C5 (summit_neurology) | Near-identical subject ("Claim denied CO-45 charge exceeds fee schedule[ allowance]"), different customers |
| Same-customer near-duplicate (2-way) | P6 / P7 (both brightpath_urgent) | Both "underpayment/bundling" on a visit, no patient name to disambiguate |
| Same-customer near-duplicate (3-way) | R5 / R6 / R7 (all ggi_gastro) | Identical template ("AR follow-up needed on aged \<payer\> balance"), differ only by payer |

**Found during this audit, NOT exploited by any eval case at the time of writing** (at least 3 more constructs already existed in the corpus) — **[Update: all 3 now have eval coverage as of Stage 0, 2026-08-03 — `crosscust_a1_pm4_mri`, `crosscust_e1_pm5_eligibility`, `crosscust_p2_p5_era` in `eval_queries.py`. Table left as originally written for the audit trail.]**

| Construct | Tickets | Similarity |
|---|---|---|
| Cross-customer lookalike | **A1** (sunridge_ortho, knee MRI, "insufficient conservative treatment documentation") / **PM4** (painmed_pa, lumbar MRI, "insufficient conservative treatment") | Near-identical denial reason and body part category, different customer and joint |
| Cross-customer lookalike | **E1** (metro_cardiology) / **PM5** (painmed_pa) | Both literally "Eligibility verification failed for new patient[...]" |
| Cross-customer lookalike | **P2** (coastal_derm) / **P5** (summit_neurology) | Both an ERA-vs-contracted-rate payment mismatch |

**Assessment: this is the audit's most actionable finding.** The corpus contains *more* structural difficulty than the benchmark has ever tested — meaning some of the value the last conversation's discussion attributed to "we'd need new tickets for this" is actually available for free, at zero corpus-modification risk, by writing eval queries against constructs that already exist. This should be sequenced *before* any new near-duplicate/lookalike tickets are authored (see roadmap).

Beyond these, no other same-category, same- or cross-customer subject pairs in the corpus show meaningful overlap (checked directly against the full subject listing across all 6 categories) — the corpus doesn't have a deep reserve of undiscovered structural difficulty, just these three additional pairs.

## Dimension 7 — Conversation Realism & Continuity

- **Interaction type/sender diversity is thin.** Across all 151 interactions: 81 `customer_email`, 67 `agent_reply`, only **3 `internal_note`** — and zero interactions modeling an attachment, a status change, or any of the other real production interaction shapes. Since offline indexing only ever embeds `EMAIL`/`REPLY` content anyway (per the production integration contract), this doesn't directly hurt retrieval testing — but it does mean the corpus, if ever inspected or demoed as "realistic ticket history," reads as flatter than a real ticket timeline (which routinely has internal coordination notes interspersed).
- **Inter-interaction timing is a genuine strength, not a gap.** Gaps between interactions within a ticket range from 1 hour to 200 hours (~8 days), median 15 hours, average 29 hours — a believable mix of same-day exchanges and slower-moving follow-ups. Worth stating plainly since an audit should surface strengths too, not just gaps.
- **Interaction text itself is uniformly clean, professional prose** — no typos, no signature/disclaimer noise, no HTML, no quoted-history artifacts anywhere in the corpus's *stored* interaction content. This is a reasonable simplification (by the time something is durable ticket history, it's typically already reasonably clean) and is not double-counted as a gap here — surface-form noise on the *incoming* side is already covered by the Broken Thread Headers iteration and the still-proposed Noisy Writing iteration, both of which operate on fresh incoming emails, not stored history.

---

## Gap Analysis — prioritized by expected impact on retrieval quality, with why eval-query work alone cannot address each

| Priority | Gap | Why fresh eval queries against the existing corpus cannot fix this |
|---|---|---|
| **1** | 18% of tickets (9/50) have only one interaction, no agent reply ever recorded — **[DONE for 7/9 as of Stage 1, 2026-08-03; `PM1`/`PM7` deliberately excluded, frozen baseline]** | A new incoming email tests whether *that* email attaches correctly — it cannot retroactively give the *target ticket* a richer history. The thinness is a property of the stored ticket, which only corpus-side changes can address. |
| **2** | Long-running/evolving-context coverage is 2 tickets, both the same customer — **[still open]** | No incoming email can simulate "what if this ticket had 10 interactions spread over 2 months" — that requires the ticket to actually have that history *before* the query runs, since retrieval and context-building operate on what's already indexed. |
| **3** | Interaction richness is concentrated in 1 customer (pinehill_ophtho: 7.0 avg vs. corpus 3.0 avg, harborview_bh: 1.3 avg) — **[still open]** | Same reasoning as #1, at the customer level — no email sent *to* harborview_bh can make harborview_bh's own ticket history richer; only authoring more/deeper interactions for that customer's tickets can. |
| **4** | 3 known cross-customer lookalike pairs exist in the corpus but are untested (A1/PM4, E1/PM5, P2/P5) — **[DONE as of Stage 0, 2026-08-03]** | **This is the one gap eval-query work fully solves on its own** — no corpus change needed, just new queries against what already exists. Listed here for completeness and sequencing, not as a corpus-expansion item. |
| **5** | Only 3 structural-difficulty *families* exist total (before counting the 3 newly-found ones) — no 4-way or higher near-duplicate set, no second same-customer 2-way pair — **[still open, = proposed Stage 4]** | A new query can *probe* existing ambiguity but cannot *create* a 4th near-duplicate ticket to be ambiguous against — that requires writing a new ticket into the corpus with deliberately overlapping content. |
| **6** | Internal-note/attachment interaction-type diversity is minimal (3 of 151) — **[still open, = proposed Stage 5]** | Lower priority since these types aren't embedded/retrieved anyway per the production contract — cosmetic/realism-only, not a retrieval-quality gap. Listed for completeness. |

---

## Final Assessment

1. **Is the corpus still adequate for continued decision-coverage eval work?** Partially — categories, statuses, and customer counts are fine; interaction depth and long-running coverage are not. Four iterations of eval-query work have been implicitly relying on a corpus where "conversation history" means 3 interactions on average and "evolving context" means two tickets belonging to one customer. That's a real, quantified ceiling on what those iterations could ever have tested, independent of how well-designed the queries were.
2. **Is the imbalance a corpus-wide problem or a concentrated one?** Concentrated. Thinness (single-interaction tickets) is spread broadly across many customers/categories; richness is concentrated in one customer. Both patterns point the same direction: the corpus needs *more evenly distributed* depth, not just *more* tickets.
3. **Is there low-risk value available before touching the corpus at all?** Yes — Dimension 6 found 3 real, currently-unused structural-difficulty constructs already sitting in the existing 50 tickets. Writing eval queries against these is exactly as safe as every prior iteration (pure query addition, zero corpus risk) and should happen before or alongside any corpus-expansion work, not after.
4. **Prioritized gaps to address, highest-impact first:**
   1. Interaction-depth thinness (9 single-interaction tickets) — the broadest, most systemic gap.
   2. Long-running/evolving-context coverage concentrated in one customer.
   3. Per-customer richness imbalance (harborview_bh and similarly-thin customers).
   4. A genuinely new structural-difficulty construct (4-way near-duplicate, or a second same-customer pair) — lower priority than the above three, since the corpus already has 3 unused constructs to exploit first.
   5. (Zero corpus risk, sequence independently) New eval queries against the 3 already-existing, untested lookalike pairs.

---

*As of this writing: audit only. No changes made to `seed_data.py` or any other corpus file. A staged, risk-annotated expansion roadmap follows in a separate proposal, per the agreed process — no corpus modification happens until that roadmap is reviewed and explicitly approved.*

**Update (2026-08-03, same day): Stages 0 and 1 of `CORPUS_EXPANSION_ROADMAP.md` have since been approved and executed** — the 3 latent lookalike pairs from Dimension 6 now have eval coverage, and the 7 non-frozen single-interaction tickets from Dimension 4 (`A3`, `C4`, `E1`, `G1`, `P3`, `P4`, `R4`) have each been enriched with one agent reply (corpus now 158 interactions, up from 151). Gap #1 (single-interaction tickets) is partially addressed — 2 of 9 originally-thin tickets (`PM1`, `PM7`) remain untouched by design (frozen baseline). Gaps #2 (long-running coverage concentrated in one customer) and #3 (per-customer richness imbalance) are unaddressed. Full results: `eval_reports/2026-08-03_corpus_stage0_stage1.md`.
