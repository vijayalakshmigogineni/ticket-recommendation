# Spot-Check: Heavy Noise Level

Purpose: the full pilot (`pilot/raw/`) ended up with zero `heavy`-noise items (spec target: ~10%) — an artifact of manual sampling, not a deliberate exclusion (see `pilot/qa_report.md`). Before trusting the automated pipeline to hit that target on its own, this is a small, targeted check: does the current prompt wording actually produce *realistic* heavy noise (not gibberish), and does `generation_qa_checklist.md`'s noise-level rule classify it correctly? 3 messages + 3 eval queries, not folded into the main pilot artifacts — this is a validation exercise, not new corpus/eval data.

Noise-level rule being tested (`generation_qa_checklist.md` §6): **heavy** = 5+ markers (common abbreviations, dropped apostrophes, missing punctuation, lowercase sentence starts, misspellings) or a run-on/no-punctuation pattern.

## 3 heavy-noise messages

**M1 — Claims denial context (Sunrise Family Medicine-style scenario):**
> hey need help asap - clm for pt denied by aetna sayin no auth on file but i no we got the auth b4 the appt can u ppl check the system bc this is the 3rd time this happend this month and its really startin to hold up our AR

**M2 — Payment posting context:**
> posting issue again!! era came in wrong amt for medicaid clm still not fixed from last wk when i emailed u about it pls advise whats goin on w this acct asap bc patient callin bout their bill

**M3 — Prior authorization context:**
> need retro auth for mri done last tues doc said its urgent but insurance wants clinical notes which i already sent twice not sure whats takin so long over here everyones askin me whats the holdup

## 3 heavy-noise eval queries (deliberately spread across tiers — noise and difficulty are supposed to be independent axes per spec §5, this checks that holds up in practice)

**EQ1 — `easy` tier + heavy noise** (references `tkt_1_1` from the pilot — explicit identifiers must survive the noise):
> hey can u chk on clm CLM-88214 for pt PT-40217 aetna denied it again sayin no referral but we sent it b4 not sure whats goin on here pls advise asap

**EQ2 — `moderate_paraphrase` tier + heavy noise** (reworded version of `tkt_1_2`'s underpayment issue, no explicit identifiers):
> our medicare pmts for last mo came in lower than they shoulda been per our contract not sure if this is a postin error or somethin else pls chk into it we keep losin money on these visits

**EQ3 — `hard_semantic` tier + heavy noise** (vague version of `tkt_2_3`'s missing-charge issue — the hardest combination, vague *and* noisy):
> somethin aint right with one of our surgical clms again feels like its missin stuff idk whats goin on but pls take a look when u get a sec this keeps happenin

## Validation walkthrough

| Item | Noise markers found | Rule verdict | Tier-specific check | Realism read |
|---|---|---|---|---|
| M1 | `asap`, `clm`, `pt`, `auth`, `b4`, `AR` (6 abbreviations) + no punctuation throughout + lowercase start + misspellings (`sayin`, `happend`, `startin`, `no`→"know") | **heavy** (well over the 5-marker floor) | — | Reads as a rushed billing coordinator typing fast, not gibberish — fully parseable |
| M2 | `era`, `amt`, `clm`, `wk`, `u`, `pls`, `w`, `acct`, `asap` (9 abbreviations) + run-on, minimal punctuation + informal spellings (`goin`, `callin`) | **heavy** | — | Same — messy but coherent |
| M3 | `auth`, `mri`, `tues`, `doc` (abbreviations) + no punctuation/run-on + lowercase start + dropped apostrophes (`its`, `takin`, `askin`, `everyones`) | **heavy** | — | Same |
| EQ1 | Same style as M1/M2 | **heavy** | `easy`: contains `CLM-88214` + `PT-40217` explicitly — identifier survives the noise, rule passes | Realistic |
| EQ2 | Same style | **heavy** | `moderate_paraphrase`: reworded ("pmts," "shoulda," "postin"), no exact claim number, low lexical overlap with the original thread | Realistic |
| EQ3 | Same style | **heavy** | `hard_semantic`: no explicit identifier present, appropriately vague on top of noisy | Realistic |
| All 6 | — | — | Leakage scan: no enum literals, no meta/refusal patterns, no `temp_id` strings | Clean |

## Finding

**No bug found** — unlike the boilerplate tier, heavy noise works as designed on the first attempt: the prompt's existing "jargon-dense and typo-heavy" instruction produces text that's genuinely messy but still readable and realistic, the noise-level heuristic correctly classifies all 6 as `heavy`, and noise level held independent of difficulty tier as intended (EQ1 stayed easy — identifiers survived the noise — while EQ3 stacked vague *and* noisy without becoming incoherent).

One honest caveat, consistent with the same limitation noted throughout the pilot: "realistic, not gibberish" is my own qualitative read, not an independent human judgment — worth a quick second pair of eyes before fully trusting it, but not a blocker.

**Recommendation:** no changes needed to the heavy-noise prompt wording or the QA rule. Safe to proceed to Phase 6 (automated pipeline) and let it hit the ~10% heavy-noise target through normal sampling — this spot-check found no reason to expect problems at scale.
