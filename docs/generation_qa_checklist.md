# Generation QA Checklist

Status: **Draft — pending pilot validation**, companion to `docs/generation_prompts.md`. Runs *after* Templates 1–5 produce raw content and *before* an item is treated as frozen benchmark data. Every generated item gets a verdict; the verdict decides what happens to it, not a human eyeballing everything.

## Why not "one LLM judge checks everything"

Nine checks were asked for. Not all of them need an LLM call — some are cheaper and *more reliable* as plain code:

| Method | What it's for | Cost |
|---|---|---|
| **Deterministic (rule-based)** | Anything with an objectively correct answer from the data itself: enum membership, referential integrity, ordering, required fields, regex/leakage scans, word-count bins | Free, instant, zero false-negatives on what it checks |
| **Statistical (batch-level)** | Things that are only meaningful in aggregate: realized category/difficulty/style distributions vs. spec targets | Free, runs once per batch not per item |
| **LLM-judged (semantic)** | Genuine judgment calls a regex can't make: does this read as coherent, is this issue really this category/issue_type, is this distractor plausible | Costs a call, reserved for what actually needs it |

Where a check can be caught by a rule, it is — LLM judges are for the residual semantic judgment only. This also means the same `hard_negative`-vocabulary-imitation failure mode gets caught twice, once cheaply (category-mismatch rule) and once semantically (Judge 1), which is more robust than either alone.

## Verdict levels

Every generated item (ticket, conversation, eval query) ends in one of:

- **PASS** — all deterministic checks clean, no LLM judge flags. Enters the benchmark as-is.
- **FLAG** — a soft/semantic concern (tier feels borderline, tone ambiguous, distractor weak) — **kept**, but marked `qa_flag=true` and routed to the front of the human review queue (see "Interaction with pilot review" below).
- **FAIL** — a hard rule violated (invalid enum, broken structure, leaked internal label, ground-truth mismatch on a hard-checked field, model broke character). **Not manually patched** — regenerate that item from the same inputs/temp_id via the same template, discard the failed attempt. Patching by hand would let a broken generation setting quietly persist.

---

## 1. Customer QA (foundational)

Runs on Template 1 output. Cheap, deterministic only — no semantic judgment needed at this level.

| Check | Method | Rule | On fail |
|---|---|---|---|
| Required fields present | Rule | `name`, ≥1 `contacts[]` with non-empty `email` | FAIL |
| Email format valid | Rule | Standard email regex | FAIL |
| No duplicate emails across customers in batch | Rule | Dedup check across the whole batch (schema has a unique constraint on `email_address` — catch this before it hits the DB, not after) | FAIL |
| No duplicate practice name in batch/avoid-list | Rule | String match against batch + orchestrator's avoid-list | FLAG (regenerate that one customer is cheap) |

## 2. Ticket Seed QA

Runs on Template 2 output. Covers checklist items **#1 (category and issue_type validity)** and **#2 (category/issue_type/content consistency)**.

| Check | Method | Rule | On fail |
|---|---|---|---|
| Category is a valid enum value | Rule | Exact match against `TicketCategory` (`claims`, `payment_posting`, `prior_authorization`, `accounts_receivable`, `eligibility`, `charge_entry`) | FAIL |
| Issue Type is a valid enum value for its category | Rule | Exact match against the assigned category's Issue Type list (spec §2 / Template 2 table — the default v1 controlled vocabulary) | FAIL |
| Status is a valid enum value | Rule | Exact match against `TicketStatus` | FAIL |
| Category and issue_type match the orchestrator's assignment | Rule | Seed's `category`/`issue_type`/`status` must equal what was assigned in the prompt, not something the model substituted | FAIL |
| Closed-ticket date logic | Rule | If `status=closed`, `closed_at_offset_days` must be present and less negative (more recent) than `created_at_offset_days` | FAIL |
| Sibling distinctness (disambiguation-tier customers) | Rule | `distinguishing_details` non-empty; `claim_number`/`patient_id` differ from every sibling seed sharing category; sibling's `issue_type` is a valid value under the same category (mechanical check only — see next row for the semantic "plausibly confusable" judgment) | FAIL |
| **Sibling pairing plausibility (disambiguation-tier)** | **LLM judge (Judge 1, sibling question)** | When two sibling tickets share a category, is their issue_type pairing genuinely plausible to confuse in production (e.g. `claim_denial` + `claim_rejection_clearinghouse`), not just two different enum values that happen to share a category (e.g. `claim_denial` + `documentation_request_from_payer`)? | FLAG if judge says implausible/too-dissimilar |
| **Category & issue_type / content consistency** | **LLM judge (Judge 1, ticket-seed pass)** | Given category + issue_type + `core_issue_summary`/`procedure_description`, would an RCM domain expert file this under the assigned category *and* issue_type, or different ones? | FLAG if judge disagrees on issue_type only, FAIL if judge says "clearly wrong category" |

