"""Manually-authored sample dataset for verifying the recommendation pipeline
end-to-end -- NOT synthetic-generation-pipeline output (that effort is
explicitly out of scope for this prototype). ~24 tickets across all 6
categories, 3-5 interactions each, spread over the last ~60 days, with
realistic email threading fields (message_id/conversation_id/in_reply_to).

Plain literals only, on purpose: this file is hand-authored content, read by
scripts/seed_data.py, not a generator.
"""

from __future__ import annotations

import datetime

ANCHOR_DATE = datetime.datetime(2026, 7, 30, 9, 0, tzinfo=datetime.timezone.utc)


def days_ago(n: float, hour: int = 9, minute: int = 0) -> datetime.datetime:
    dt = ANCHOR_DATE - datetime.timedelta(days=n)
    return dt.replace(hour=hour, minute=minute, second=0, microsecond=0)


CUSTOMERS = [
    {"key": "riverside_family_medicine", "name": "Riverside Family Medicine",
     "inbox_email": "billing@riversidefamilymed.com"},
    {"key": "sunridge_ortho", "name": "Sunridge Orthopedic Associates",
     "inbox_email": "billing@sunridgeortho.com"},
    {"key": "lakeside_peds", "name": "Lakeside Pediatrics Group",
     "inbox_email": "office@lakesidepeds.com"},
    {"key": "metro_cardiology", "name": "Metro Cardiology Partners",
     "inbox_email": "ar@metrocardiologypartners.com"},
    {"key": "valley_womens_health", "name": "Valley Women's Health",
     "inbox_email": "frontdesk@valleywomenshealth.com"},
    {"key": "coastal_derm", "name": "Coastal Dermatology Center",
     "inbox_email": "billing@coastalderm.com"},
    {"key": "harborview_bh", "name": "Harborview Behavioral Health",
     "inbox_email": "admin@harborviewbh.com"},
    # Dashboard-testing customer -- lets whoever's poking at the dashboard use
    # their own inbox_email in the Playground instead of memorizing one of
    # the 7 above. Customer identification lowercases the sender address
    # before matching, so this must stay lowercase to match reliably.
    {"key": "painmed_pa", "name": "PainMed PA",
     "inbox_email": "gogineni@painmedpa.com"},
    # --- Dataset-expansion customers (12 total) -- QA dimension coverage:
    # business workflow / RCM service / recommendation-scenario variety. See
    # PROJECT_PLAN or the dashboard conversation history for the coverage map.
    {"key": "brightpath_urgent", "name": "Brightpath Urgent Care",
     "inbox_email": "urgentcare@brightpathuc.com"},
    {"key": "summit_neurology", "name": "Summit Neurology Associates",
     "inbox_email": "billing@summitneurology.com"},
    {"key": "ggi_gastro", "name": "Golden Gate GI Associates",
     "inbox_email": "ar@ggigastro.com"},
    {"key": "pinehill_ophtho", "name": "Pinehill Ophthalmology",
     "inbox_email": "office@pinehillmd.com"},
]

