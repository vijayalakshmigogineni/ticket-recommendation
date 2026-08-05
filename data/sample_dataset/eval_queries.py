"""Structured eval query set: (incoming email) -> (expected outcome).

Consolidates the test-case scenarios worked out across dashboard testing
into a single, code-committed ground-truth file that scripts/run_eval.py can
score automatically -- no manual Accept/Reject in the Playground needed.

Each entry:
- key: short id for this eval query, used in reports
- sender_email, subject, body: the incoming email (mirrors IncomingEmail)
- conversation_id / in_reply_to (optional): set only to exercise thread-
  detection auto-attach
- expected_ticket_keys: list[str] | None -- ticket key(s) from
  data/sample_dataset/seed_data.py TICKETS this email SHOULD resolve to.
  None means "no ticket should be attached" (unknown customer, or a
  correctly-rejected no-match). A list with >1 key means any one of them
  counts as correct -- used for deliberately-ambiguous near-duplicate /
  disambiguation scenarios where more than one answer is defensible.
- difficulty: "clear" (unambiguous -- counts toward the headline accuracy
  number) | "hard" (deliberately hard/ambiguous -- tracked and reported
  separately so it doesn't dilute the headline number)
- ambiguity_type: only set on "hard" cases -- distinguishes two different
  things a single "hard" tag used to conflate: "multi_acceptable" (the case
  is genuinely ambiguous across >1 defensible ticket; declining to guess is
  defensible behavior, not just a pass/fail miss) vs. "single_answer" (there
  is exactly one correct ticket; the difficulty is a real retrieval/semantic
  ceiling, and declining or picking wrong is a genuine gap, not a shrug).
  Conflating these under one "hard cases passed" number made every report
  re-explain by hand which failures were fine and which weren't -- this
  field lets the reporting layer split them automatically.
- note: what this case is actually testing
"""

from __future__ import annotations