## 3. Conversation QA

Runs on Template 3 output. Covers checklist items **#3 (logical flow)** and **#4 (sender alternation)**.

| Check | Method | Rule | On fail |
|---|---|---|---|
| Message 1 structure | Rule | `messages[0].sender_type == "client"`, `intent_type == "initial_request"` | FAIL |
| Intent/tone/length/noise are valid enum values | Rule | Exact match against `MessageIntent`/`Tone`/`LengthBucket`/`NoiseLevel` | FAIL |
| Day offsets non-decreasing | Rule | `day_offset[i] >= day_offset[i-1]` | FAIL |
| Closed-ticket resolution shape | Rule | If `status=closed`, last message is `account_manager`+resolution-flavored intent or `client`+`thank_you`; final `day_offset` ≤ `closed_at_offset_days` | FLAG |
| Sender-alternation degeneracy | Rule | No run of 3+ consecutive messages from the same `sender_type` unless the thread has ≤3 messages total | FLAG (occasionally realistic, usually a generation tell) |
| Grounding facts echoed correctly | Rule | `claim_number`/`patient_id`/`payer`/`date_of_service` appearing in message text match the ticket seed's values (no silent drift) | FAIL |
| **Logical flow / intent-content match** | **LLM judge (Judge 1, conversation pass)** | Read the thread top-to-bottom: does each message make sense given what preceded it, no contradictions (e.g. claim number changes mid-thread), does each message's content actually match its `intent_type` tag (a `thank_you`-tagged message that's actually a new complaint is a mislabel) | FLAG if minor, FAIL if a message contradicts an established fact |

## 4. Eval Query QA

Runs on Template 4 output. Covers checklist item **#5 (query plausibility)**.

| Check | Method | Rule | On fail |
|---|---|---|---|
| Non-empty, non-degenerate text | Rule | Reasonable length, not empty/gibberish/repeated-token | FAIL |
| Label-leakage scan | Rule | `email_text` must not contain any enum literal (`hard_semantic`, `same_customer_disambiguation`, `should_match`, `claim_denial`, `missing_clinical_documentation`, or any other category/issue_type value, etc.), the words "difficulty tier"/"ground truth"/"distractor", or any `temp_id` string | FAIL — this is the single highest-value automated check, since it directly enforces Template 4's own anti-leakage instruction |
| Model broke character | Rule | Scan for refusal/meta patterns ("As an AI", "I cannot", "this is a synthetic example") — applies to **every** generated text field across all templates, not just this one | FAIL |
| Style tags are valid enum values | Rule | Exact match against `Tone`/`LengthBucket`/`NoiseLevel` | FAIL |
| **Plausibility** | *Not a separate LLM call* — Judge 2 (below) and Template 5 both read this email closely as part of their own task; an implausible/garbled email will surface as low-confidence or incoherent `reasoning` from Template 5, which itself becomes a FLAG (see §5). Not worth a third redundant "is this plausible" call. | | |

## 5. Ground-Truth & Distractor QA

Covers checklist items **#6 (does ground truth actually match)**, **#7 (distractor realism)**, and **#8 (difficulty tier satisfied)**. This section leans hardest on Template 5, since a blind independent re-derivation of the label *is* the check for #6 and #8 — formalized here as explicit gate criteria rather than left as "compare and see."