# ---------------------------------------------------------------------------
# Tickets. `age_days` = how long ago the founding interaction happened;
# `closed_age_days` only set for RESOLVED/CLOSED tickets.
# ---------------------------------------------------------------------------
TICKETS = [
    # --- CLAIMS ---
    {"key": "C1", "customer": "riverside_family_medicine", "category": "claims",
     "subject": "Claim denied CO-45 charge exceeds fee schedule", "status": "RESOLVED",
     "age_days": 52, "closed_age_days": 45},
    {"key": "C2", "customer": "sunridge_ortho", "category": "claims",
     "subject": "Claim rejected by clearinghouse - invalid NPI", "status": "CLOSED",
     "age_days": 48, "closed_age_days": 40},
    {"key": "C3", "customer": "metro_cardiology", "category": "claims",
     "subject": "Multiple claims denied for missing modifier 25", "status": "IN_PROGRESS",
     "age_days": 9},
    {"key": "C4", "customer": "valley_womens_health", "category": "claims",
     "subject": "Claim denied - timely filing limit exceeded", "status": "IN_PROGRESS",
     "age_days": 26},

    # --- PAYMENT_POSTING ---
    {"key": "P1", "customer": "lakeside_peds", "category": "payment_posting",
     "subject": "Payment posted to wrong patient account", "status": "RESOLVED",
     "age_days": 30, "closed_age_days": 26},
    {"key": "P2", "customer": "coastal_derm", "category": "payment_posting",
     "subject": "ERA not matching expected payment amount", "status": "IN_PROGRESS",
     "age_days": 14},
    {"key": "P3", "customer": "harborview_bh", "category": "payment_posting",
     "subject": "Check payment received but not posted", "status": "PENDING",
     "age_days": 4},
    {"key": "P4", "customer": "riverside_family_medicine", "category": "payment_posting",
     "subject": "Duplicate payment posting on claim #48213", "status": "OPEN",
     "age_days": 2},

    # --- PRIOR_AUTHORIZATION ---
    {"key": "A1", "customer": "sunridge_ortho", "category": "prior_authorization",
     "subject": "Prior auth denied for knee MRI", "status": "WAITING_FOR_CLIENT",
     "age_days": 7},
    {"key": "A2", "customer": "metro_cardiology", "category": "prior_authorization",
     "subject": "Prior auth expired before procedure date", "status": "IN_PROGRESS",
     "age_days": 5},
    {"key": "A3", "customer": "valley_womens_health", "category": "prior_authorization",
     "subject": "Missing prior auth number on submitted claim", "status": "RESOLVED",
     "age_days": 38, "closed_age_days": 3},
    {"key": "A4", "customer": "lakeside_peds", "category": "prior_authorization",
     "subject": "Urgent prior auth request for specialist referral", "status": "RESOLVED",
     "age_days": 20, "closed_age_days": 17},

    # --- ACCOUNTS_RECEIVABLE ---
    {"key": "R1", "customer": "coastal_derm", "category": "accounts_receivable",
     "subject": "Aging AR report shows unpaid balance over 120 days", "status": "OPEN",
     "age_days": 14},
    {"key": "R2", "customer": "harborview_bh", "category": "accounts_receivable",
     "subject": "Patient balance dispute after insurance adjustment", "status": "RESOLVED",
     "age_days": 33, "closed_age_days": 3},
    {"key": "R3", "customer": "riverside_family_medicine", "category": "accounts_receivable",
     "subject": "Write-off request for small balance accounts", "status": "RESOLVED",
     "age_days": 35, "closed_age_days": 31},
    {"key": "R4", "customer": "sunridge_ortho", "category": "accounts_receivable",
     "subject": "AR follow-up needed on outstanding payer balance", "status": "PENDING",
     "age_days": 8},

    # --- ELIGIBILITY ---
    {"key": "E1", "customer": "metro_cardiology", "category": "eligibility",
     "subject": "Eligibility verification failed for new patient", "status": "OPEN",
     "age_days": 2},
    {"key": "E2", "customer": "valley_womens_health", "category": "eligibility",
     "subject": "Coverage termination discovered after service", "status": "CLOSED",
     "age_days": 42, "closed_age_days": 36},
    {"key": "E3", "customer": "lakeside_peds", "category": "eligibility",
     "subject": "Wrong insurance plan on file causing claim rejection", "status": "IN_PROGRESS",
     "age_days": 11},
    {"key": "E4", "customer": "coastal_derm", "category": "eligibility",
     "subject": "Secondary insurance not verified before visit", "status": "RESOLVED",
     "age_days": 23, "closed_age_days": 1},

    # --- CHARGE_ENTRY ---
    {"key": "G1", "customer": "harborview_bh", "category": "charge_entry",
     "subject": "Incorrect CPT code entered on charge", "status": "OPEN",
     "age_days": 5},
    {"key": "G2", "customer": "riverside_family_medicine", "category": "charge_entry",
     "subject": "Missing charge entry for date of service 06/14", "status": "RESOLVED",
     "age_days": 21, "closed_age_days": 1},
    {"key": "G3", "customer": "sunridge_ortho", "category": "charge_entry",
     "subject": "Charge entered with wrong units causing overbilling", "status": "RESOLVED",
     "age_days": 18, "closed_age_days": 15},
    {"key": "G4", "customer": "metro_cardiology", "category": "charge_entry",
     "subject": "Duplicate charge entry needs correction", "status": "IN_PROGRESS",
     "age_days": 6},

    # --- PainMed PA (dashboard-testing customer) ---
    {"key": "PM1", "customer": "painmed_pa", "category": "claims",
     "subject": "Claim denied for missing prior authorization on injection procedure",
     "status": "OPEN", "age_days": 2},
    {"key": "PM2", "customer": "painmed_pa", "category": "prior_authorization",
     "subject": "Prior auth pending for spinal cord stimulator trial",
     "status": "IN_PROGRESS", "age_days": 5},
    {"key": "PM3", "customer": "painmed_pa", "category": "payment_posting",
     "subject": "Payment posted short on interventional pain procedure",
     "status": "RESOLVED", "age_days": 15, "closed_age_days": 10},
    {"key": "PM4", "customer": "painmed_pa", "category": "prior_authorization",
     "subject": "Prior auth denied for lumbar MRI - insufficient conservative treatment",
     "status": "WAITING_FOR_CLIENT", "age_days": 8},
    {"key": "PM5", "customer": "painmed_pa", "category": "eligibility",
     "subject": "Eligibility verification failed for new patient - plan not found on portal",
     "status": "OPEN", "age_days": 3},
    {"key": "PM6", "customer": "painmed_pa", "category": "accounts_receivable",
     "subject": "AR follow-up needed on aging balance with United for interventional procedures",
     "status": "IN_PROGRESS", "age_days": 9},
    {"key": "PM7", "customer": "painmed_pa", "category": "charge_entry",
     "subject": "Wrong CPT code entered on facet joint injection charge",
     "status": "OPEN", "age_days": 4},

    # --- Dataset-expansion tickets (QA dimension coverage) ---
    {"key": "C5", "customer": "summit_neurology", "category": "claims",
     "subject": "Claim denied CO-45 charge exceeds fee schedule allowance",
     "status": "RESOLVED", "age_days": 40, "closed_age_days": 33},
    {"key": "C6", "customer": "brightpath_urgent", "category": "claims",
     "subject": "Batch of claims denied - need review before resubmission",
     "status": "OPEN", "age_days": 2},
    {"key": "C7", "customer": "ggi_gastro", "category": "claims",
     "subject": "Claim rejected for incorrect place of service code",
     "status": "CLOSED", "age_days": 30, "closed_age_days": 24},
    {"key": "C8", "customer": "pinehill_ophtho", "category": "claims",
     "subject": "Cataract surgery claim denied - medical necessity appeal in progress",
     "status": "IN_PROGRESS", "age_days": 35},
    {"key": "P5", "customer": "summit_neurology", "category": "payment_posting",
     "subject": "ERA payment amount doesn't match contracted rate",
     "status": "IN_PROGRESS", "age_days": 7},
    {"key": "P6", "customer": "brightpath_urgent", "category": "payment_posting",
     "subject": "Payment posted short on urgent care visit - bundling question",
     "status": "RESOLVED", "age_days": 12, "closed_age_days": 8},
    {"key": "P7", "customer": "brightpath_urgent", "category": "payment_posting",
     "subject": "Underpayment on E/M visit - possible bundling with procedure",
     "status": "RESOLVED", "age_days": 9, "closed_age_days": 5},
    {"key": "A5", "customer": "ggi_gastro", "category": "prior_authorization",
     "subject": "Prior auth needed for upper endoscopy procedure",
     "status": "RESOLVED", "age_days": 7, "closed_age_days": 1},
    {"key": "A6", "customer": "pinehill_ophtho", "category": "prior_authorization",
     "subject": "Prior auth appeal for retina procedure - repeated follow-up needed",
     "status": "WAITING_FOR_CLIENT", "age_days": 25},
    {"key": "A7", "customer": "summit_neurology", "category": "prior_authorization",
     "subject": "Prior auth for nerve conduction study - approved quickly, closing out",
     "status": "RESOLVED", "age_days": 6, "closed_age_days": 5},
    {"key": "R5", "customer": "ggi_gastro", "category": "accounts_receivable",
     "subject": "AR follow-up needed on aged Aetna balance",
     "status": "OPEN", "age_days": 11},
    {"key": "R6", "customer": "ggi_gastro", "category": "accounts_receivable",
     "subject": "AR follow-up needed on aged Cigna balance",
     "status": "IN_PROGRESS", "age_days": 9},
    {"key": "R7", "customer": "ggi_gastro", "category": "accounts_receivable",
     "subject": "AR follow-up needed on aged BCBS balance",
     "status": "OPEN", "age_days": 6},
    {"key": "E5", "customer": "brightpath_urgent", "category": "eligibility",
     "subject": "Walk-in patient eligibility could not be verified",
     "status": "OPEN", "age_days": 1},
    {"key": "E6", "customer": "pinehill_ophtho", "category": "eligibility",
     "subject": "Patient submitted new insurance card - needs re-verification",
     "status": "IN_PROGRESS", "age_days": 4},
    {"key": "E7", "customer": "summit_neurology", "category": "eligibility",
     "subject": "Coverage verification cleared up - closing out",
     "status": "RESOLVED", "age_days": 5, "closed_age_days": 4},
    {"key": "G5", "customer": "ggi_gastro", "category": "charge_entry",
     "subject": "Charge entered with wrong number of units",
     "status": "RESOLVED", "age_days": 33, "closed_age_days": 1},
    {"key": "G6", "customer": "brightpath_urgent", "category": "charge_entry",
     "subject": "FYI - charge correction already handled on our end",
     "status": "CLOSED", "age_days": 3, "closed_age_days": 2},
    {"key": "G7", "customer": "pinehill_ophtho", "category": "charge_entry",
     "subject": "Question about which CPT code applies - need clarification",
     "status": "PENDING", "age_days": 6},
]