EVAL_QUERIES: list[dict] = [
    {
        "key": "pm1_paraphrase",
        "sender_email": "gogineni@painmedpa.com",
        "subject": "Question about claim denial - prior auth missing",
        "body": (
            "Hi, we have a claim that came back denied because the prior authorization "
            "number wasn't included. This was for one of our epidural injection "
            "procedures, patient R. Simmons. We had this authorized ahead of time so it "
            "looks like it just didn't get attached to the claim. Can you resubmit with "
            "the auth number added?"
        ),
        "expected_ticket_keys": ["PM1"],
        "difficulty": "clear",
        "note": "Semantic match despite no thread headers, paraphrased wording",
    },
    {
        "key": "pm2_autoattach",
        "sender_email": "gogineni@painmedpa.com",
        "subject": "Re: Prior auth pending for spinal cord stimulator trial",
        "body": (
            "Just sending over the conservative treatment notes you requested - let me "
            "know once you've had a chance to review."
        ),
        "conversation_id": "<conv-pm2@rcmsupport.internal>",
        "expected_ticket_keys": ["PM2"],
        "difficulty": "clear",
        "note": "Deterministic auto-attach via conversation_id, no LLM involved",
    },
    {
        "key": "remit_address_reject",
        "sender_email": "gogineni@painmedpa.com",
        "subject": "Question about updating our practice's remit address",
        "body": (
            "We're moving our billing office to a new address next month - do we need "
            "to notify payers directly, or does your team handle updating the remit-to "
            "address on file for our contracted payers?"
        ),
        "expected_ticket_keys": None,
        "difficulty": "clear",
        "note": "Hard negative - unrelated content, correct rejection expected",
    },
    {
        "key": "pm2_pm4_disambiguation",
        "sender_email": "gogineni@painmedpa.com",
        "subject": "Prior auth denied - need appeal guidance",
        "body": (
            "We got a prior auth denial citing insufficient conservative treatment "
            "documentation. Can you confirm exactly what we need to submit for the "
            "appeal?"
        ),
        "expected_ticket_keys": ["PM4"],
        "difficulty": "hard",
        "ambiguity_type": "single_answer",
        "note": "Disambiguation - PM4's wording matches exactly, PM2 is a plausible confusion",
    },
    {
        "key": "unknown_customer",
        "sender_email": "random.person@unknownclinic.com",
        "subject": "Billing question",
        "body": "Hi, can someone help me understand a recent charge on our account?",
        "expected_ticket_keys": None,
        "difficulty": "clear",
        "note": "Unknown customer short-circuit, before any retrieval runs",
    },
    {
        "key": "pm5_eligibility",
        "sender_email": "gogineni@painmedpa.com",
        "subject": "Question on patient coverage lookup",
        "body": (
            "We're trying to verify coverage for a new patient getting an epidural "
            "injection next week and the payer portal isn't showing the plan. Has this "
            "happened before - can you confirm if it's a system issue on the payer's "
            "end?"
        ),
        "expected_ticket_keys": ["PM5"],
        "difficulty": "clear",
        "note": "Category coverage: eligibility",
    },
    {
        "key": "pm6_ar",
        "sender_email": "gogineni@painmedpa.com",
        "subject": "Status check on aged United claims",
        "body": (
            "Wanted to check in on the outstanding interventional procedure claims we "
            "flagged with United a while back - any movement on those?"
        ),
        "expected_ticket_keys": ["PM6"],
        "difficulty": "clear",
        "note": "Category coverage: accounts_receivable",
    },
    {
        "key": "pm7_charge_entry",
        "sender_email": "gogineni@painmedpa.com",
        "subject": "CPT code correction needed",
        "body": (
            "One of our facet injection charges looks like it went out with the wrong "
            "CPT code - billed with the imaging guidance add-on when the note doesn't "
            "support it. Can this get fixed before it's submitted?"
        ),
        "expected_ticket_keys": ["PM7"],
        "difficulty": "clear",
        "note": "Category coverage: charge_entry",
    },
    {
        "key": "cross_customer_c1",
        "sender_email": "billing@riversidefamilymed.com",
        "subject": "Question about claim denial - CO-45",
        "body": (
            "Following up on the CO-45 denial we had - just confirming the write-off "
            "amount was correct on our end before we close the books on this one."
        ),
        "expected_ticket_keys": ["C1"],
        "difficulty": "clear",
        "note": "Cross-customer similarity guard - must not cross-attach to C5 (Summit Neurology)",
    },
    {
        "key": "near_dup_p6_p7",
        "sender_email": "urgentcare@brightpathuc.com",
        "subject": "Question about the bundling adjustment",
        "body": (
            "Following up on the bundling adjustment question we sent over recently - "
            "just want to confirm the write-off makes sense before we close it out."
        ),
        "expected_ticket_keys": ["P6", "P7"],
        "difficulty": "hard",
        "ambiguity_type": "multi_acceptable",
        "note": "Near-duplicate 2-way disambiguation, no patient named to disambiguate on",
    },
    {
        "key": "three_way_ar",
        "sender_email": "ar@ggigastro.com",
        "subject": "Checking on our AR follow-up",
        "body": (
            "Just wanted to check in on the aged balance follow-up your team has been "
            "working on for us."
        ),
        "expected_ticket_keys": ["R5", "R6", "R7"],
        "difficulty": "hard",
        "ambiguity_type": "multi_acceptable",
        "note": "3-way disambiguation across payers, no payer named to disambiguate on",
    },
    {
        "key": "c6_missing_identifiers",
        "sender_email": "urgentcare@brightpathuc.com",
        "subject": "Any update on those denied claims?",
        "body": (
            "Just checking in on the batch of claims we flagged as denied earlier this "
            "week - any progress reviewing those?"
        ),
        "expected_ticket_keys": ["C6"],
        "difficulty": "clear",
        "note": "Missing identifiers - no claim number or patient name in either message",
    },
    {
        "key": "a7_false_positive_guard",
        "sender_email": "billing@summitneurology.com",
        "subject": "Following up on the nerve study authorization",
        "body": (
            "Wanted to check whether the conservative treatment documentation we "
            "discussed was enough for the nerve conduction study authorization, or if "
            "anything else is needed."
        ),
        "expected_ticket_keys": ["A7"],
        "difficulty": "clear",
        "note": "A7 superficially resembles denial-pattern language elsewhere in the "
                "dataset but was actually a clean quick approval - should still attach "
                "correctly, not get confused into a rejection",
    },
    {
        "key": "c8_long_running_followup",
        "sender_email": "office@pinehillmd.com",
        "subject": "Checking in on cataract appeal",
        "body": "Checking in - did the peer-to-peer for the cataract appeal ever get scheduled?",
        "expected_ticket_keys": ["C8"],
        "difficulty": "clear",
        "note": "Long-running (9-interaction) thread, generic status-check wording",
    },
    {
        "key": "e6_document_submission",
        "sender_email": "office@pinehillmd.com",
        "subject": "Following up on insurance card update",
        "body": "We're following up on getting that new insurance card verified before the visit.",
        "expected_ticket_keys": ["E6"],
        "difficulty": "clear",
        "note": "Document-submission workflow follow-up",
    },
    {
        "key": "g6_no_action_confirm",
        "sender_email": "urgentcare@brightpathuc.com",
        "subject": "Confirming no action needed",
        "body": (
            "Just confirming - no further action needed on that charge correction we "
            "flagged, right?"
        ),
        "expected_ticket_keys": ["G6"],
        "difficulty": "clear",
        "note": "Informational/archive-tone ticket, already CLOSED",
    },
    {
        "key": "g5_charge_units_followup",
        "sender_email": "ar@ggigastro.com",
        "subject": "Update on charge units correction",
        "body": "Any update on fixing the unit count on that injection charge?",
        "expected_ticket_keys": ["G5"],
        "difficulty": "clear",
        "note": "Standard follow-up",
    },
    {
        "key": "ggi_no_payment_ticket",
        "sender_email": "ar@ggigastro.com",
        "subject": "Question about a short payment",
        "body": (
            "We just got a payment that seems short on one of our claims - can someone "
            "check the ERA?"
        ),
        "expected_ticket_keys": None,
        "difficulty": "clear",
        "note": "Golden Gate GI has no payment_posting ticket at all - correct no-match expected",
    },
    {
        "key": "a6_escalation",
        "sender_email": "office@pinehillmd.com",
        "subject": "Need help escalating auth delay",
        "body": (
            "We really need someone to look into the delays on this injection "
            "authorization - it's been going on far too long."
        ),
        "expected_ticket_keys": ["A6"],
        "difficulty": "clear",
        "note": "Escalation/complaint tone should still route correctly on content",
    },
    {
        "key": "c1_hard_paraphrase",
        "sender_email": "billing@riversidefamilymed.com",
        "subject": "Follow-up on pricing adjustment",
        "body": (
            "Following up on the write-off amount from that contractual pricing "
            "adjustment a while back."
        ),
        "expected_ticket_keys": ["C1"],
        "difficulty": "hard",
        "ambiguity_type": "single_answer",
        "note": "Very indirect paraphrase, no CO-45/claim#/CPT mentioned - tests semantic ceiling",
    },
    {
        "key": "a5_endoscopy_status",
        "sender_email": "ar@ggigastro.com",
        "subject": "Status on endoscopy authorization",
        "body": "Wanted to check status on the endoscopy authorization we submitted.",
        "expected_ticket_keys": ["A5"],
        "difficulty": "clear",
        "note": "Standard follow-up",
    },

    # --- THANK YOU / APPRECIATION (fresh-incoming decision coverage) ---
    # Prior to this batch, appreciation tone existed only as reply-in-thread
    # corpus content (A7, E7, PM3 endings), never as a fresh eval case. The
    # risk this category targets: a naive system treats low-topical-content
    # gratitude as "nothing to match" and wrongly returns no-match, especially
    # when the underlying ticket is already RESOLVED/CLOSED (all statuses are
    # equally eligible attach candidates per the production integration
    # contract's Decision #5).
    {
        "key": "thankyou_e7_resolved",
        "sender_email": "billing@summitneurology.com",
        "subject": "Thank you!",
        "body": (
            "Thank you so much for sorting out the coverage issue so quickly - really "
            "appreciate the fast turnaround!"
        ),
        "expected_ticket_keys": ["E7"],
        "difficulty": "clear",
        "category": "thank_you_appreciation",
        "note": "Pure appreciation against a RESOLVED eligibility ticket - tests status-eligibility Decision #5",
    },
    {
        "key": "thankyou_pm3_resolved",
        "sender_email": "gogineni@painmedpa.com",
        "subject": "Thanks for the help",
        "body": (
            "Thanks for clarifying the bundling adjustment on that facet injection "
            "payment - appreciate you checking into it."
        ),
        "expected_ticket_keys": ["PM3"],
        "difficulty": "clear",
        "category": "thank_you_appreciation",
        "note": "Appreciation against a RESOLVED payment_posting ticket",
    },
    {
        "key": "thankyou_c2_closed",
        "sender_email": "billing@sunridgeortho.com",
        "subject": "Thanks for fixing that",
        "body": (
            "Just wanted to say thanks for fixing that NPI issue on the claim - "
            "resubmission went through fine."
        ),
        "expected_ticket_keys": ["C2"],
        "difficulty": "clear",
        "category": "thank_you_appreciation",
        "note": "Appreciation against a CLOSED (true terminal-state) claims ticket - strongest test of Decision #5",
    },
    {
        "key": "thankyou_r3_ar_resolved",
        "sender_email": "billing@riversidefamilymed.com",
        "subject": "Thank you",
        "body": "Thanks for pushing that write-off through for us - one less thing to track.",
        "expected_ticket_keys": ["R3"],
        "difficulty": "clear",
        "category": "thank_you_appreciation",
        "note": "Appreciation against a RESOLVED accounts_receivable ticket - underrepresented service",
    },
    {
        "key": "thankyou_g3_chargeentry_resolved",
        "sender_email": "billing@sunridgeortho.com",
        "subject": "Appreciate the fix",
        "body": "Appreciate you catching and fixing those unit errors on the PT charge.",
        "expected_ticket_keys": ["G3"],
        "difficulty": "clear",
        "category": "thank_you_appreciation",
        "note": "Appreciation against a RESOLVED charge_entry ticket",
    },
    {
        "key": "thankyou_a4_priorauth_resolved",
        "sender_email": "office@lakesidepeds.com",
        "subject": "Thank you for expediting",
        "body": (
            "Thank you for expediting that referral authorization - the appointment "
            "went ahead as planned."
        ),
        "expected_ticket_keys": ["A4"],
        "difficulty": "clear",
        "category": "thank_you_appreciation",
        "note": "Appreciation against a RESOLVED prior_authorization ticket",
    },
    {
        "key": "thankyou_e2_closed_valley",
        "sender_email": "frontdesk@valleywomenshealth.com",
        "subject": "Thanks",
        "body": "Thanks for getting that coverage situation sorted out.",
        "expected_ticket_keys": ["E2"],
        "difficulty": "clear",
        "category": "thank_you_appreciation",
        "note": "Appreciation against a CLOSED eligibility ticket - second terminal-state test, different customer/service pairing than thankyou_c2_closed",
    },
    {
        "key": "thankyou_ambiguous_lowcontent",
        "sender_email": "billing@sunridgeortho.com",
        "subject": "Thanks",
        "body": "Thanks so much, appreciate it!",
        "expected_ticket_keys": ["A1", "R4"],
        "difficulty": "hard",
        "ambiguity_type": "multi_acceptable",
        "category": "thank_you_appreciation",
        "note": (
            "Deliberately ambiguous - zero topical anchor, sunridge_ortho has 4 "
            "candidate tickets (C2, A1, R4, G3). Acceptable set is the two "
            "currently-open/non-terminal tickets (A1, R4), on the theory that a "
            "content-free thanks is more plausibly about a live thread than one "
            "closed 15-40 days ago. Exploratory: what matters is what the system "
            "does under genuine ambiguity, not forcing a single 'correct' answer."
        ),
    },

    # --- INFORMATIONAL EMAIL (fresh-incoming decision coverage) ---
    # Prior to this batch, FYI/no-request tone existed only inside G6's own
    # thread (a reply to an already-known ticket), never as a brand-new email
    # arriving cold. The risk this category targets is the same one Thank You
    # tested for gratitude tone: a naive system treats "just letting you know,
    # no action needed" as a signal to archive/ignore rather than attach.
    {
        "key": "info_c5_claims_resolved",
        "sender_email": "billing@summitneurology.com",
        "subject": "FYI on that EMG claim",
        "body": (
            "FYI - we went ahead and adjusted off that EMG claim balance ourselves once "
            "we confirmed it was a contractual write-off, not an appealable denial. "
            "Didn't want you to think it was still outstanding."
        ),
        "expected_ticket_keys": ["C5"],
        "difficulty": "clear",
        "category": "informational_email",
        "note": "Self-resolved-by-customer informational update against a RESOLVED claims ticket",
    },
    {
        "key": "info_p2_payment_discrepancy",
        "sender_email": "billing@coastalderm.com",
        "subject": "Update on the ERA discrepancy",
        "body": (
            "Just an FYI on that ERA discrepancy we flagged - we re-ran the numbers on "
            "our end and think the $60 gap might actually be an interest payment bundled "
            "in, not a real shortfall. Wanted to pass that along in case it saves you "
            "some digging."
        ),
        "expected_ticket_keys": ["P2"],
        "difficulty": "clear",
        "category": "informational_email",
        "note": "Informational mid-investigation update, non-terminal payment_posting ticket",
    },
    {
        "key": "info_a3_priorauth_selfresolved",
        "sender_email": "frontdesk@valleywomenshealth.com",
        "subject": "Found the auth number",
        "body": (
            "Quick FYI - turns out we actually had a note of the auth number on our end "
            "after all, it was just buried in a different fax. No need to track it down "
            "from your side if it's easier: it's auth #4471-B."
        ),
        "expected_ticket_keys": ["A3"],
        "difficulty": "clear",
        "category": "informational_email",
        "note": "Informational update supplying a resolving detail, no request framed, OPEN prior_authorization ticket",
    },
    {
        "key": "info_r1_ar_update",
        "sender_email": "billing@coastalderm.com",
        "subject": "Update on the aging report numbers",
        "body": (
            "FYI on that Blue Cross aging bucket - three of those accounts actually got "
            "paid last week according to our own EOB records, so the real outstanding "
            "total is a bit lower than what we originally flagged."
        ),
        "expected_ticket_keys": ["R1"],
        "difficulty": "clear",
        "category": "informational_email",
        "note": "Informational correction to previously-shared context, OPEN accounts_receivable ticket",
    },
    {
        "key": "info_g4_chargeentry_selffixed",
        "sender_email": "ar@metrocardiologypartners.com",
        "subject": "FYI - caught that duplicate too",
        "body": (
            "Just letting you know - we caught that duplicate echo charge on our own end "
            "this morning too and flagged it in our system. Wanted you to have the full "
            "picture in case you'd already started on it."
        ),
        "expected_ticket_keys": ["G4"],
        "difficulty": "clear",
        "category": "informational_email",
        "note": "Self-caught-duplicate informational update, IN_PROGRESS charge_entry ticket",
    },
    {
        "key": "info_e3_eligibility_selfupdated",
        "sender_email": "office@lakesidepeds.com",
        "subject": "FYI - updated our records too",
        "body": (
            "FYI, we also went into our own system and corrected the insurance on file to "
            "the new plan, just so both records match going forward."
        ),
        "expected_ticket_keys": ["E3"],
        "difficulty": "clear",
        "category": "informational_email",
        "note": "Informational confirmation after agent already acted, IN_PROGRESS eligibility ticket",
    },
    {
        "key": "info_c7_claims_closed",
        "sender_email": "ar@ggigastro.com",
        "subject": "FYI on the root cause",
        "body": (
            "FYI - we dug into why that place-of-service code was wrong in the first "
            "place: our scheduling system had the wrong site flagged for that surgery "
            "center, so we've corrected it there too so it doesn't happen again on "
            "future claims."
        ),
        "expected_ticket_keys": ["C7"],
        "difficulty": "clear",
        "category": "informational_email",
        "note": "New root-cause information, CLOSED (terminal-status) claims ticket - parallel to thankyou_c2_closed",
    },
    {
        "key": "info_ambiguous_archive_boundary",
        "sender_email": "ar@metrocardiologypartners.com",
        "subject": "FYI",
        "body": "Just a quick FYI - we think everything's handled on our end now, no action needed!",
        "expected_ticket_keys": ["E1", "A2"],
        "difficulty": "hard",
        "ambiguity_type": "multi_acceptable",
        "category": "informational_email",
        "note": (
            "Deliberately ambiguous - zero topical anchor, metro_cardiology has 4 "
            "candidate tickets (C3, A2, G4, E1). Acceptable set is the two most-recently "
            "active (E1 age_days=2, A2 age_days=5), same recency-favors-live-thread logic "
            "as thankyou_ambiguous_lowcontent. Doubles as a probe of the related "
            "Archive/No-Action gap - the phrase 'no action needed' is the literal "
            "archive-trigger tone, so this tests whether the system defaults to "
            "no-match/archive on that phrasing alone with no other signal."
        ),
    },

    # --- BROKEN THREAD HEADERS (fresh-incoming decision coverage) ---
    # recommender/preprocessing.py is explicitly built to strip quoted reply/
    # forward history (plain '>' quoting, "On...wrote:", Outlook banners,
    # pasted header blocks, HTML blockquotes) so a broken-threading email's
    # new content isn't diluted by old thread text -- but no eval case had
    # ever run a real quoted-reply email through the full pipeline to confirm
    # this actually works end-to-end. None of these set conversation_id/
    # in_reply_to, simulating headers lost in transit; every body below was
    # verified against the real clean_text() function before being finalized.
    {
        "key": "broken_headers_gt_quote",
        "sender_email": "ar@metrocardiologypartners.com",
        "subject": "Re: Multiple claims denied for missing modifier 25",
        "body": (
            "Thanks - just wanted to check on timing for those resubmissions.\n\n"
            "> Reviewing all three now. You're right that the E/M codes need modifier 25 "
            "since a significant, separately identifiable service was documented "
            "alongside the procedure. I'll add the modifier and resubmit all three."
        ),
        "expected_ticket_keys": ["C3"],
        "difficulty": "clear",
        "category": "broken_thread_headers",
        "note": "Plain '>' quoting, no threading headers - verified fully stripped, only new content survives",
    },
    {
        "key": "broken_headers_on_wrote",
        "sender_email": "office@lakesidepeds.com",
        "subject": "Re: Payment posted to wrong patient account",
        "body": (
            "Got it - one follow-up: will M. Delgado's account balance reflect this by "
            "the next statement cycle?\n\n"
            "On Wed, Jul 29, 2026 at 11:40 AM, RCM Support <support@example.com> wrote:\n"
            "> Payment has been moved to the correct account. Both balances now reflect "
            "accurately. Let me know if you see anything else off."
        ),
        "expected_ticket_keys": ["P1"],
        "difficulty": "clear",
        "category": "broken_thread_headers",
        "note": "Gmail/Apple Mail 'On <date>, <name> wrote:' preamble - verified fully stripped, RESOLVED ticket",
    },
    {
        "key": "broken_headers_original_message",
        "sender_email": "admin@harborviewbh.com",
        "subject": "Re: Patient balance dispute after insurance adjustment",
        "body": (
            "Just checking in - were you able to confirm the EOB matches what the "
            "patient actually owes?\n\n"
            "-----Original Message-----\n"
            "From: RCM Support\n"
            "Sent: Tuesday, July 28, 2026\n"
            "To: Harborview Behavioral Health\n"
            "Subject: Re: Patient balance dispute\n\n"
            "Reviewing the EOB now to confirm the patient responsibility amount matches "
            "what the payer actually adjudicated before we send any further statements."
        ),
        "expected_ticket_keys": ["R2"],
        "difficulty": "clear",
        "category": "broken_thread_headers",
        "note": "Outlook '-----Original Message-----' banner - verified fully stripped",
    },
    {
        "key": "broken_headers_forwarded",
        "sender_email": "billing@coastalderm.com",
        "subject": "Fwd: Secondary insurance not verified before visit",
        "body": (
            "Hi - following up on this one, has the secondary claim actually been paid "
            "yet?\n\n"
            "-----Forwarded Message-----\n"
            "From: RCM Support\n"
            "Sent: Monday, July 20, 2026\n"
            "Subject: Re: Secondary Medicaid verification\n\n"
            "Secondary claim submitted and accepted. Will monitor for payment."
        ),
        "expected_ticket_keys": ["E4"],
        "difficulty": "clear",
        "category": "broken_thread_headers",
        "note": "Genuine forward (not reply) of an old thread, '-----Forwarded Message-----' banner - verified fully stripped, RESOLVED ticket",
    },
    {
        "key": "broken_headers_pasted_block",
        "sender_email": "office@pinehillmd.com",
        "subject": "Re: Question about which CPT code applies - need clarification",
        "body": (
            "Sending over the note now, let me know what you think.\n\n"
            "From: Office Manager\n"
            "Sent: Friday, July 31, 2026 9:14 AM\n"
            "To: RCM Support\n"
            "Subject: Re: CPT code question - dilated exam\n\n"
            "Good question - the distinction usually comes down to whether the "
            "documentation supports a comprehensive exam of all elements versus a "
            "limited number of elements for 92012. Can you send over the note so I can "
            "take a look?"
        ),
        "expected_ticket_keys": ["G7"],
        "difficulty": "clear",
        "category": "broken_thread_headers",
        "note": "Pasted From/Sent/To/Subject header block with no dashed banner - tests the pasted-block detector specifically, verified fully stripped",
    },
    {
        "key": "broken_headers_html_blockquote",
        "sender_email": "billing@riversidefamilymed.com",
        "subject": "Re: Missing charge entry for date of service 06/14",
        "body": (
            "<div>Here are the codes: CPT 99213, diagnosis M54.5. Let me know if that's "
            "enough to enter it manually.</div>"
            "<blockquote class=\"gmail_quote\">Not seeing it on our end either - looks "
            "like the charge never made it over from the EHR feed. Can you resend the "
            "encounter or confirm the CPT/diagnosis codes so we can manually enter it?"
            "</blockquote>"
        ),
        "expected_ticket_keys": ["G2"],
        "difficulty": "clear",
        "category": "broken_thread_headers",
        "note": "HTML blockquote with gmail_quote class - tests strip_html's quote-class detection, a different code path than the plain-text regex, verified fully stripped",
    },
    {
        "key": "broken_headers_early_quote_boundary",
        "sender_email": "ar@metrocardiologypartners.com",
        "subject": "Re: Multiple claims denied for missing modifier 25",
        "body": (
            "Thanks!\n\n"
            "> Reviewing all three now. You're right that the E/M codes need modifier 25\n"
            "> since a significant, separately identifiable service was documented "
            "alongside\n"
            "> the procedure. I'll add the modifier and resubmit all three."
        ),
        "expected_ticket_keys": ["C3"],
        "difficulty": "clear",
        "category": "broken_thread_headers",
        "note": (
            "Same ticket as broken_headers_gt_quote, deliberately - tests the "
            "_MIN_CHARS_BEFORE_QUOTE_CUT boundary. Verified real behavior: only a "
            "PARTIAL strip happens because the quote starts within the first 40 chars "
            "('Thanks!' is short) - the first quoted line leaks through uncut "
            "('Thanks!\\n\\n> Reviewing all three now...') before stripping catches up on "
            "a later line. Paired with the first case to isolate this exact effect."
        ),
    },
    {
        "key": "broken_headers_terse_after_strip",
        "sender_email": "billing@summitneurology.com",
        "subject": "Re: ERA payment amount doesn't match contracted rate",
        "body": (
            "Sounds good, thanks for looking into it.\n\n"
            "On Thu, Jul 23, 2026 at 4:05 PM, RCM Support <support@example.com> wrote:\n"
            "> Thanks for flagging - I'll pull the fee schedule and compare it against "
            "the ERA line item to see where the gap is coming from."
        ),
        "expected_ticket_keys": ["P5"],
        "difficulty": "hard",
        "ambiguity_type": "single_answer",
        "category": "broken_thread_headers",
        "note": (
            "Semantic-floor probe - verified the quote fully strips, leaving only "
            "'Sounds good, thanks for looking into it.' (40 chars) plus the subject "
            "line. summit_neurology has 3 other already-tested tickets (C5, E7, A7) as "
            "live competition. Tests whether near-nothing surviving content is still "
            "enough once the quoted crutch (which would have made this trivial) is "
            "correctly removed."
        ),
    },

    # --- ARCHIVE / NO-ACTION (fresh-incoming decision coverage) ---
    # g6_no_action_confirm only ever tested a reply *inside* an already-known
    # thread. These 8 test a brand-new "no action needed" email arriving cold,
    # deciding attach-vs-archive from scratch. The hard case's ground truth
    # was built by tracing real grouping/rerank scores first, applying the
    # lesson from info_ambiguous_archive_boundary's recency-only mistake.
    {
        "key": "archive_c4_claims_selfresolved",
        "sender_email": "frontdesk@valleywomenshealth.com",
        "subject": "No need to chase that claim anymore",
        "body": (
            "Actually, no need to chase this down anymore - we found the original "
            "submission confirmation ourselves and the payer's already agreed to "
            "reprocess it. You can go ahead and close this one out."
        ),
        "expected_ticket_keys": ["C4"],
        "difficulty": "clear",
        "category": "archive_no_action",
        "note": "Cold no-action-needed email, self-resolved-by-customer, OPEN claims ticket",
    },
    {
        "key": "archive_e5_eligibility_rescheduled",
        "sender_email": "urgentcare@brightpathuc.com",
        "subject": "Update on the walk-in patient",
        "body": (
            "Update - the patient decided to reschedule instead of waiting, so no need "
            "to keep chasing that eligibility check today. We'll resend when they come "
            "back in."
        ),
        "expected_ticket_keys": ["E5"],
        "difficulty": "clear",
        "category": "archive_no_action",
        "note": "Cold no-action-needed email, situation changed, OPEN eligibility ticket",
    },
    {
        "key": "archive_g1_chargeentry_noaction",
        "sender_email": "admin@harborviewbh.com",
        "subject": "About that CPT correction",
        "body": (
            "No action needed on that CPT correction after all - we pulled the note "
            "again and it does support the full 60 minutes, so the original code was "
            "actually right."
        ),
        "expected_ticket_keys": ["G1"],
        "difficulty": "clear",
        "category": "archive_no_action",
        "note": "Cold no-action-needed email, self-corrected assessment, OPEN charge_entry ticket",
    },
    {
        "key": "archive_p3_payment_noaction",
        "sender_email": "admin@harborviewbh.com",
        "subject": "Update on the Aetna check",
        "body": (
            "Never mind on that Aetna check - we just saw it hit posted in the system "
            "on our end, so no need to track it down anymore."
        ),
        "expected_ticket_keys": ["P3"],
        "difficulty": "clear",
        "category": "archive_no_action",
        "note": "Cold no-action-needed email, self-resolved, PENDING payment_posting ticket",
    },
    {
        "key": "archive_p4_payment_notduplicate",
        "sender_email": "billing@riversidefamilymed.com",
        "subject": "About the duplicate payment question",
        "body": (
            "Turns out that wasn't actually a duplicate - looks like two separate "
            "visits got billed the same day, so nothing to correct here after all, no "
            "action needed."
        ),
        "expected_ticket_keys": ["P4"],
        "difficulty": "clear",
        "category": "archive_no_action",
        "note": "Cold no-action-needed email, self-corrected assessment, OPEN payment_posting ticket",
    },
    {
        "key": "archive_r4_ar_noaction",
        "sender_email": "billing@sunridgeortho.com",
        "subject": "Update on the Cigna balance",
        "body": (
            "Actually, you can hold off on chasing that Cigna balance - three of those "
            "claims from the early June batch just posted as paid, so there's nothing "
            "left to follow up on for now."
        ),
        "expected_ticket_keys": ["R4"],
        "difficulty": "clear",
        "category": "archive_no_action",
        "note": "Cold no-action-needed email, partial resolution, PENDING accounts_receivable ticket",
    },
    {
        "key": "archive_a2_priorauth_deprioritize",
        "sender_email": "ar@metrocardiologypartners.com",
        "subject": "Update on the cath auth",
        "body": (
            "Actually, hold off on that new auth submission - the procedure ended up "
            "getting cancelled for now, so there's nothing to submit until we "
            "reschedule again. No action needed on our end for the time being."
        ),
        "expected_ticket_keys": ["A2"],
        "difficulty": "clear",
        "category": "archive_no_action",
        "note": "Cold no-action-needed email, temporary deprioritization rather than full closure, IN_PROGRESS prior_authorization ticket",
    },
    {
        "key": "archive_ambiguous_lakeside",
        "sender_email": "office@lakesidepeds.com",
        "subject": "All set",
        "body": "Just wanted to let you know everything's fine on our end now - no action needed!",
        "expected_ticket_keys": ["A4", "P1"],
        "difficulty": "hard",
        "ambiguity_type": "multi_acceptable",
        "category": "archive_no_action",
        "note": (
            "Deliberately ambiguous - zero topical anchor, lakeside_peds has 3 "
            "candidate tickets (P1, A4, E3). Ground truth built by TRACING real "
            "grouping scores first (applying the lesson from "
            "info_ambiguous_archive_boundary's recency-only mistake), not guessing: "
            "verified final_score A4=0.496, P1=0.447, E3=0.408 - a real gap, not a "
            "near-tie. Acceptable set is the two RESOLVED tickets (A4, P1), both "
            "plausible closure narratives with stronger grouping signal; E3 (still "
            "IN_PROGRESS) is excluded since a customer wouldn't plausibly say 'no "
            "action needed' about something still being actively chased."
        ),
    },

    # --- CROSS-CUSTOMER SIMILARITY (Corpus Coverage Audit Stage 0) ---
    # These 3 lookalike pairs already existed in the corpus but were never
    # tested - found during the 2026-08-03 corpus audit, not built from
    # scratch. Each verifies the same guard cross_customer_c1 already proved
    # once (C1/C5), against 3 more real, naturally-occurring lookalikes.
    # Structurally these should be easy (retrieval is customer-scoped, so the
    # decoy ticket can never even be a candidate) - the value is in
    # diversifying the regression guard, not expecting difficulty.
    {
        "key": "crosscust_a1_pm4_mri",
        "sender_email": "billing@sunridgeortho.com",
        "subject": "Following up on the knee MRI auth",
        "body": (
            "Following up on the knee MRI prior auth - the payer's denial mentioned "
            "conservative treatment documentation being insufficient. What does the "
            "appeal process look like from here?"
        ),
        "expected_ticket_keys": ["A1"],
        "difficulty": "clear",
        "category": "cross_customer_similarity",
        "note": (
            "Guards against PM4 (painmed_pa) - near-identical denial reason "
            "('insufficient conservative treatment documentation') for a different "
            "MRI joint (knee vs. lumbar), different customer. Found during the "
            "2026-08-03 corpus audit as a latent, previously-untested pair."
        ),
    },
    {
        "key": "crosscust_e1_pm5_eligibility",
        "sender_email": "ar@metrocardiologypartners.com",
        "subject": "Still showing not found on the portal",
        "body": (
            "D. Marsh's eligibility check is still coming back as not found on the "
            "portal ahead of tomorrow's visit - can someone take another look before "
            "we see the patient?"
        ),
        "expected_ticket_keys": ["E1"],
        "difficulty": "clear",
        "category": "cross_customer_similarity",
        "note": (
            "Guards against PM5 (painmed_pa) - both tickets are literally 'eligibility "
            "verification failed / plan not found' for a new patient ahead of a "
            "visit, different customer. Found during the 2026-08-03 corpus audit."
        ),
    },
    {
        "key": "crosscust_p2_p5_era",
        "sender_email": "billing@coastalderm.com",
        "subject": "Any movement on that ERA discrepancy",
        "body": (
            "Following up on that ERA discrepancy from batch 06/20 - were you able to "
            "track down where the $60 difference is coming from?"
        ),
        "expected_ticket_keys": ["P2"],
        "difficulty": "clear",
        "category": "cross_customer_similarity",
        "note": (
            "Guards against P5 (summit_neurology) - both tickets are an ERA-amount-"
            "vs-expected-rate mismatch, different customer. Found during the "
            "2026-08-03 corpus audit."
        ),
    },

    # --- EXPLICIT BUSINESS IDENTIFIERS (Phase 2, 2026-08-04) ---
    # Every prior case was deliberately written as paraphrase, to test
    # semantic understanding -- nothing has ever tested the opposite, easier
    # ceiling: if the customer just quotes the exact claim/auth number (or,
    # for services with no formal ID in this corpus, an equally unambiguous
    # exact detail), does hybrid retrieval's keyword-search half resolve it
    # trivially? All identifiers below were verified against the real
    # interaction content in seed_data.py, not invented for this batch.
    {
        "key": "pm1_explicit_claim",
        "sender_email": "gogineni@painmedpa.com",
        "subject": "Claim #93021 status",
        "body": "Hi, just checking on claim #93021 - any update on the resubmission?",
        "expected_ticket_keys": ["PM1"],
        "difficulty": "clear",
        "category": "explicit_business_identifiers",
        "note": (
            "Explicit claim-number citation, claims category. Deliberately the same "
            "ticket as pm1_paraphrase (the very first eval case, which paraphrases "
            "the same underlying issue with zero identifiers) - the pair together "
            "demonstrates the identifier-anchored ceiling vs. the semantic floor on "
            "identical ground truth."
        ),
    },
    {
        "key": "a3_explicit_claim",
        "sender_email": "frontdesk@valleywomenshealth.com",
        "subject": "Claim #90112 update",
        "body": "Wanted to check in on claim #90112 - has the auth number been added yet?",
        "expected_ticket_keys": ["A3"],
        "difficulty": "clear",
        "category": "explicit_business_identifiers",
        "note": "Explicit claim-number citation, prior_authorization category.",
    },
    {
        "key": "p5_explicit_claim",
        "sender_email": "billing@summitneurology.com",
        "subject": "Claim #59042 follow-up",
        "body": "Any update on claim #59042? Just want to confirm the reprocessing went through.",
        "expected_ticket_keys": ["P5"],
        "difficulty": "clear",
        "category": "explicit_business_identifiers",
        "note": "Explicit claim-number citation, payment_posting category.",
    },
    {
        "key": "r1_explicit_aging_bucket",
        "sender_email": "billing@coastalderm.com",
        "subject": "Update on the 120+ day Blue Cross bucket",
        "body": (
            "Following up on the $14,300 Blue Cross aging bucket - any status on "
            "those 22 accounts?"
        ),
        "expected_ticket_keys": ["R1"],
        "difficulty": "clear",
        "category": "explicit_business_identifiers",
        "note": (
            "No formal ID exists for AR tickets in this corpus, so the identifier "
            "here is an equally unambiguous exact quantitative anchor (dollar "
            "figure + account count + payer + aging bucket) instead of a code - "
            "realistic for this service, which is why the analog is used rather "
            "than forcing a claim number that wouldn't exist in real AR follow-up."
        ),
    },
    {
        "key": "pm5_explicit_patient_context",
        "sender_email": "gogineni@painmedpa.com",
        "subject": "A. Reyes eligibility - plan not found",
        "body": (
            "Follow-up on A. Reyes' eligibility check - did the 'plan not found' "
            "issue on the portal get resolved before the appointment?"
        ),
        "expected_ticket_keys": ["PM5"],
        "difficulty": "clear",
        "category": "explicit_business_identifiers",
        "note": (
            "Same reasoning as r1_explicit_aging_bucket - no numeric ID exists for "
            "this ticket, so the anchor is the exact patient name plus the "
            "ticket's own distinctive phrase ('plan not found')."
        ),
    },
    {
        "key": "g1_explicit_charge_detail",
        "sender_email": "admin@harborviewbh.com",
        "subject": "CPT correction for B. Tran, 7/24 visit",
        "body": (
            "Checking in on the CPT correction for B. Tran's 7/24 visit - did it "
            "get changed from 90837 to 90834?"
        ),
        "expected_ticket_keys": ["G1"],
        "difficulty": "clear",
        "category": "explicit_business_identifiers",
        "note": "Explicit patient+date+CPT-code citation, charge_entry category.",
    },

    # --- LENGTH & STYLE DISTRIBUTION (2026-08-05) ---
    # Production traffic is not uniformly long or uniformly short - it's a mix
    # of terse acknowledgements, medium status updates, and detailed multi-
    # paragraph explanations. These 9 cases deliberately span all three
    # lengths (short/medium/long) and multiple tones (formal, casual/
    # lowercase, numbered-question, recap-with-attachment-reference) against
    # a mix of newly-deepened tickets (P2, G2, E4) and already-validated deep
    # tickets from the prior enrichment pass (A3, R2, C4, A6), so a failure
    # can be attributed to email length/style rather than ticket novelty.
    {
        "key": "lendist_short_ack_g2",
        "sender_email": "billing@riversidefamilymed.com",
        "subject": "Re: Missing charge entry for date of service 06/14",
        "body": (
            "Thanks for catching the modifier 25 issue on that injection code - "
            "appreciate you staying on it."
        ),
        "expected_ticket_keys": ["G2"],
        "difficulty": "clear",
        "category": "length_style_distribution",
        "note": "Short (1-line) acknowledgement against G2's now 17-interaction "
                "resolved history - tests that short content still resolves cleanly "
                "on a deep ticket, not just a thin one.",
    },
    {
        "key": "lendist_short_followup_p2",
        "sender_email": "billing@coastalderm.com",
        "subject": "quick check - $60 era thing",
        "body": (
            "hey just checking in, any word yet on that $60 gap from the payer's "
            "rep?"
        ),
        "expected_ticket_keys": ["P2"],
        "difficulty": "clear",
        "category": "length_style_distribution",
        "note": "Short, casual/lowercase style against P2's still-unresolved "
                "7-interaction reconciliation - deliberately distinct wording/tone "
                "from the more formal info_p2_payment_discrepancy and "
                "crosscust_p2_p5_era cases already covering this ticket.",
    },
    {
        "key": "lendist_short_confirm_a3",
        "sender_email": "frontdesk@valleywomenshealth.com",
        "subject": "Re: Missing prior auth number on submitted claim",
        "body": (
            "Thank you - confirmed the payment posted correctly on our end too. "
            "Appreciate all the follow-through on this one."
        ),
        "expected_ticket_keys": ["A3"],
        "difficulty": "clear",
        "category": "length_style_distribution",
        "note": "Short thank-you close against A3's already-validated 8-interaction "
                "resolved history (deepened in the prior corpus-enrichment pass) - "
                "cross-checks that short content still attaches correctly on a "
                "ticket deepened earlier, not just ones deepened in this pass.",
    },
    {
        "key": "lendist_medium_update_e4",
        "sender_email": "billing@coastalderm.com",
        "subject": "Re: Secondary insurance not verified before visit",
        "body": (
            "Following up on R. Okafor's claim now that Medicare's come into the "
            "picture. Once the Medicare payment posts and the Medicaid crossover "
            "goes out, is there anything else we need to do on our end, or will "
            "you handle the resubmission end to end? He's also got another "
            "appointment next month, so we want to make sure his insurance is "
            "set up correctly going into that visit too."
        ),
        "expected_ticket_keys": ["E4"],
        "difficulty": "clear",
        "category": "length_style_distribution",
        "note": "Medium-length update carrying two distinct questions against E4's "
                "newly-deepened 12-interaction Medicare/Medicaid coordination-of-"
                "benefits history.",
    },
    {
        "key": "lendist_medium_status_r2",
        "sender_email": "admin@harborviewbh.com",
        "subject": "Re: Patient balance dispute after insurance adjustment",
        "body": (
            "Checking in on G. Ferris's payment plan - she mentioned she made her "
            "second $60 installment last week. Can you confirm that posted on "
            "your end? Also want to make sure the account reflects the remaining "
            "balance correctly since she'll have one more payment left after "
            "this one."
        ),
        "expected_ticket_keys": ["R2"],
        "difficulty": "clear",
        "category": "length_style_distribution",
        "note": "Medium status update with a specific dollar figure and payment-"
                "count reference against R2's already-validated 8-interaction "
                "payment-plan history.",
    },
    {
        "key": "lendist_medium_docref_c4",
        "sender_email": "frontdesk@valleywomenshealth.com",
        "subject": "Re: Claim denied - timely filing limit exceeded",
        "body": (
            "Wanted to follow up on claim #81044 for T. Nguyen. Has the corrected "
            "response come back yet from the payer now that they've accepted the "
            "clearinghouse delivery log as proof of timely filing? The patient's "
            "asked about her balance a couple more times, so we'd like to give "
            "her a real answer if the reprocessing has gone through."
        ),
        "expected_ticket_keys": ["C4"],
        "difficulty": "clear",
        "category": "length_style_distribution",
        "note": "Medium update citing the exact claim number and a specific proof-"
                "of-filing detail against C4's already-validated 7-interaction "
                "dispute history.",
    },
    {
        "key": "lendist_long_recap_g2",
        "sender_email": "billing@riversidefamilymed.com",
        "subject": "Full recap - H. Ruiz charge entry and modifier 25 correction",
        "body": (
            "Hi team,\n\n"
            "Wanted to send a full recap of where things stand on H. Ruiz's 6/14 "
            "visit, since this has gone through a few rounds and I want to make "
            "sure nothing slips through.\n\n"
            "The original charge (CPT 99214) never made it over from our EHR "
            "feed, so we sent the codes over manually, including CPT 20610 for "
            "the joint injection that was also done that day. The first "
            "submission came back with 20610 denied as bundled into 99214 under "
            "an NCCI edit, since there wasn't a modifier flagging it as a "
            "separate service. We agreed modifier 25 should be added since the "
            "injection genuinely was separate from the routine visit, and you "
            "resubmitted the corrected claim with that fix.\n\n"
            "A couple of questions on our end:\n"
            "1. Has the corrected claim posted payment for both codes yet, or is "
            "it still pending?\n"
            "2. We have another patient with a similar same-day E/M plus "
            "injection visit later this month - should we proactively add "
            "modifier 25 on that one too, or does it depend on the "
            "documentation each time?\n\n"
            "I've attached our internal encounter note for H. Ruiz's visit in "
            "case it's useful for reference.\n\n"
            "Thanks again for staying on top of this one,\n"
            "Dana - Riverside Family Medicine billing"
        ),
        "expected_ticket_keys": ["G2"],
        "difficulty": "clear",
        "category": "length_style_distribution",
        "note": "Long (15+ line), information-dense email with a full history "
                "recap, two explicit numbered questions, and an attachment "
                "reference against G2's newly-deepened 17-interaction charge-"
                "entry saga - the realistic 'detailed explanation' shape that was "
                "previously entirely untested in the benchmark.",
    },
    {
        "key": "lendist_long_followup_a6",
        "sender_email": "office@pinehillmd.com",
        "subject": "Re: Prior auth appeal for retina procedure - repeated "
                   "follow-up needed",
        "body": (
            "Hi,\n\n"
            "Sorry for the delay getting back to you on this - it's been a busy "
            "stretch here. To recap where we left off: B. Sorensen's intravitreal "
            "injection (CPT 67028, wet AMD) was denied for insufficient "
            "documentation, we submitted an appeal with Dr. Nakamura's note and "
            "the OCT imaging, and after a few rounds of escalation the payer "
            "asked for one more thing before they'll issue a determination - "
            "updated visual acuity from within the last 30 days.\n\n"
            "Attached is that updated visual acuity result from this week's "
            "visit. Please let us know as soon as it's submitted to the payer.\n\n"
            "The patient has now been waiting well over a month for this "
            "injection and is understandably anxious - is there any way to get a "
            "committed timeline once this last piece is in, rather than another "
            "open-ended review period?\n\n"
            "Thanks for your continued help on this,\n"
            "Front Desk - Pinehill Ophthalmology"
        ),
        "expected_ticket_keys": ["A6"],
        "difficulty": "clear",
        "category": "length_style_distribution",
        "note": "Long follow-up against A6's pre-existing 10-interaction thread "
                "(untouched by this iteration's corpus changes) - deliberately "
                "targets a ticket not touched in this pass, isolating whether "
                "email length itself, not ticket novelty, is what's being tested.",
    },
    {
        "key": "lendist_long_detailed_e4",
        "sender_email": "billing@coastalderm.com",
        "subject": "Detailed follow-up - R. Okafor Medicare/Medicaid coordination",
        "body": (
            "Hi,\n\n"
            "Following up in detail on R. Okafor's claim since this turned out "
            "to be more involved than we expected. To recap from our end: his "
            "secondary Medicaid claim came back with only a partial payment, and "
            "you flagged that he'd become Medicare-eligible back in May, meaning "
            "Medicare should now be primary instead of his old employer plan or "
            "Medicaid for any visit after his Part B effective date.\n\n"
            "A few things I wanted to check on:\n"
            "- Has the void-and-rebill to Medicare as primary been fully "
            "processed, and did Medicaid's secondary crossover post correctly "
            "after that?\n"
            "- Should we be worried we have other patients who've recently "
            "turned 65 with the exact same issue - is there a way to flag those "
            "proactively instead of finding out only after a claim gets shorted?\n"
            "- His date of birth on file is 03/14/1961 in case that helps pull up "
            "the right account quickly.\n\n"
            "Let me know what you need from us. Thanks for catching this - would "
            "have been a much bigger mess if it slipped through.\n\n"
            "Best,\n"
            "Priya - Coastal Dermatology Center"
        ),
        "expected_ticket_keys": ["E4"],
        "difficulty": "clear",
        "category": "length_style_distribution",
        "note": "Long, detailed email with a DOB reference, multiple questions, "
                "and a broader proactive-process question against E4's newly-"
                "deepened saga - tests context builder/reranker behavior when "
                "both the ticket history and the incoming email are substantial.",
    },

    # --- STAGE 1 SCENARIO-COVERAGE VALIDATION (2026-08-05) ---
    {
        "key": "g5_refund_closeloop_followup",
        "sender_email": "ar@ggigastro.com",
        "subject": "Closing the loop on the 96372 issue",
        "body": (
            "Hi - wanted to close the loop on this. Did the payer refund for K. "
            "Whitfield's claim ever clear on their end?"
        ),
        "expected_ticket_keys": ["G5"],
        "difficulty": "clear",
        "category": "length_style_distribution",
        "note": "Semantic-precision test against G5's now 19-interaction history - "
                "references a specific late-stage detail (the payer refund) rather than "
                "the ticket's original topic (unit counts), to confirm retrieval isn't "
                "just matching on the earliest, most-embedded content.",
    },
    {
        "key": "a5_urgent_dayof_followup",
        "sender_email": "ar@ggigastro.com",
        "subject": "URGENT - endoscopy auth",
        "body": "Appointment is in an hour - do we have the auth number??",
        "expected_ticket_keys": ["A5"],
        "difficulty": "clear",
        "category": "length_style_distribution",
        "note": "Genuinely urgent tone/formatting (caps subject, double question mark, "
                "extreme time compression) against A5's resolved routing-delay saga - "
                "tests whether emotionally-loaded short text still retrieves correctly, "
                "not just calm short text.",
    },
]
