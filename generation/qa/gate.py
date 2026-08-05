"""Combines generation.qa.rules (deterministic) + the 2 LLM judges (semantic)
into a single PASS/FLAG/FAIL verdict per generation unit. See
docs/generation_qa_checklist.md "Verdict levels": FAIL -> regenerate from the
same inputs, never hand-patched; FLAG -> kept, routed to the front of the
manual review queue; PASS -> enters the benchmark as-is.
"""

from __future__ import annotations

from dataclasses import dataclass

from generation.qa.rules import (
    FAIL,
    FLAG,
    Finding,
    check_conversation,
    check_customer,
    check_distractor_prefilter,
    check_eval_query,
    check_ground_truth_match,
    check_hard_negative,
    check_style_tags,
    check_ticket_seed,
    check_tier_conformance,
)
from generation.schemas import Judge1Output, Judge2Output, LabelOutput

PASS = "pass"


@dataclass
class Verdict:
    status: str  # PASS | FLAG | FAIL
    findings: list[Finding]


def combine(findings: list[Finding], judge_verdicts: list[str] | None = None) -> Verdict:
    judge_verdicts = judge_verdicts or []
    if any(f.severity == FAIL for f in findings) or FAIL in judge_verdicts:
        status = FAIL
    elif any(f.severity == FLAG for f in findings) or FLAG in judge_verdicts:
        status = FLAG
    else:
        status = PASS
    return Verdict(status=status, findings=findings)


def gate_customer(
    customer_item: dict, batch_inbox_emails: list[str], avoid_names: list[str]
) -> Verdict:
    return combine(check_customer(customer_item, batch_inbox_emails, avoid_names))


def gate_ticket_seed(
    ticket_item: dict,
    assignment: dict,
    sibling_seeds: list[dict] | None = None,
    judge1: Judge1Output | None = None,
) -> Verdict:
    findings = check_ticket_seed(ticket_item, assignment, sibling_seeds)
    judge_verdicts = [judge1.verdict] if judge1 is not None else []
    return combine(findings, judge_verdicts)


def gate_conversation(
    ticket_seed: dict, conversation: dict, judge1: Judge1Output | None = None
) -> Verdict:
    findings = check_conversation(ticket_seed, conversation)
    judge_verdicts = [judge1.verdict] if judge1 is not None else []
    return combine(findings, judge_verdicts)


def gate_eval_query(email_text: str, tone: str, length_bucket: str, noise_level: str) -> Verdict:
    findings = check_eval_query(email_text)
    findings += check_style_tags(email_text, tone, length_bucket, noise_level)
    return combine(findings)


def gate_label(
    intended_target_temp_id: str | None,
    intended_tier: str,
    judged: LabelOutput,
) -> Verdict:
    findings = check_ground_truth_match(intended_target_temp_id, judged.matched_label)
    findings += check_tier_conformance(intended_tier, judged.difficulty_tier.value)
    if intended_tier == "hard_negative":
        findings += check_hard_negative(judged.should_match)
    return combine(findings)


def gate_distractor(
    correct_ticket_temp_id: str,
    distractor_ticket_temp_id: str,
    same_customer: bool,
    judge2: Judge2Output | None = None,
) -> Verdict:
    findings = check_distractor_prefilter(
        correct_ticket_temp_id, distractor_ticket_temp_id, same_customer
    )
    if not findings and judge2 is not None and not judge2.is_realistic_distractor:
        findings.append(Finding(FLAG, "distractor_realism", "Judge 2: not actually confusable"))
    return combine(findings)