# ---------------------------------------------------------------------------
# Interactions. `offset_hours` is relative to the ticket's founding
# interaction (age_days above), so the whole thread moves together when
# age_days changes. `sender` is "customer" | "agent" | "system".
# message_id / conversation_id follow a `<ticketkey-msgNN@domain>` convention.
# ---------------------------------------------------------------------------
INTERACTIONS: dict[str, list[dict]] = {
    "C1": [
        {"sender": "customer", "type": "customer_email", "offset_hours": 0,
         "content": "Hi team, we got a denial on claim #55201 for patient J. Alvarez, "
                    "date of service 5/28. The EOB shows CO-45 - charge exceeds fee "
                    "schedule/maximum allowable. Our billed amount was $420 for CPT 99214. "
                    "Can you confirm whether we should adjust or appeal this?"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 5,
         "content": "Thanks for flagging this. CO-45 is a contractual adjustment, not a "
                    "true denial - the payer is applying their allowed amount and the "
                    "difference has to be written off per your fee schedule agreement, "
                    "it isn't appealable. I'll process the adjustment and repost."},
        {"sender": "customer", "type": "customer_email", "offset_hours": 30,
         "content": "Got it, that makes sense given our contract with them. Please go "
                    "ahead and post the adjustment. Thank you!"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 32,
         "content": "Adjustment posted, claim balance now $0. Closing this out - let us "
                    "know if anything else comes up on this account."},
    ],
    "C2": [
        {"sender": "customer", "type": "customer_email", "offset_hours": 0,
         "content": "Claim #61190 for Dr. Higgins' patient bounced back from the "
                    "clearinghouse with rejection code 'invalid NPI - rendering provider'. "
                    "Dr. Higgins' NPI is 1447382910, not sure why it's rejecting."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 4,
         "content": "Looking at the 837 file now, it looks like the rendering NPI field "
                    "was populated with the group NPI instead of Dr. Higgins' individual "
                    "NPI. I'll correct the loop 2310B segment and resubmit."},
        {"sender": "agent", "type": "internal_note", "offset_hours": 6,
         "content": "Corrected rendering NPI mapping in clearinghouse profile for Dr. "
                    "Higgins so this doesn't recur on future claims."},
        {"sender": "customer", "type": "customer_email", "offset_hours": 50,
         "content": "Just checking - did the resubmission go through okay?"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 52,
         "content": "Yes, resubmitted claim was accepted by the clearinghouse and is now "
                    "with the payer. Closing this ticket - it'll show as a new claim status "
                    "update if there's a further issue."},
    ],
    "C3": [
        {"sender": "customer", "type": "customer_email", "offset_hours": 0,
         "content": "We have three claims (#70212, #70233, #70255) all denied this week "
                    "for the same reason - missing modifier 25 on the E/M code billed "
                    "alongside a cardiac procedure on the same day. Can someone review "
                    "and get these corrected?"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 6,
         "content": "Reviewing all three now. You're right that the E/M codes need "
                    "modifier 25 since a significant, separately identifiable service was "
                    "documented alongside the procedure. I'll add the modifier and resubmit "
                    "all three."},
        {"sender": "customer", "type": "customer_email", "offset_hours": 40,
         "content": "Appreciate it - any update on the resubmissions?"},
    ],
    "C4": [
        {"sender": "customer", "type": "customer_email", "offset_hours": 0,
         "content": "Claim #81044 for patient T. Nguyen was denied for 'timely filing "
                    "limit exceeded'. We submitted this back in March though - can you "
                    "check what happened? We have proof of original submission."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 6,
         "content": "Checking our submission logs now to see if there's a gap between "
                    "when this went out and when the payer actually received it."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 48,
         "content": "Our logs confirm claim #81044 went out through the clearinghouse "
                    "on time in March, but the payer's system shows no record of "
                    "receiving it. Filing a dispute with our transmission report "
                    "attached as proof."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 216,
         "content": "Payer pushed back, still showing no record on their end. "
                    "Escalating with the clearinghouse's own delivery confirmation as "
                    "additional proof."},
        {"sender": "customer", "type": "customer_email", "offset_hours": 384,
         "content": "Any update on this one? The patient's been asking about the "
                    "balance."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 408,
         "content": "The clearinghouse pulled their delivery log showing acceptance by "
                    "the payer's system on the original March date - sending that over "
                    "now as the decisive proof."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 552,
         "content": "Payer's system now correctly shows receipt and they've accepted "
                    "the claim for reprocessing under the original filing date. Should "
                    "see a corrected response soon."},
    ],

    "P1": [
        {"sender": "customer", "type": "customer_email", "offset_hours": 0,
         "content": "A payment of $310 that should belong to patient M. Delgado (acct "
                    "#4471) appears to have posted to a different patient's account "
                    "instead - possibly R. Delgado, similar last name. Can you check the "
                    "ERA and move it?"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 3,
         "content": "Confirmed - the payment was posted to R. Delgado's account by "
                    "mistake due to the name match. I'll reverse it and repost to M. "
                    "Delgado's account #4471 where it belongs."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 26,
         "content": "Payment has been moved to the correct account. Both balances now "
                    "reflect accurately. Let me know if you see anything else off."},
    ],
    "P2": [
        {"sender": "customer", "type": "customer_email", "offset_hours": 0,
         "content": "The ERA we received for batch 06/20 shows a total payment of $1,240 "
                    "but when I add up the line items they only total $1,180. There's a "
                    "$60 discrepancy somewhere in this remittance."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 8,
         "content": "Pulling the 835 file to reconcile line by line. Will get back to you "
                    "shortly with where the $60 difference is coming from - possibly an "
                    "interest payment or a separate overpayment recoupment line."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 48,
         "content": "Reconciled line by line - it's not an interest payment, that's ruled "
                    "out. Still short $60 with no matching adjustment code anywhere in the "
                    "835. Escalating to the payer's provider rep for a corrected remittance "
                    "breakdown."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 120,
         "content": "Provider rep is looking into it on their end. Their initial guess is "
                    "a bundling adjustment that got applied at the payer level but never "
                    "showed up as its own line item on our copy of the 835. Waiting on "
                    "their research team to confirm."},
        {"sender": "customer", "type": "customer_email", "offset_hours": 192,
         "content": "Doing our own month-end reconciliation - any word from the rep yet "
                    "on that $60?"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 216,
         "content": "Rep confirmed they're still researching - they've acknowledged the "
                    "batch total doesn't reconcile on their side either, but no firm "
                    "answer yet. Escalated internally with their claims-adjustment team."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 280,
         "content": "Still open - rep says it needs their claims-adjustment team to "
                    "actually review the batch, could be a few more days. Will keep "
                    "pushing and update as soon as I hear back."},
    ],
    "P3": [
        {"sender": "customer", "type": "customer_email", "offset_hours": 0,
         "content": "We received a paper check from Aetna for $890 last week (check "
                    "#004521) but I don't see it reflected as posted in the system yet. "
                    "Can someone confirm receipt and post it?"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 4,
         "content": "Confirming we have the check in hand - it's in the deposit queue "
                    "now and should show as posted within 1-2 business days."},
    ],
    "P4": [
        {"sender": "customer", "type": "customer_email", "offset_hours": 0,
         "content": "Looks like claim #48213 has two identical payments posted on the "
                    "same date, both for $215. That can't be right - can you check if "
                    "this was a duplicate ERA import?"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 5,
         "content": "Looking at the ERA batch now to see if it was imported twice, or "
                    "if these are two separate line items that just happen to match in "
                    "amount."},
    ],

    "A1": [
        {"sender": "customer", "type": "customer_email", "offset_hours": 0,
         "content": "The prior auth request for patient K. Bell's left knee MRI (ordered "
                    "by Dr. Osei) came back denied by the payer. Denial letter says "
                    "'insufficient conservative treatment documentation'. What do we need "
                    "to submit for a peer-to-peer or appeal?"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 5,
         "content": "We'll need at least 6 weeks of documented conservative treatment "
                    "(PT notes, NSAID trial, or injection records) before they'll "
                    "reconsider. Can you have Dr. Osei's office send over the conservative "
                    "treatment notes on file?"},
        {"sender": "agent", "type": "internal_note", "offset_hours": 6,
         "content": "Waiting on client to provide conservative treatment documentation "
                    "before we can file the appeal."},
    ],
    "A2": [
        {"sender": "customer", "type": "customer_email", "offset_hours": 0,
         "content": "Patient S. Whitfield's prior auth for the cardiac catheterization "
                    "expired on 7/15, but the procedure got rescheduled to 7/22 due to a "
                    "hospital bed shortage. Do we need a brand new auth or can this be "
                    "extended?"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 4,
         "content": "Most payers won't extend an expired auth - we'll need to submit a "
                    "new prior auth request with the updated procedure date. I'm starting "
                    "that now given the short turnaround."},
    ],
    "A3": [
        {"sender": "customer", "type": "customer_email", "offset_hours": 0,
         "content": "Claim #90112 just got rejected for 'missing prior authorization "
                    "number'. We definitely got an auth approved for this - I think we "
                    "just forgot to include the auth number on the claim submission. Can "
                    "you pull it up and add it?"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 5,
         "content": "Pulling up the original authorization on file now and will add "
                    "the number to the claim before resubmitting."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 24,
         "content": "Resubmitted claim #90112 with the authorization number added. "
                    "Will monitor for the updated response."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 192,
         "content": "Update - the claim came back denied again, this time for a "
                    "different reason: the payer says the authorization had expired "
                    "by the date of service, even though it was valid when originally "
                    "approved. We may need to appeal."},
        {"sender": "customer", "type": "customer_email", "offset_hours": 216,
         "content": "That doesn't seem right - the auth was approved for a 90-day "
                    "window and the visit was well within that. Can you push back on "
                    "this?"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 240,
         "content": "Agreed, this looks like an error on their end. Filing an appeal "
                    "with the original approval letter and the visit date attached - "
                    "will update once we hear back."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 576,
         "content": "Appeal update - the payer confirmed the original authorization "
                    "was valid all along and is correcting the denial on claim #90112. "
                    "Should see an updated response within 2 weeks."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 840,
         "content": "Claim #90112 came back paid correctly under the original "
                    "authorization. Marking this resolved."},
    ],
    "A4": [
        {"sender": "customer", "type": "customer_email", "offset_hours": 0,
         "content": "URGENT - patient needs a specialist referral prior auth approved by "
                    "end of day tomorrow, appointment is already scheduled. Can this be "
                    "expedited?"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 2,
         "content": "Submitting as an expedited/urgent request right now given the "
                    "appointment timeline. Will update you as soon as we hear back."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 20,
         "content": "Good news - the expedited prior auth was approved this morning. "
                    "Appointment can proceed as scheduled."},
    ],

    "R1": [
        {"sender": "customer", "type": "customer_email", "offset_hours": 0,
         "content": "Our aging report shows about $14,300 across 22 accounts sitting in "
                    "the 120+ day bucket, mostly Blue Cross. Can your team do a push on "
                    "these before they age further?"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 10,
         "content": "Starting a full AR follow-up campaign on the 120+ Blue Cross bucket "
                    "this week - will call on each and report back with status per "
                    "account."},
    ],
    "R2": [
        {"sender": "customer", "type": "customer_email", "offset_hours": 0,
         "content": "Patient G. Ferris is disputing a $180 balance that showed up after "
                    "the insurance adjustment posted - says their insurance told them they "
                    "owe $0. Can we get this verified before we send another statement?"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 12,
         "content": "Reviewing the EOB now to confirm the patient responsibility amount "
                    "matches what the payer actually adjudicated before we send any further "
                    "statements."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 72,
         "content": "Confirmed the payer adjudicated patient responsibility at $180, "
                    "matching what we billed - but the patient's insurance rep may have "
                    "quoted from a different EOB. Can you ask her to confirm directly "
                    "with her insurer whether that $0 quote was really for this visit?"},
        {"sender": "customer", "type": "customer_email", "offset_hours": 168,
         "content": "Patient followed up with her insurer - turns out the $0 quote was "
                    "for a different visit entirely, not this one. She's acknowledged "
                    "she owes the $180 for this claim."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 180,
         "content": "Good to have that cleared up. Sending the statement for $180 now "
                    "that it's confirmed."},
        {"sender": "customer", "type": "customer_email", "offset_hours": 480,
         "content": "Patient called back saying she can't pay the full $180 right now "
                    "- can we set up a payment plan?"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 504,
         "content": "Sure, setting up a 3-month payment plan at $60/month. Sending the "
                    "agreement over for her to sign."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 720,
         "content": "First payment posted after she signed. Will track the remaining "
                    "two installments and follow up if any are missed - closing this "
                    "out as resolved for now."},
    ],
    "R3": [
        {"sender": "customer", "type": "customer_email", "offset_hours": 0,
         "content": "We'd like to write off a batch of small-balance accounts under $10 - "
                    "there are about 40 of them and it's not worth the postage to keep "
                    "statementing. Can you process a write-off for anything under $10?"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 24,
         "content": "Processed the small-balance write-off for all 38 qualifying accounts "
                    "under the $10 threshold. Let us know if you'd like to adjust that "
                    "threshold going forward."},
    ],
    "R4": [
        {"sender": "customer", "type": "customer_email", "offset_hours": 0,
         "content": "Cigna still hasn't paid on the batch of claims from early June - "
                    "total outstanding is around $6,800. Can someone call and get a status "
                    "update on why these are stuck?"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 7,
         "content": "Calling Cigna's provider line now to get a status update on the "
                    "June batch - will follow up once I hear back."},
    ],

    "E1": [
        {"sender": "customer", "type": "customer_email", "offset_hours": 0,
         "content": "New patient D. Marsh is on the schedule for tomorrow but eligibility "
                    "verification is coming back as 'not found' on the payer portal. Can "
                    "someone double check before the appointment?"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 3,
         "content": "I'll check directly with the payer's eligibility line since the "
                    "portal seems to be having issues today - what's the patient's date "
                    "of birth and member ID?"},
    ],
    "E2": [
        {"sender": "customer", "type": "customer_email", "offset_hours": 0,
         "content": "We just found out patient L. Ostrander's coverage was actually "
                    "terminated two weeks before her visit on 6/2 - we billed the old "
                    "insurance and it's obviously denying now. How do we handle this?"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 6,
         "content": "Since coverage was terminated prior to service, we'll need to bill "
                    "the patient directly or check if she picked up new coverage we can "
                    "bill instead. Can you ask the front desk to confirm if she has other "
                    "active insurance?"},
        {"sender": "customer", "type": "customer_email", "offset_hours": 48,
         "content": "Confirmed she has no other coverage - go ahead and bill patient "
                    "directly."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 50,
         "content": "Rebilled to patient responsibility and statement generated. Closing "
                    "this out."},
    ],
    "E3": [
        {"sender": "customer", "type": "customer_email", "offset_hours": 0,
         "content": "Claim for patient A. Chu rejected because it looks like her old "
                    "insurance (United) is still on file instead of the new Cigna plan she "
                    "switched to in May. Can you update her insurance info and resubmit?"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 5,
         "content": "Updated her primary insurance to the new Cigna plan and resubmitting "
                    "the claim now."},
    ],
    "E4": [
        {"sender": "customer", "type": "customer_email", "offset_hours": 0,
         "content": "Patient R. Okafor has a secondary Medicaid plan that we never "
                    "verified before his last visit - primary paid but secondary claim is "
                    "sitting unbilled. Can we get this verified and submitted?"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 9,
         "content": "Verified the secondary Medicaid coverage is active and submitting "
                    "the crossover claim now."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 30,
         "content": "Secondary claim submitted and accepted. Will monitor for payment."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 200,
         "content": "Update - Medicaid's remittance came back with only a partial "
                    "payment. Flagging a possible coordination-of-benefits issue: Medicaid "
                    "may not have on file that this patient also has an active Medicare "
                    "plan that should have been billed as primary instead."},
        {"sender": "customer", "type": "customer_email", "offset_hours": 220,
         "content": "That's odd - we've always billed his employer plan as primary for "
                    "him before. Is Medicare something new?"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 244,
         "content": "Checked further - he turned 65 back in May and became Medicare-"
                    "eligible. Medicare Part B looks to have gone into effect just before "
                    "this visit, so it should now be primary for services on or after "
                    "that date, with his employer plan or Medicaid falling to secondary. "
                    "Confirming exact effective dates with Medicare directly."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 290,
         "content": "Confirmed with Medicare - Part B effective date is before this "
                    "visit's date of service. This claim needs to be corrected to bill "
                    "Medicare as primary, with Medicaid as secondary."},
        {"sender": "customer", "type": "customer_email", "offset_hours": 340,
         "content": "Got it - do we need to void and rebill from scratch, or can this be "
                    "corrected in place?"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 360,
         "content": "Needs a full void and rebill since the primary payer itself is "
                    "changing, not just an amount correction. Submitting the void now."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 408,
         "content": "Original claim voided. Rebilling to Medicare as primary."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 480,
         "content": "Medicare processed and paid as primary. Resubmitting the secondary "
                    "crossover to Medicaid now with Medicare's EOB attached."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 528,
         "content": "Medicaid secondary payment posted correctly. Both primary and "
                    "secondary are now paid and reconciled - closing this out as "
                    "resolved."},
    ],

    "G1": [
        {"sender": "customer", "type": "customer_email", "offset_hours": 0,
         "content": "Charge for patient B. Tran's visit on 7/24 was entered as CPT 90837 "
                    "(60 min therapy) but the documentation only supports 90834 (45 min). "
                    "Can this be corrected before it goes out?"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 4,
         "content": "Pulling the documentation now to double check the time increments "
                    "before we correct anything."},
    ],
    "G2": [
        {"sender": "customer", "type": "customer_email", "offset_hours": 0,
         "content": "We don't see a charge entered for patient H. Ruiz's visit on 6/14 - "
                    "the encounter is in our EHR but nothing showed up on our charge "
                    "report. Can you check if it fell through the cracks?"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 8,
         "content": "Not seeing it on our end either - looks like the charge never made it "
                    "over from the EHR feed. Can you resend the encounter or confirm the "
                    "CPT/diagnosis codes so we can manually enter it?"},
        {"sender": "customer", "type": "customer_email", "offset_hours": 30,
         "content": "Codes for that visit are CPT 99214, diagnosis M25.561 (right knee "
                    "pain)."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 36,
         "content": "Thanks - one thing before I enter this: the encounter notes also "
                    "reference a joint injection performed the same visit, but I don't "
                    "see a separate injection code in what you sent. Was that bundled "
                    "into the E/M intentionally, or should it be billed separately?"},
        {"sender": "customer", "type": "customer_email", "offset_hours": 60,
         "content": "Good catch, that was an oversight - yes, please add CPT 20610 for "
                    "the injection as well, that should have been on the original list."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 66,
         "content": "Got it, entering the charge now with both 99214 and 20610."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 90,
         "content": "Charge entered and submitted for the 6/14 date of service."},
        {"sender": "customer", "type": "customer_email", "offset_hours": 150,
         "content": "Just following up - has this claim gone out yet, or still pending?"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 156,
         "content": "Submitted last week, still waiting on the remittance - will update "
                    "as soon as it comes back."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 240,
         "content": "Remittance came back with a problem: 20610 was denied as bundled "
                    "into 99214 per the NCCI edit, since no modifier was applied to show "
                    "it was a significant, separately identifiable service that day."},
        {"sender": "customer", "type": "customer_email", "offset_hours": 264,
         "content": "Can we add modifier 25 and resubmit? The injection genuinely was "
                    "separate from the routine visit, not part of it."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 270,
         "content": "Agreed, that's exactly the right fix. Adding modifier 25 to the E/M "
                    "code and resubmitting the corrected claim now."},
        {"sender": "agent", "type": "internal_note", "offset_hours": 271,
         "content": "NCCI edit override applied per documented separate-procedure "
                    "justification (modifier 25, joint injection same visit as E/M). "
                    "Flagging for coding QA spot-check next cycle."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 312,
         "content": "Corrected claim resubmitted with modifier 25 attached."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 456,
         "content": "Payer accepted the resubmission - 20610 is now paying separately as "
                    "expected. Will confirm once payment actually posts."},
        {"sender": "customer", "type": "customer_email", "offset_hours": 480,
         "content": "Thanks for staying on this one, appreciate the follow-through."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 500,
         "content": "Payment posted correctly for both codes. Closing this out as "
                    "resolved."},
    ],
    "G3": [
        {"sender": "customer", "type": "customer_email", "offset_hours": 0,
         "content": "Patient W. Sato's physical therapy charge was entered as 4 units of "
                    "97110 but the note only documents 2 units (30 minutes). This is "
                    "overbilling the payer - can you correct the units?"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 5,
         "content": "Confirmed the documentation supports 2 units, not 4. Correcting the "
                    "charge now and will note the reason for the adjustment."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 24,
         "content": "Units corrected to 2 and claim has not yet been submitted, so no "
                    "rebilling needed. Closing this out."},
    ],
    "G4": [
        {"sender": "customer", "type": "customer_email", "offset_hours": 0,
         "content": "It looks like patient F. Adeyemi's echo procedure got entered twice "
                    "as separate charges on the same date of service - can you verify and "
                    "remove the duplicate before billing goes out?"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 4,
         "content": "Confirmed there are two identical charge lines for the same echo "
                    "procedure. Voiding the duplicate now before this reaches claim "
                    "submission."},
    ],

    # --- PainMed PA (dashboard-testing customer) ---
    "PM1": [
        {"sender": "customer", "type": "customer_email", "offset_hours": 0,
         "content": "We got a denial on claim #93021 for patient R. Simmons' epidural "
                    "steroid injection - the EOB says missing prior authorization number. "
                    "We definitely got this approved beforehand, can you check and resubmit "
                    "with the correct auth number?"},
    ],
    "PM2": [
        {"sender": "customer", "type": "customer_email", "offset_hours": 0,
         "content": "Following up on the prior auth request for patient T. Alvarez's spinal "
                    "cord stimulator trial - submitted last week, insurance portal still "
                    "shows pending. Can you check status?"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 6,
         "content": "Checked with the payer - they're requesting additional clinical "
                    "documentation (failed conservative treatment history) before approving. "
                    "Can you have the office send over those notes?"},
    ],
    "PM3": [
        {"sender": "customer", "type": "customer_email", "offset_hours": 0,
         "content": "The payment we received for patient K. Brooks' facet joint injection "
                    "($340) is less than the contracted rate ($480) - can you check if this "
                    "was posted correctly?"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 5,
         "content": "Reviewed the EOB - this was a bundling adjustment, the payer bundled it "
                    "with another same-day procedure per their policy. The $140 difference is "
                    "a contractual write-off, not a posting error."},
        {"sender": "customer", "type": "customer_email", "offset_hours": 28,
         "content": "Got it, thanks for checking."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 29,
         "content": "No problem, closing this out."},
    ],
    "PM4": [
        {"sender": "customer", "type": "customer_email", "offset_hours": 0,
         "content": "Prior auth for patient M. Diaz's lumbar MRI got denied - payer says "
                    "insufficient conservative treatment documentation. What do we need to "
                    "submit for the appeal?"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 5,
         "content": "Same as usual for these denials - need at least 6 weeks of documented "
                    "PT notes or an NSAID trial. Can you get those from the referring "
                    "physician's office?"},
    ],
    "PM5": [
        {"sender": "customer", "type": "customer_email", "offset_hours": 0,
         "content": "New patient A. Reyes is scheduled for an epidural steroid injection "
                    "tomorrow, but eligibility verification on the payer portal is coming "
                    "back 'plan not found'. Can someone double check before the appointment "
                    "so we're not billing an inactive plan?"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 4,
         "content": "Checked directly with the payer - the plan is active, there was just a "
                    "data sync delay on their portal. Confirmed active coverage effective "
                    "this year, safe to proceed with the appointment as scheduled."},
    ],
    "PM6": [
        {"sender": "customer", "type": "customer_email", "offset_hours": 0,
         "content": "We have about $9,200 in interventional pain procedure claims sitting "
                    "with United past 90 days with no response. Can your team follow up and "
                    "get a status update on where these are stuck?"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 10,
         "content": "Starting outreach to United's provider line today on the full batch "
                    "over 90 days - will report back with per-claim status once we get "
                    "through to a rep."},
    ],
    "PM7": [
        {"sender": "customer", "type": "customer_email", "offset_hours": 0,
         "content": "Charge for patient N. Ellis' facet joint injection on 7/26 was entered "
                    "as CPT 64493 but the documentation only supports 64490 (single level, "
                    "no imaging guidance add-on). Can this be corrected before the claim "
                    "goes out?"},
    ],

    # --- Dataset-expansion interactions ---
    "C5": [
        {"sender": "customer", "type": "customer_email", "offset_hours": 0,
         "content": "Hi team, we received a denial on claim #48830 for patient R. Delgado, "
                    "date of service 6/14. The EOB lists CO-45 - charge exceeds fee "
                    "schedule/maximum allowable. We billed $310 for CPT 95886 (needle EMG). "
                    "Should we be adjusting this off or is there an appeal angle here?"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 6,
         "content": "Thanks for sending this over. CO-45 is a contractual adjustment tied to "
                    "our negotiated rate with the payer, not a true denial, so there's no "
                    "appeal basis here - the difference between our billed amount and the "
                    "allowable is written off per the fee schedule agreement. I'll confirm "
                    "the exact allowable and get back to you with the adjustment amount."},
        {"sender": "customer", "type": "customer_email", "offset_hours": 48,
         "content": "Got it, that matches what we've seen with similar denials. Can you "
                    "confirm the allowable amount so we can post the write-off correctly on "
                    "our end?"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 150,
         "content": "Confirmed - the allowable for 95886 under your contract is $268, so the "
                    "write-off is $42. Go ahead and post that as a contractual adjustment; no "
                    "further action needed on this one. Closing this out on our end."},
    ],
    "C6": [
        {"sender": "customer", "type": "customer_email", "offset_hours": 0,
         "content": "Hi, we've had a batch of claims come back denied this week and want to "
                    "get eyes on them before we resubmit anything. Looks like a mix of "
                    "reasons - some timely filing, some missing info - but nothing's jumped "
                    "out as a single root cause yet. Can someone take a look before we start "
                    "resending?"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 5,
         "content": "Happy to help - to make sure we're reviewing the right claims, can you "
                    "send over the specific claim numbers or a denial report export from the "
                    "clearinghouse? A general date range would work too if the list isn't "
                    "pulled together yet."},
        {"sender": "customer", "type": "customer_email", "offset_hours": 20,
         "content": "We're still compiling the list from the clearinghouse portal - a few of "
                    "our front desk staff flagged different ones so I want to consolidate "
                    "before sending. Will get you the full list with claim numbers by "
                    "tomorrow."},
    ],
    "C7": [
        {"sender": "customer", "type": "customer_email", "offset_hours": 0,
         "content": "Claim #71204 for patient T. Nguyen (DOS 4/22) came back rejected - "
                    "clearinghouse is flagging an incorrect place of service code. We billed "
                    "CPT 45380 (colonoscopy w/biopsy) with POS 11, but this was actually "
                    "performed at our surgery center. Can you confirm the correct POS and "
                    "get this corrected?"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 8,
         "content": "Good catch - for procedures performed at an ambulatory surgical center, "
                    "POS should be 24, not 11. I'll correct the claim and resubmit today."},
        {"sender": "customer", "type": "customer_email", "offset_hours": 20,
         "content": "Quick question while you're in there - does this affect any of our "
                    "other claims from that same surgery center visit, or just this one?"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 26,
         "content": "Just this one - the others from that visit were already coded with "
                    "POS 24, this was the only one flagged."},
        {"sender": "customer", "type": "customer_email", "offset_hours": 60,
         "content": "Thanks - any sense of turnaround once it's resubmitted? Just want to "
                    "flag it for our AR aging report."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 120,
         "content": "Resubmitted claim went through clean with POS 24 and processed for "
                    "payment - no further action needed. Closing this out."},
    ],
    "C8": [
        {"sender": "customer", "type": "customer_email", "offset_hours": 0,
         "content": "We received a denial on the cataract surgery claim for patient "
                    "H. Okafor, DOS 5/1, CPT 66984. Payer denied for medical necessity, "
                    "stating the chart doesn't support significant visual impairment. We'd "
                    "like to appeal - can you help us put this together?"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 10,
         "content": "Absolutely, we can work on this appeal. To support medical necessity "
                    "we'll need the pre-op visual acuity results, glare/BAT testing if "
                    "performed, and the physician's documentation of functional impact on "
                    "daily activities. Can you send those over?"},
        {"sender": "customer", "type": "customer_email", "offset_hours": 60,
         "content": "Attached the visual acuity chart (20/70 corrected OD), glare testing "
                    "results, and Dr. Whitfield's note on how the vision loss is affecting "
                    "the patient's driving and reading. Let us know if you need anything "
                    "else."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 96,
         "content": "This is solid documentation. I've put together the appeal letter "
                    "referencing the visual acuity and functional impact and submitted it "
                    "to the payer today. I'll keep you posted once we hear back."},
        {"sender": "customer", "type": "customer_email", "offset_hours": 250,
         "content": "Checking in on this - it's been about a week and a half since the "
                    "appeal went in. Have we heard anything back from the payer yet?"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 270,
         "content": "Update - the payer reviewed the appeal and is requesting a "
                    "peer-to-peer review between Dr. Whitfield and their medical director "
                    "before they'll reconsider. I'm reaching out to get that scheduled "
                    "now."},
        {"sender": "customer", "type": "customer_email", "offset_hours": 450,
         "content": "This is our second time following up and it's been nearly a month "
                    "now since the original denial. The patient is understandably getting "
                    "anxious about getting this resolved - can we get the peer-to-peer "
                    "locked in?"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 470,
         "content": "Completely understand the frustration, and I'm sorry this has "
                    "dragged on. I escalated with the payer's scheduling line and the "
                    "peer-to-peer is now set for this Thursday - Dr. Whitfield has it on "
                    "the calendar. I'll follow up right after with the outcome."},
        {"sender": "customer", "type": "customer_email", "offset_hours": 600,
         "content": "Thanks for the update - we'll hold tight for Thursday. Appreciate "
                    "you pushing to get this scheduled."},
    ],
    "P5": [
        {"sender": "customer", "type": "customer_email", "offset_hours": 0,
         "content": "The ERA we received for patient M. Castellano's visit (claim #59042, "
                    "CPT 99215) shows a payment of $94, but our contracted rate with this "
                    "payer for that code is $138. Can you take a look and confirm whether "
                    "this was posted correctly?"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 10,
         "content": "Thanks for flagging - I'll pull the fee schedule and compare it "
                    "against the ERA line item to see where the gap is coming from."},
        {"sender": "customer", "type": "customer_email", "offset_hours": 70,
         "content": "Appreciate it - also want to flag this payer has shorted us on a "
                    "couple other claims recently, so if it's a systemic rate issue on "
                    "their end we may want to escalate more broadly."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 120,
         "content": "Confirmed there's a discrepancy - the payer applied an outdated fee "
                    "schedule version. I'm submitting a corrected claim/reconsideration "
                    "request for the $44 difference and will also flag the pattern with "
                    "our payer rep to check for a broader rate loading issue."},
    ],
    "P6": [
        {"sender": "customer", "type": "customer_email", "offset_hours": 0,
         "content": "Payment posted short on patient K. Ramos's visit (DOS 6/2) - we "
                    "billed CPT 99213 (E/M) along with 12002 (laceration repair) but only "
                    "got paid for the repair code. Is the E/M getting bundled in here?"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 20,
         "content": "Looks like the payer applied an NCCI edit bundling the E/M into the "
                    "procedure since no separate, significant issue was documented beyond "
                    "the laceration. If there was a distinct problem addressed at the same "
                    "visit, we'd need modifier 25 on the E/M with supporting documentation "
                    "to unbundle it."},
        {"sender": "customer", "type": "customer_email", "offset_hours": 70,
         "content": "Checked the note - it really was just the laceration, no separate "
                    "issue addressed. That makes sense then, we'll leave it as posted. "
                    "Thanks for confirming."},
    ],
    "P7": [
        {"sender": "customer", "type": "customer_email", "offset_hours": 0,
         "content": "We're showing an underpayment on patient D. Whitfield's visit (DOS "
                    "6/10) - billed CPT 99214 (E/M) plus 94640 (nebulizer treatment), but "
                    "the E/M paid at $0. Possible bundling with the treatment?"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 15,
         "content": "Similar to what we've seen before - if the E/M and the nebulizer "
                    "treatment were for the same straightforward issue, the payer will "
                    "bundle them. If the physician addressed something separate and "
                    "significant during that visit, modifier 25 with documentation would "
                    "support unbundling the E/M."},
        {"sender": "customer", "type": "customer_email", "offset_hours": 60,
         "content": "Reviewed the chart - the physician also assessed and adjusted the "
                    "patient's asthma action plan, which is separate from the nebulizer "
                    "treatment itself. We'll add modifier 25 and documentation and "
                    "resubmit."},
    ],
    "A5": [
        {"sender": "customer", "type": "customer_email", "offset_hours": 0,
         "content": "Patient S. Delacruz needs an upper endoscopy (CPT 43239) scheduled "
                    "for next week - can you get prior authorization submitted with United "
                    "Healthcare? Diagnosis is chronic GERD with dysphagia."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 10,
         "content": "On it - submitting the prior auth request now with the GERD/"
                    "dysphagia diagnosis and prior PPI trial history. Will update once we "
                    "hear back."},
        {"sender": "customer", "type": "customer_email", "offset_hours": 40,
         "content": "Any update? Just want to make sure we're clear before the "
                    "appointment date."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 55,
         "content": "Still pending with the payer - their standard turnaround is 5-7 "
                    "business days. I'll follow up with them directly tomorrow if we "
                    "haven't heard back and keep you posted."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 80,
         "content": "Followed up with the payer - turns out the request never actually "
                    "made it to clinical review, it got stuck in their general intake "
                    "queue due to a routing issue on their end, not a denial. Escalating "
                    "now to get it properly routed given the appointment's coming up "
                    "fast."},
        {"sender": "customer", "type": "customer_email", "offset_hours": 90,
         "content": "That's frustrating to hear, but appreciate you catching it - "
                    "appointment's in 3 days, any way to expedite now that it's routed "
                    "correctly?"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 100,
         "content": "Requested expedited handling given the timeline - payer said "
                    "they'd try to turn it around within 48 hours given the "
                    "circumstances."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 130,
         "content": "Still no word - called again and confirmed it's actually in "
                    "clinical review now, not stuck. Should hear back very soon."},
        {"sender": "customer", "type": "customer_email", "offset_hours": 150,
         "content": "Appointment's tomorrow morning - anything?"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 156,
         "content": "Just got word - approved! Authorization number is UHC-4471829, "
                    "confirmed valid through the appointment date. You're clear for "
                    "tomorrow."},
        {"sender": "customer", "type": "customer_email", "offset_hours": 160,
         "content": "That's a huge relief, thank you for pushing on this - really "
                    "appreciate the quick work at the end there."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 165,
         "content": "Glad it came together in time. Closing this out - let us know if "
                    "you need anything for the follow-up visit."},
    ],
    "A6": [
        {"sender": "customer", "type": "customer_email", "offset_hours": 0,
         "content": "Prior auth for patient B. Sorensen's intravitreal injection (CPT "
                    "67028, wet AMD) was denied - payer says insufficient documentation "
                    "of diagnosis. Can you help get this turned around? Patient needs the "
                    "injection soon."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 12,
         "content": "I'll take a look at the denial letter and get the appeal started. "
                    "Can you send over the most recent OCT imaging and the retina "
                    "specialist's note confirming the wet AMD diagnosis?"},
        {"sender": "customer", "type": "customer_email", "offset_hours": 36,
         "content": "Attached the OCT results and Dr. Nakamura's note. Please let us "
                    "know as soon as this is submitted."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 80,
         "content": "Appeal submitted with the OCT imaging and clinical note. Payer's "
                    "stated turnaround is 10 business days."},
        {"sender": "customer", "type": "customer_email", "offset_hours": 280,
         "content": "This is the second time we're reaching out on this - it's been over "
                    "two weeks and the patient still hasn't been able to get the "
                    "injection. Any movement on the payer's end?"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 300,
         "content": "Apologies for the delay - I followed up with the payer today and "
                    "they say the appeal is still in clinical review. I've asked for "
                    "expedited handling given the treatment delay risk to the patient."},
        {"sender": "agent", "type": "internal_note", "offset_hours": 305,
         "content": "Internal note: called payer provider line again re: expedited "
                    "review - rep confirmed case flagged urgent but no committed decision "
                    "date. Following up with our payer relations contact directly rather "
                    "than the general queue."},
        {"sender": "customer", "type": "customer_email", "offset_hours": 450,
         "content": "This is now the third time we've had to follow up about this. A "
                    "month is an unreasonable amount of time for a patient with active "
                    "wet AMD to be waiting on treatment - can someone escalate this on "
                    "your side today?"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 460,
         "content": "I completely understand the frustration and I'm sorry this has "
                    "dragged on this long. I escalated directly with the payer's prior "
                    "auth department this morning. They're asking for one more piece - "
                    "updated visual acuity from within the last 30 days - before they'll "
                    "issue a determination. Can you send that over as soon as it's "
                    "available?"},
        {"sender": "customer", "type": "customer_email", "offset_hours": 590,
         "content": "Understood - we're pulling the updated visual acuity now and will "
                    "get it over to you within the next day or two."},
    ],
    "A7": [
        {"sender": "customer", "type": "customer_email", "offset_hours": 0,
         "content": "Prior auth needed for patient L. Bianchi's nerve conduction study "
                    "(CPT 95910) - payer notes usually ask about conservative treatment "
                    "history before approving, so wanted to get this in early in case "
                    "they come back with questions on that."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 4,
         "content": "Submitted the request with the conservative treatment history "
                    "included (PT and NSAID trial documented in the chart) - good news, "
                    "the payer approved it same-day, no additional questions asked. Auth "
                    "is on file through the end of next month."},
        {"sender": "customer", "type": "customer_email", "offset_hours": 20,
         "content": "That's great news, thank you for turning this around so fast - "
                    "really appreciate it!"},
    ],
    "R5": [
        {"sender": "customer", "type": "customer_email", "offset_hours": 0,
         "content": "Can your team push on our aged Aetna balance? We've got about "
                    "$18,400 outstanding across 14 accounts, several sitting past 90 "
                    "days. Would like a status update on where things stand with "
                    "follow-up calls."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 15,
         "content": "We'll start working through the Aetna aging bucket - I'll pull the "
                    "list of 14 accounts and prioritize by balance and age, then report "
                    "back with status on each."},
        {"sender": "customer", "type": "customer_email", "offset_hours": 100,
         "content": "Thanks - any early read on which ones are moving? A couple of the "
                    "larger balances are ones we're especially watching."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 180,
         "content": "Made calls on 6 of the 14 so far - 2 are reprocessing after we "
                    "cleared up a COB issue, 3 needed corrected claims resubmitted, and 1 "
                    "is confirmed patient responsibility. Will continue through the rest "
                    "of the list this week."},
    ],
    "R6": [
        {"sender": "customer", "type": "customer_email", "offset_hours": 0,
         "content": "Following up on our aged Cigna balance - we're showing roughly "
                    "$11,200 outstanding across 9 accounts, most past the 60-day mark. "
                    "Can your team get some calls going on these?"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 10,
         "content": "Starting on the Cigna bucket now - pulling the 9 accounts and will "
                    "work through them by balance/age priority, same as we're doing with "
                    "your other payer follow-ups."},
        {"sender": "customer", "type": "customer_email", "offset_hours": 90,
         "content": "Appreciate it - let us know if any of these need something from "
                    "our side like updated documentation."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 150,
         "content": "Update - worked 5 of the 9 so far. 2 were missing referral "
                    "documentation on Cigna's end that we've now supplied, 2 are in "
                    "active reprocessing, and 1 needed a corrected claim which is "
                    "resubmitted. Continuing on the rest."},
    ],
    "R7": [
        {"sender": "customer", "type": "customer_email", "offset_hours": 0,
         "content": "Can we get a push on our aged BCBS balance too? Looks like about "
                    "$7,600 across 6 accounts sitting past 45 days."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 10,
         "content": "We'll add the BCBS accounts to this week's AR follow-up alongside "
                    "the Aetna and Cigna work already in progress - I'll pull the 6 "
                    "accounts and start calls."},
        {"sender": "customer", "type": "customer_email", "offset_hours": 80,
         "content": "Sounds good, thanks. This one's a smaller bucket than the others "
                    "but still want to keep it moving before it ages further."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 130,
         "content": "Worked all 6 BCBS accounts - 3 reprocessing after a timely filing "
                    "appeal, 2 confirmed paid but misapplied to the wrong account "
                    "internally (corrected now), and 1 still pending payer response. "
                    "Will keep monitoring that last one."},
    ],
    "E5": [
        {"sender": "customer", "type": "customer_email", "offset_hours": 0,
         "content": "Walk-in patient at the front desk right now, no appointment on "
                    "file - we can't get eligibility to verify through the payer portal. "
                    "Insurance card shows a United Healthcare plan. Can someone check on "
                    "this while the patient waits?"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 1,
         "content": "Checking now - can you confirm the member ID and date of birth "
                    "from the card? United's portal has been intermittent today so I may "
                    "need to call their eligibility line directly."},
        {"sender": "customer", "type": "customer_email", "offset_hours": 2,
         "content": "Sent the member ID and DOB over separately - patient's still here "
                    "so whatever you can confirm quickly would help."},
    ],
    "E6": [
        {"sender": "customer", "type": "customer_email", "offset_hours": 0,
         "content": "Patient A. Fairweather came in today with a new insurance card - "
                    "looks like they switched from Cigna to a Humana Medicare Advantage "
                    "plan. Attaching a photo of the new card, can you re-verify before "
                    "their visit next week?"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 8,
         "content": "Got the card image, thanks. I'll run eligibility on the new Humana "
                    "plan and confirm coverage details before the appointment."},
        {"sender": "customer", "type": "customer_email", "offset_hours": 40,
         "content": "Great - also want to flag they mentioned a referral might be "
                    "needed for ophthalmology under this plan, not sure if that's "
                    "accurate."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 60,
         "content": "Confirmed active coverage effective this month, and yes, this "
                    "Humana plan does require a referral from the PCP for specialist "
                    "visits. I'd recommend getting that on file before the appointment "
                    "to avoid a denial."},
    ],
    "E7": [
        {"sender": "customer", "type": "customer_email", "offset_hours": 0,
         "content": "We had some confusion on patient V. Okonkwo's coverage - "
                    "eligibility check showed inactive but the patient insists their "
                    "plan is active. Can you take another look?"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 4,
         "content": "Looking into it now - sometimes this happens when a plan renews "
                    "and the payer's system hasn't updated the effective date yet. "
                    "Checking directly with the payer."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 10,
         "content": "Confirmed with the payer - the patient's plan did renew and is "
                    "active, there was just a lag in their system reflecting the new "
                    "effective date. Eligibility is now showing correctly on our end "
                    "too."},
        {"sender": "customer", "type": "customer_email", "offset_hours": 14,
         "content": "That's a relief - thank you so much for chasing this down so "
                    "quickly, we were worried we'd have to reschedule the patient."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 16,
         "content": "Happy to help! Closing this out now that everything's confirmed "
                    "active - let us know if anything else comes up before the visit."},
    ],
    "G5": [
        {"sender": "customer", "type": "customer_email", "offset_hours": 0,
         "content": "Hi team,\n\nWanted to flag something before this claim goes out - "
                    "while running our pre-billing report this morning I noticed patient "
                    "O. Reyes's claim for the visit on 7/2 has CPT 96372 (therapeutic "
                    "injection) entered w/ 3 units, but the chart only documents one "
                    "injection administered that day. Can you correct the unit count to 1 "
                    "before it releases?\n\nAlso, this code comes up a lot for us with "
                    "injection visits so if there's an easy way to check nothing else got "
                    "entered the same way recently that'd be great - but main thing right "
                    "now is just getting this one corrected in time, we're kind of up "
                    "against the clock on it.\n\nThanks!\nMonica"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 6,
         "content": "Thanks for catching this before it went out - pulling the encounter "
                    "now, should have it corrected shortly."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 30,
         "content": "Unit count's corrected to 1 on O. Reyes's claim, on hold til "
                    "confirmed. Also poked around on where the 3-unit default is coming "
                    "from - looks like it might be tied to the charge entry template for "
                    "this code rather than something entered manually, but I want to loop "
                    "in our coding team to confirm before I call it fully resolved. Give "
                    "me a bit on that."},
        {"sender": "customer", "type": "customer_email", "offset_hours": 50,
         "content": "ok that's good to know - is this just us or could this be a payer "
                    "thing too? want to make sure we don't need to flag this elsewhere "
                    "too"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 130,
         "content": "Coding confirmed it's our template default, not payer side - been "
                    "set to 3 units from an older protocol that hasn't applied in a "
                    "while. Fixed the default to 1 and pulled the last two weeks of "
                    "claims on this code - found one more, R. Delacroix, DOS 6/28, same "
                    "issue, already corrected. Nothing else in that window as far as I "
                    "can tell."},
        {"sender": "customer", "type": "customer_email", "offset_hours": 150,
         "content": "appreciate you actually digging into why instead of just patching "
                    "the one claim, thanks"},
        {"sender": "customer", "type": "customer_email", "offset_hours": 300,
         "content": "hey - not sure if this is related but we just caught the same 3 "
                    "unit thing again, third patient now, K Whitfield DOS 7/9. thought "
                    "this was supposed to be fixed after the template thing? kind of "
                    "confused why it's still happening"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 306,
         "content": "Sorry to hear that - can you send me the claim # for K. Whitfield's "
                    "visit so I can dig into why it slipped through?"},
        {"sender": "customer", "type": "customer_email", "offset_hours": 330,
         "content": "claim #77410, DOS 7/9 - attached the remittance, you can see the "
                    "units on there"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 350,
         "content": "Looking into claim #77401 now."},
        {"sender": "customer", "type": "customer_email", "offset_hours": 352,
         "content": "that's 77410 not 77401, just making sure"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 372,
         "content": "You're right, sorry - #77410. Found it: this encounter got created "
                    "the day before the template fix went in, so it inherited the old "
                    "default even though it wasn't billed til after. This one already "
                    "went to the payer too and their remittance is flagging an "
                    "overpayment for the extra 2 units - they want a refund before "
                    "they'll reprocess. I've submitted the refund request but their "
                    "turnaround on those is usually 2-3 weeks, so this piece might take a "
                    "little while even though the coding side is already fixed."},
        {"sender": "customer", "type": "customer_email", "offset_hours": 472,
         "content": "Hi -\n\nStepping in on this one. Monica mentioned this is the third "
                    "time in about two weeks we've dealt with the same 96372 unit issue, "
                    "and now the last one is stuck waiting on a payer refund for weeks on "
                    "top of it. I get that the template default is fixed, but something "
                    "is clearly still slipping through - this last claim was created "
                    "before the fix went in but got processed after, so we're now "
                    "waiting on your team AND the payer both.\n\nI want a full audit of "
                    "every 96372 claim going back 30 days, not two weeks, and honestly at "
                    "this point I'd rather get a call once that's done than another email "
                    "back and forth. We've also had K. Whitfield's family ask us about "
                    "the remittance, which isn't a conversation we should be having over "
                    "an internal template mistake.\n\nLet me know when the audit's "
                    "done.\n\nDiane"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 482,
         "content": "Diane - completely understand, sorry this has taken three rounds. "
                    "Starting a full 30-day audit on 96372 today, not just two weeks. "
                    "Looped in my supervisor to call you once it's done rather than "
                    "another email. Should have this wrapped in the next few days, "
                    "though the payer refund piece may still lag a bit behind since "
                    "that's on their timeline, not ours."},
        {"sender": "customer", "type": "customer_email", "offset_hours": 522,
         "content": "hi - just checking in, any update on the audit?"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 552,
         "content": "Audit's done - found two more affected claims beyond the three "
                    "already caught, both corrected on our end already. The payer "
                    "refund for K. Whitfield's claim is still processing on their end, "
                    "probably another week or so, but everything else is fully resolved. "
                    "No other instances found in the 30-day window."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 750,
         "content": "Update - payer processed the refund and reprocessed K. Whitfield's "
                    "claim correctly. Everything's cleared now."},
        {"sender": "customer", "type": "customer_email", "offset_hours": 770,
         "content": "thanks for staying on top of this, appreciate it"},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 785,
         "content": "Glad we got it fully sorted. Closing this out - let us know if "
                    "anything else comes up."},
    ],
    "G6": [
        {"sender": "customer", "type": "customer_email", "offset_hours": 0,
         "content": "Just an FYI - we caught a charge entry error on our end for "
                    "patient G. Halloran (wrong CPT code entered for a splint "
                    "application) and already corrected it in our system before it went "
                    "to billing. No action needed from your team, just wanted to keep "
                    "you in the loop."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 5,
         "content": "Thanks for the heads up - good to know it was caught before "
                    "submission. I'll note this in our records in case it comes up "
                    "during reconciliation."},
        {"sender": "customer", "type": "customer_email", "offset_hours": 20,
         "content": "Sounds good, appreciate you noting it. Nothing further needed "
                    "here."},
    ],
    "G7": [
        {"sender": "customer", "type": "customer_email", "offset_hours": 0,
         "content": "Question on charge entry for patient F. Levesque's visit - we're "
                    "not sure whether this should be billed as 92014 (comprehensive "
                    "established patient exam) or 92012 (intermediate exam). The visit "
                    "included a dilated exam but the note is a little thin on the "
                    "extent of exam elements documented."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 10,
         "content": "Good question - the distinction usually comes down to whether the "
                    "documentation supports a comprehensive exam of all elements "
                    "(extended history, full exam of the visual system, initiation of "
                    "diagnostic/treatment program) versus a limited number of elements "
                    "for 92012. Can you send over the note so I can take a look?"},
        {"sender": "customer", "type": "customer_email", "offset_hours": 30,
         "content": "Attached the note - dilated fundus exam was done and documented, "
                    "along with visual acuity and IOP, but I don't see a clear statement "
                    "about initiating or continuing a treatment plan."},
        {"sender": "agent", "type": "agent_reply", "offset_hours": 55,
         "content": "Based on what's documented, this reads closer to 92012 "
                    "(intermediate) - the exam elements are there but without a clearly "
                    "stated treatment plan initiation/continuation, it likely won't "
                    "support the comprehensive-level code on audit. Might be worth a "
                    "quick addendum from the physician if a treatment plan was actually "
                    "discussed."},
        {"sender": "customer", "type": "customer_email", "offset_hours": 90,
         "content": "Makes sense - we'll check with the physician about an addendum. "
                    "In the meantime we'll hold this charge as 92012 pending that "
                    "conversation."},
    ],
}