| Check | Method | Rule | On fail |
|---|---|---|---|
| **Ground-truth match (#6)** | Compare Template 4's intended target vs. Template 5's independently-judged `matched_label` | Any disagreement on *which ticket* (or null vs. non-null) | **FAIL** — hard gate, this is the single most important correctness property in the whole benchmark |
| **Difficulty tier conformance (#8)** | Compare Template 4's assigned tier vs. Template 5's independently-judged tier, **plus** rule-based signals: | | |
| — `easy` | Rule | `email_text` contains an explicit identifier matching the ticket seed (claim number, patient ref, or date of service) | FAIL if missing |
| — `moderate_paraphrase` | Rule (lexical overlap) | Token/n-gram overlap between `email_text` and the target thread should be *low* — flag if overlap is high enough that it reads as `easy` in disguise | FLAG |
| — `hard_semantic` | Rule | `email_text` must **not** contain an explicit identifier (regex for claim/patient number patterns) | FAIL if one leaked in |
| — `hard_negative` | Rule + Judge | Template 5's `should_match` must come back `false`; near-miss ticket's category (issue_type may differ from the target's — that's the point of this tier, only category-level surface similarity is required) should still show up as a `distractor_label` (i.e. genuinely confusable, not obviously unrelated) | FAIL if `should_match=true` (tier failed at its one job); FLAG if not confusable enough |
| — `boilerplate` | Rule | Low word count (see length bins, §6) but `should_match=true` in the typical case | FLAG if `should_match=false` — spec's intent is low-signal-but-real, not no-match |
| — `same_customer_disambiguation` | Rule | ≥2 real candidate tickets existed for that customer+category, with semantically similar issue types (see §2 Sibling pairing plausibility), at generation time; Template 5's `distractor_labels` non-empty | FAIL if only one real candidate existed (tier wasn't actually testable) |
| Tier disagreement (general) | Compare | Template 4 tier ≠ Template 5 tier, no rule above caught why | FLAG for manual review — this is generation *drift*, not necessarily wrong, but needs a human look |
| **Distractor realism (#7)** | Rule pre-filter | Distractor ID ≠ correct ticket ID (no self-distraction); distractor belongs to the same customer; for `hard_negative`, distractor's category matches the near-miss category (issue_type may differ); for `same_customer_disambiguation`, distractor's category matches **and** issue_type is semantically similar to the target's | FAIL if any rule pre-filter fails — a structurally-wrong distractor isn't worth judging further |
| **Distractor realism (#7), semantic** | **LLM judge (Judge 2)** | Only runs on distractors that passed the rule pre-filter: given the email + the distractor's summary, is this actually a plausible confusion a retrieval system might make, or did Template 5 just pick a nearby ticket arbitrarily? | FLAG if judge says "not actually confusable" |

## 6. Style-Tag Conformance (#9)

Cuts across Templates 3 and 4 — same bins apply to both message `body_text` and eval query `email_text`.

**Per-item (rule-based bins):**

| Tag | Signal | Default bins *(adjustable — tune after pilot review)* |
|---|---|---|
| `length_bucket` | Word count | short: 10–40 · medium: 40–120 · long: 120–300 |
| `noise_level` | Count of noise markers: common abbreviations (`pt`, `asap`, `w/`), dropped apostrophes, missing punctuation, lowercase sentence starts, misspellings | clean: 0 markers · mild: 1–4 · heavy: 5+ or run-on/no-punctuation pattern |
| `tone` | Heuristic signals: contractions, exclamation marks, informal greeting/sign-off vs. formal "Dear"/"Best regards", no contractions | If signals clearly point one way, check against tag. If **absent or conflicting**, don't guess — route to a lightweight LLM tone classification (only for ambiguous cases, not every item, to keep cost down) |

Action on mismatch: FLAG (style conformance is a realism concern, not a correctness one — doesn't invalidate the label).

**Batch-level (statistical, run once per batch, not per item):**

After each generation batch, tally realized `category` / `issue_type` / `status` / `intent_type` / `tone` / `length_bucket` / `noise_level` / `difficulty_tier` frequencies and diff against the spec's target percentages (§2, §3, §4, §5 of `benchmark_dataset_spec.md`). This doesn't fail individual items — it flags the *batch* and tells the orchestrator to bias sampling in the next batch (e.g. "last batch came out 90% `clean` noise, target is 60% — force more `mild`/`heavy` next round").

---

## New LLM judge prompts

Two new judges, not nine — most checks above are rule-based or reuse Template 5. Same copy-paste-ready convention as `generation_prompts.md` (JSON-only output, no leakage of the judging process into the verdict).

### Judge 1 — Ticket & Conversation Consistency

Runs once per ticket, after Templates 2+3 both exist, only on items that passed the rule-based pre-checks in §2/§3. When the ticket is part of a disambiguation-tier sibling pair, the sibling's seed is passed in too, so Judge 1 can also answer the sibling-pairing-plausibility question (§2) in the same call rather than needing a third judge.

```
You are a QA reviewer for a synthetic RCM support-ticket benchmark. Review
the ticket seed and its full message thread together.

Ticket seed (includes category and issue_type):
{{TICKET_SEED_JSON}}

Message thread:
{{MESSAGES_JSON}}

{{#IF SIBLING_SEED}}
This ticket has a disambiguation-tier sibling for the same customer and
category:
{{SIBLING_SEED_JSON}}
{{/IF}}

Answer:
1. Category & issue_type fit: given category "{{CATEGORY}}" and issue_type
   "{{ISSUE_TYPE}}", would an RCM billing expert file this under that exact
   category and issue_type, or does it actually belong under a different
   one (same or different category)? If different, name which.
2. Logical flow: reading top to bottom, does each message make sense given
   what came before? Flag any contradiction (e.g. a fact — claim number,
   patient, payer, amount — changing between messages without explanation).
3. Intent/content match: for each message, does its content actually match
   its labeled intent_type, or is any message mislabeled (e.g. tagged
   thank_you but actually raises a new issue)?
4. Sibling pairing plausibility (only answer if a sibling seed is given
   above, otherwise output null): is this ticket's issue_type genuinely
   plausible to confuse with the sibling's in production — similar enough
   that an AM could realistically mix them up (e.g. claim_denial vs.
   claim_rejection_clearinghouse) — or too dissimilar despite sharing a
   category (e.g. claim_denial vs. documentation_request_from_payer)?

Output ONLY a JSON object, no other text:
{
  "category_consistent": true | false,
  "suggested_category": "<enum value, or null if consistent>",
  "issue_type_consistent": true | false,
  "suggested_issue_type": "<enum value, or null if consistent>",
  "sibling_pairing_plausible": true | false | null,
  "flow_issues": ["<description>", ...],   // empty array if none
  "intent_mismatches": [{"message_index": <int>, "labeled_intent": "<...>", "issue": "<...>"}],
  "verdict": "pass" | "flag" | "fail",
  "reasoning": "<brief justification>"
}
```

### Judge 2 — Distractor Realism

Runs only on distractors that already passed the rule pre-filter in §5 (same customer, not self, category/issue_type-plausible per tier).

```
You are a QA reviewer checking whether a benchmark distractor is realistic.

Incoming email:
{{EMAIL_TEXT}}

Correct ticket (what this email is actually about):
{{CORRECT_TICKET_SUMMARY_JSON}}

Candidate distractor ticket (flagged as a plausible-but-wrong match):
{{DISTRACTOR_TICKET_SUMMARY_JSON}}

Would a retrieval system relying on textual/semantic similarity plausibly
confuse the distractor for the correct answer here — i.e. is this a
realistic near-miss, or is it only nominally similar (same category, or
even same/similar issue_type, label) with nothing in the actual content
that would cause confusion?

Output ONLY a JSON object, no other text:
{
  "is_realistic_distractor": true | false,
  "shared_surface_features": ["<e.g. same payer, similar phrasing>", ...],
  "reasoning": "<brief justification>"
}
```

---

## Traceability: requested checks → coverage

| # | Requested check | Covered by |
|---|---|---|
| 1 | Assigned category and issue_type valid | §2 rule table |
| 2 | Issue type consistent with category | §2 rule table (issue_type belongs to assigned category) + Judge 1 (category & issue_type fit question) |
| 3 | Conversation flows logically | §3 rule table + Judge 1 |
| 4 | Sender types alternate correctly | §3 rule table (alternation-degeneracy + closed-ticket shape) |
| 5 | Eval query plausible | §4 rule table (leakage/degeneracy scan); deep plausibility folded into Judge 2 / Template 5's own read, not a separate call |
| 6 | Ground-truth ticket actually matches | §5 — Template 4 vs. Template 5 agreement, hard FAIL gate |
| 7 | Distractors realistic | §5 rule pre-filter + Judge 2 |
| 8 | Difficulty tier satisfied | §5 — per-tier rule table + Template 4/5 tier agreement |
| 9 | Linguistic variation matches style tags | §6 — per-item bins (rule/heuristic) + batch-level statistical check |

## Interaction with pilot review

The spec's existing QA note calls for a ~10% manual spot-check. With this gate in place, spend that human budget more effectively than pure random sampling:

1. **Every FAIL** gets regenerated automatically — a human never needs to see these, they shouldn't reach the benchmark at all.
2. **Every FLAG** goes to the front of the manual review queue — these are exactly the cases automation itself found uncertain, so they're the highest-value use of reviewer time.
3. **A smaller random sample of PASS items** (the original 10%, now applied only to the pool that already cleared automation) catches whatever the rules and judges both missed.

This turns the flat 10%-random spot-check into a risk-weighted one, at no extra cost — the FLAG pool is a byproduct of the gate you already need to run.
