"""Hand-authored incoming-email test fixtures for Milestone 8 (end-to-end
pipeline verification). Each covers one distinct path through the online
pipeline; `expected` is for our own manual/test-assertion use, never
consumed by the pipeline itself.
"""

from __future__ import annotations

TEST_EMAILS = [
    {
        "key": "auto_attach_thread_reply",
        "description": "Literal reply-in-thread to C4 (valley_womens_health, claim denied "
        "timely filing, OPEN) -- should auto-attach via thread detection, no AI involved.",
        "sender_email": "frontdesk@valleywomenshealth.com",
        "subject": "RE: Claim denied - timely filing limit exceeded",
        "body": "Just following up on this - any update on claim #81044? We really need "
        "this resolved before month end.",
        "message_id": "<c4-followup01@valleywomenshealth.com>",
        "conversation_id": "<conv-c4@rcmsupport.internal>",
        "in_reply_to": "<c4-msg01@valleywomenshealth.com>",
        "reference_message_ids": ["<c4-msg01@valleywomenshealth.com>"],
        "expected": {"path": "auto_attach", "ticket_key": "C4"},
    },
    {
        "key": "semantic_match_broken_thread",
        "description": "New message-id/no threading, same underlying issue as A1 "
        "(sunridge_ortho, prior auth denied knee MRI, WAITING_FOR_CLIENT) phrased "
        "differently -- should be caught by embedding retrieval + rerank + LLM decision.",
        "sender_email": "billing@sunridgeortho.com",
        "subject": "Conservative treatment records for Kevin Bell",
        "body": "Hi, following up on the MRI authorization issue for our patient - Dr. Osei's "
        "office just sent over the physical therapy and NSAID trial notes you asked for "
        "so we can get the imaging approved. Attaching those now, let us know if you need "
        "anything else for the appeal.",
        "message_id": "<sunridge-newmsg-001@sunridgeortho.com>",
        "conversation_id": None,
        "in_reply_to": None,
        "reference_message_ids": [],
        "expected": {"path": "ai_decision", "should_attach": True, "ticket_key": "A1"},
    },
    {
        "key": "hard_negative_new_issue",
        "description": "riverside_family_medicine has 4 unrelated existing tickets "
        "(C1 resolved, P4 open, R3 resolved, G2 waiting) -- this is a genuinely new, "
        "unrelated policy question. Should NOT attach to any of them.",
        "sender_email": "billing@riversidefamilymed.com",
        "subject": "Question about PT pre-authorization policy",
        "body": "We have a new patient starting physical therapy next week. Do we generally "
        "need pre-authorization for PT visits under most of our commercial payers, or does "
        "it vary by plan? Just want to get ahead of this before scheduling more visits.",
        "message_id": "<riverside-newmsg-001@riversidefamilymed.com>",
        "conversation_id": None,
        "in_reply_to": None,
        "reference_message_ids": [],
        "expected": {"path": "ai_decision", "should_attach": False},
    },
    {
        "key": "same_customer_disambiguation",
        "description": "metro_cardiology has 4 open-ish tickets across different categories "
        "(C3 claims/modifier 25, A2 prior auth expired, E1 eligibility failed, G4 duplicate "
        "charge). This email is about a DIFFERENT patient's claim denied for the same "
        "missing-modifier-25 reason -- should match C3 specifically, not the other three.",
        "sender_email": "ar@metrocardiologypartners.com",
        "subject": "Another modifier 25 denial",
        "body": "Just got another one back - claim for a different patient's echo visit was "
        "denied again, same reason as before, missing modifier 25 on the E/M code billed "
        "same-day as the procedure. Can you add it to the same batch you're already fixing?",
        "message_id": "<metro-newmsg-001@metrocardiologypartners.com>",
        "conversation_id": None,
        "in_reply_to": None,
        "reference_message_ids": [],
        "expected": {"path": "ai_decision", "should_attach": True, "ticket_key": "C3"},
    },
]
