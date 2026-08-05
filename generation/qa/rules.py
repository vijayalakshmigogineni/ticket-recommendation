"""Deterministic QA checks. See docs/generation_qa_checklist.md sections 1-6.

Pure functions -- no API calls. Each returns a list[Finding]; an empty list
means "this rule found nothing to flag." qa/gate.py combines these with the
two LLM judges into a PASS/FLAG/FAIL verdict per generation unit.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.enums import (
    DifficultyTier,
    LengthBucket,
    MessageIntent,
    NoiseLevel,
    SenderType,
    Tone,
    TERMINAL_TICKET_STATUSES,
    TicketCategory,
    TicketStatus,
)

FAIL = "fail"
FLAG = "flag"

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_TEMP_ID_RE = re.compile(r"\b(cust|tkt|q)_\d+(_\d+)?\b")
# Synthetic identifiers (CLM-1234, PT-88213, ...) are expected to appear
# verbatim in easy-tier text -- strip them before the noise-marker scan below,
# or a claim number like "CLM-100" gets miscounted as the "clm" abbreviation
# marker (short for "claim") purely because it contains that substring.
_IDENTIFIER_RE = re.compile(r"\b[A-Za-z]{2,6}-[A-Za-z0-9-]+\b")
_META_PHRASES = (
    "difficulty tier", "ground truth", "distractor", "should_match", "temp_id",
)
_REFUSAL_PATTERNS = (
    "as an ai", "i cannot", "i can't help with", "this is a synthetic example",
    "this is a synthetic", "as a language model",
)
_NOISE_ABBREVIATIONS = (
    " pt ", " asap", " w/", " u ", " ur ", " pls ", " b4", " thx", " asap",
    " acct", " clm", " auth", " amt", " wk ", " goin", " callin", " sayin",
    " startin", " takin", " askin", " everyones", "'ll not", " idk ",
)


@dataclass
class Finding:
    severity: str  # FAIL | FLAG
    check: str
    message: str


# --- 1. Customer QA -----------------------------------------------------------


def check_customer(
    customer_item: dict,
    batch_inbox_emails: list[str],
    avoid_names: list[str],
) -> list[Finding]:
    findings: list[Finding] = []
    prod = customer_item.get("production_fields", {})
    meta = customer_item.get("generation_metadata", {})

    name = prod.get("name")
    inbox_email = prod.get("inbox_email")
    contacts = meta.get("contacts") or []

    if not name or not inbox_email:
        findings.append(Finding(FAIL, "required_fields", "name/inbox_email missing or empty"))
    if not contacts or not any(c.get("email") for c in contacts):
        findings.append(Finding(FAIL, "required_fields", "no contacts with a non-empty email"))

    if inbox_email and not _EMAIL_RE.match(inbox_email):
        findings.append(Finding(FAIL, "email_format", f"invalid inbox_email: {inbox_email!r}"))
    for c in contacts:
        email = c.get("email")
        if email and not _EMAIL_RE.match(email):
            findings.append(Finding(FAIL, "email_format", f"invalid contact email: {email!r}"))

    if inbox_email and batch_inbox_emails.count(inbox_email) > 1:
        findings.append(Finding(FAIL, "duplicate_inbox_email", f"{inbox_email!r} duplicated in batch"))

    if inbox_email and any(c.get("email") == inbox_email for c in contacts):
        findings.append(Finding(FLAG, "inbox_email_matches_contact", "inbox_email equals a contact's own email"))

    if name and name in avoid_names:
        findings.append(Finding(FLAG, "duplicate_name", f"{name!r} already used"))

    return findings


# --- 2. Ticket Seed QA ---------------------------------------------------------


def check_ticket_seed(
    ticket_item: dict,
    assignment: dict,
    sibling_seeds: list[dict] | None = None,
) -> list[Finding]:
    findings: list[Finding] = []
    prod = ticket_item.get("production_fields", {})
    meta = ticket_item.get("generation_metadata", {})

    category = prod.get("category")
    status = prod.get("status")

    if category not in {c.value for c in TicketCategory}:
        findings.append(Finding(FAIL, "category_valid", f"invalid category: {category!r}"))
    if status not in {s.value for s in TicketStatus}:
        findings.append(Finding(FAIL, "status_valid", f"invalid status: {status!r}"))

    if category != assignment.get("category"):
        findings.append(Finding(FAIL, "category_matches_assignment", "category does not match orchestrator assignment"))
    if status != assignment.get("status"):
        findings.append(Finding(FAIL, "status_matches_assignment", "status does not match orchestrator assignment"))

    is_terminal = status in {s.value for s in TERMINAL_TICKET_STATUSES}
    created_offset = prod.get("created_at_offset_days")
    closed_offset = prod.get("closed_at_offset_days")
    if is_terminal:
        if closed_offset is None:
            findings.append(Finding(FAIL, "closed_date_logic", "terminal status but closed_at_offset_days is null"))
        elif created_offset is not None and closed_offset < created_offset:
            findings.append(Finding(FAIL, "closed_date_logic", "closed_at_offset_days is before created_at_offset_days"))
    elif closed_offset is not None:
        findings.append(Finding(FAIL, "closed_date_logic", "non-terminal status but closed_at_offset_days is set"))

    if sibling_seeds:
        distinguishing = meta.get("distinguishing_details")
        if not distinguishing:
            findings.append(Finding(FAIL, "sibling_distinctness", "distinguishing_details empty for a sibling-pair ticket"))
        for sibling in sibling_seeds:
            sibling_meta = sibling.get("generation_metadata", {})
            if meta.get("claim_number") and meta.get("claim_number") == sibling_meta.get("claim_number"):
                findings.append(Finding(FAIL, "sibling_distinctness", "claim_number identical to sibling"))
            if meta.get("patient_id") and meta.get("patient_id") == sibling_meta.get("patient_id"):
                findings.append(Finding(FAIL, "sibling_distinctness", "patient_id identical to sibling"))

    return findings


# --- 3. Conversation QA --------------------------------------------------------


def check_conversation(ticket_seed: dict, conversation: dict) -> list[Finding]:
    findings: list[Finding] = []
    messages = conversation.get("messages", [])
    if not messages:
        return [Finding(FAIL, "non_empty", "conversation has zero messages")]

    first = messages[0]
    if first.get("production_fields", {}).get("sender_type") != SenderType.CLIENT.value:
        findings.append(Finding(FAIL, "message_1_structure", "first message sender_type is not client"))
    if first.get("generation_metadata", {}).get("intent_type") != MessageIntent.INITIAL_REQUEST.value:
        findings.append(Finding(FAIL, "message_1_structure", "first message intent_type is not initial_request"))

    valid_intents = {i.value for i in MessageIntent}
    valid_tones = {t.value for t in Tone}
    valid_lengths = {l.value for l in LengthBucket}
    valid_noise = {n.value for n in NoiseLevel}

    prev_offset = None
    same_sender_streak = 1
    prev_sender = None
    for idx, m in enumerate(messages):
        prod = m.get("production_fields", {})
        meta = m.get("generation_metadata", {})

        if meta.get("intent_type") not in valid_intents:
            findings.append(Finding(FAIL, "enum_valid", f"message {idx}: invalid intent_type"))
        if meta.get("tone") not in valid_tones:
            findings.append(Finding(FAIL, "enum_valid", f"message {idx}: invalid tone"))
        if meta.get("length_bucket") not in valid_lengths:
            findings.append(Finding(FAIL, "enum_valid", f"message {idx}: invalid length_bucket"))
        if meta.get("noise_level") not in valid_noise:
            findings.append(Finding(FAIL, "enum_valid", f"message {idx}: invalid noise_level"))

        offset = prod.get("day_offset")
        if prev_offset is not None and offset is not None and offset < prev_offset:
            findings.append(Finding(FAIL, "day_offsets_non_decreasing", f"message {idx}: day_offset decreased"))
        prev_offset = offset

        sender = prod.get("sender_type")
        if sender == prev_sender:
            same_sender_streak += 1
        else:
            same_sender_streak = 1
        if same_sender_streak >= 3 and len(messages) > 3:
            findings.append(Finding(FLAG, "sender_alternation_degeneracy", f"message {idx}: 3+ consecutive same sender_type"))
        prev_sender = sender

    status = ticket_seed.get("production_fields", {}).get("status")
    is_terminal = status in {s.value for s in TERMINAL_TICKET_STATUSES}
    if is_terminal:
        last = messages[-1]
        last_sender = last.get("production_fields", {}).get("sender_type")
        last_intent = last.get("generation_metadata", {}).get("intent_type")
        resolution_shape = (
            last_sender == SenderType.ACCOUNT_MANAGER.value
            or last_intent == MessageIntent.THANK_YOU.value
        )
        if not resolution_shape:
            findings.append(Finding(FLAG, "closed_ticket_resolution_shape", "last message doesn't read as a resolution"))

        closed_offset = ticket_seed.get("production_fields", {}).get("closed_at_offset_days")
        last_offset = last.get("production_fields", {}).get("day_offset")
        if closed_offset is not None and last_offset is not None:
            created_offset = ticket_seed.get("production_fields", {}).get("created_at_offset_days", 0)
            final_absolute_offset = created_offset + last_offset
            if final_absolute_offset > closed_offset:
                findings.append(Finding(FAIL, "closed_ticket_resolution_shape", "final message occurs after closed_at_offset_days"))

    meta_fields = ticket_seed.get("generation_metadata", {})
    all_text = " ".join(
        m.get("production_fields", {}).get("body_text", "") for m in messages
    )
    for field_name in ("claim_number", "patient_id"):
        value = meta_fields.get(field_name)
        if value and value not in all_text:
            findings.append(Finding(FAIL, "grounding_facts_echoed", f"{field_name} {value!r} never appears in the thread"))

    return findings


# --- 4. Eval Query QA -----------------------------------------------------------


def check_broke_character(text: str) -> list[Finding]:
    lowered = text.lower()
    for pattern in _REFUSAL_PATTERNS:
        if pattern in lowered:
            return [Finding(FAIL, "broke_character", f"refusal/meta pattern found: {pattern!r}")]
    return []


def check_eval_query(email_text: str) -> list[Finding]:
    findings: list[Finding] = []
    if not email_text or len(email_text.split()) < 3:
        findings.append(Finding(FAIL, "non_degenerate", "email_text is empty or near-empty"))

    lowered = email_text.lower()
    for category in TicketCategory:
        if category.value.replace("_", " ") in lowered or category.value in lowered:
            findings.append(Finding(FAIL, "label_leakage", f"category literal leaked: {category.value!r}"))
    for tier in DifficultyTier:
        if tier.value in lowered:
            findings.append(Finding(FAIL, "label_leakage", f"difficulty tier literal leaked: {tier.value!r}"))
    for phrase in _META_PHRASES:
        if phrase in lowered:
            findings.append(Finding(FAIL, "label_leakage", f"meta phrase leaked: {phrase!r}"))
    if _TEMP_ID_RE.search(email_text):
        findings.append(Finding(FAIL, "label_leakage", "temp_id-shaped string leaked"))

    findings.extend(check_broke_character(email_text))
    return findings


def check_style_tags(text: str, tone: str, length_bucket: str, noise_level: str) -> list[Finding]:
    """Per docs/generation_qa_checklist.md §6 bins (adjustable after review)."""
    findings: list[Finding] = []
    word_count = len(text.split())

    expected_length = (
        LengthBucket.SHORT.value if word_count <= 40
        else LengthBucket.LONG.value if word_count > 120
        else LengthBucket.MEDIUM.value
    )
    if expected_length != length_bucket:
        findings.append(Finding(FLAG, "length_bucket_conformance", f"word count {word_count} suggests {expected_length!r}, tagged {length_bucket!r}"))

    scan_text = _IDENTIFIER_RE.sub(" ", text)
    lowered = scan_text.lower()
    marker_count = sum(1 for marker in _NOISE_ABBREVIATIONS if marker in f" {lowered} ")
    no_punctuation = not any(p in text for p in ".!?")
    if marker_count >= 5 or (no_punctuation and word_count > 15):
        expected_noise = NoiseLevel.HEAVY.value
    elif marker_count >= 1:
        expected_noise = NoiseLevel.MILD.value
    else:
        expected_noise = NoiseLevel.CLEAN.value
    if expected_noise != noise_level:
        findings.append(Finding(FLAG, "noise_level_conformance", f"heuristic suggests {expected_noise!r}, tagged {noise_level!r}"))

    return findings


# --- 5. Ground-Truth & Distractor QA -------------------------------------------


def check_ground_truth_match(intended_target_temp_id: str | None, judged_target_temp_id: str | None) -> list[Finding]:
    if intended_target_temp_id != judged_target_temp_id:
        return [Finding(
            FAIL, "ground_truth_match",
            f"intended target {intended_target_temp_id!r} != judged target {judged_target_temp_id!r}",
        )]
    return []


def check_tier_conformance(intended_tier: str, judged_tier: str) -> list[Finding]:
    if intended_tier != judged_tier:
        return [Finding(FLAG, "tier_conformance", f"intended tier {intended_tier!r} != judged tier {judged_tier!r}")]
    return []


def check_hard_negative(should_match_judged: bool) -> list[Finding]:
    if should_match_judged:
        return [Finding(FAIL, "hard_negative_should_not_match", "hard_negative scenario judged as a match")]
    return []


def check_distractor_prefilter(
    correct_ticket_temp_id: str,
    distractor_ticket_temp_id: str,
    same_customer: bool,
) -> list[Finding]:
    findings: list[Finding] = []
    if distractor_ticket_temp_id == correct_ticket_temp_id:
        findings.append(Finding(FAIL, "distractor_prefilter", "distractor is the same ticket as the correct answer"))
    if not same_customer:
        findings.append(Finding(FAIL, "distractor_prefilter", "distractor belongs to a different customer"))
    return findings
