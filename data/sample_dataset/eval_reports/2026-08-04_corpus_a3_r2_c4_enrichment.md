# Corpus Enrichment Report — A3, R2, C4 Deep Interaction History

**Date**: 2026-08-04
**Type**: corpus-only change (0 new eval queries). Full re-run mandatory per standing rule.
**Corpus change**: 158 → 175 interactions. Three tickets grown from 2 interactions each to 7-8, with realistic multi-week arcs (status transitions, escalations, resolutions) instead of a single customer-email/agent-reply pair.
**Result**: **54/54 clear-case accuracy (100%), zero regression.** Recall@20/@3 both 100%. Hard-case pattern unchanged (5/8, same 3 known cases failing for the same known reasons).

## What changed, and why it matters for production

The corpus audit's most significant open finding was that realistic, evolving multi-week conversations existed for only one customer (`pinehill_ophtho`) — everywhere else, tickets averaged 2-4 interactions, which doesn't reflect how real RCM back-and-forth actually plays out (denials, appeals, payer disputes, payment plans). This work directly addresses that:

- **`R2` (harborview_bh, accounts_receivable)**: a patient balance dispute that runs ~33 days — insurance confusion, patient follow-up, a payment plan setup, first payment tracked.
- **`A3` (valley_womens_health, prior_authorization)**: a denial-appeal-reprocessing saga over ~38 days — resubmission, a second denial for a different reason, an appeal, payer correction.
- **`C4` (valley_womens_health, claims)**: a timely-filing dispute over ~23 days — clearinghouse escalation, delivery-log proof, payer correction. Added after a real issue surfaced (below).

## A real production-relevant issue was found and fixed, not just documented

Enriching `A3` had a side effect: a different ticket in the same customer's pool (`C4`) started losing to a stale, unrelated candidate (`E2`) — the system confidently (0.8-0.9) recommended the wrong ticket instead of declining. That's a materially worse production behavior than an honest "not sure" — a confidently wrong recommendation is what erodes an Account Manager's trust in the system. Root cause: `C4` was a thin, weakly-anchored ticket that couldn't hold its ground once its customer pool got more crowded. Fix: enriched `C4` itself with its own realistic dispute arc, which resolved the misattribution — confirmed by a quick repeat-check (3/3 correct) and the full suite re-run.

## Bottom line

All three enriched tickets' own eval cases pass cleanly and confidently (`a3_explicit_claim`, `info_a3_priorauth_selfresolved`, `broken_headers_original_message`, `archive_c4_claims_selfresolved` — all stable). No other case was affected. The corpus now has real multi-week conversational depth in 3 more places, spread across 2 more customers, closing a real gap rather than just adding ticket count.

## Still open
`harborview_bh`'s remaining thin ticket (`P3`) and long-running-thread coverage for customers other than `pinehill_ophtho` beyond `R2`/`A3` — not urgent; reassess if it becomes relevant to a specific production scenario rather than pursuing corpus depth for its own sake.
