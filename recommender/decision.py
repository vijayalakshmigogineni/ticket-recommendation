"""Milestone 7 -- LLM Decision Layer (step 9). Takes the incoming email plus
the Top K reranked candidate tickets (context + scores) and asks the LLM for
a final should-attach / which-ticket / confidence / explanation decision.

The LLM never creates tickets and its recommendation is never auto-applied --
it is a recommendation an Account Manager reviews (step 10 of the online
pipeline), consistent with "AI never creates tickets" in the architecture.

Candidates are referred to by a small 1-based index in the prompt (not their
raw UUID) to keep the model from hallucinating a plausible-looking-but-wrong
ID; the index is mapped back to the real ticket_id in code after the call.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from pydantic import BaseModel, Field

from recommender.context_builder import TicketContext
from recommender.ollama_client import chat_structured

SYSTEM_PROMPT = (
    "You are an assistant helping a Revenue Cycle Management (RCM) Account Manager "
    "decide whether an incoming client email belongs to one of their existing support "
    "tickets. You are given the incoming email and a short list of candidate tickets, "
    "each with recent conversation context. Decide whether the email should be attached "
    "to one of the candidates, and if so, which one. If none of the candidates are "
    "genuinely about the same underlying issue, say it should not be attached to any of "
    "them -- do not force a match. You never create tickets; you only recommend."
)


class LLMDecisionSchema(BaseModel):
    should_attach: bool
    candidate_index: int | None = Field(
        default=None,
        description="1-based index into the provided candidate list, or null if should_attach is false.",
    )
    confidence: float = Field(ge=0.0, le=1.0)
    explanation: str


@dataclass
class DecisionResult:
    should_attach: bool
    ticket_id: uuid.UUID | None
    confidence: float
    explanation: str
    # Exposes the user prompt already built internally, for the debug
    # dashboard's LLM Decision stage view -- None only on the early
    # empty-candidates return, where no prompt is ever built.
    prompt: str | None = None


def _format_candidate(index: int, context: TicketContext, score: float, score_label: str) -> str:
    return f"=== Candidate {index} ({score_label}: {score:.3f}) ===\n{context.text}"


def decide(
    incoming_email_text: str,
    candidates: list[tuple[TicketContext, float]],  # (context, score), in the order to present them
    model: str,
    host: str,
    temperature: float = 0.0,
    timeout: float = 180.0,
    # Default keeps every existing caller's prompt text byte-for-byte
    # unchanged; only the no-reranker experimental pipeline passes a
    # different label, since its second tuple element isn't a rerank score.
    score_label: str = "cross-encoder score",
) -> DecisionResult:
    if not candidates:
        return DecisionResult(
            should_attach=False, ticket_id=None, confidence=1.0,
            explanation="No candidate tickets were retrieved for this customer.",
        )

    candidate_blocks = "\n\n".join(
        _format_candidate(i, ctx, score, score_label) for i, (ctx, score) in enumerate(candidates, start=1)
    )
    user_message = (
        f"Incoming email:\n{incoming_email_text}\n\n"
        f"Candidate tickets:\n{candidate_blocks}\n\n"
        f"Respond with should_attach, candidate_index (1-{len(candidates)} or null), "
        f"confidence (0-1), and a brief explanation."
    )

    result = chat_structured(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        output_format=LLMDecisionSchema,
        model=model,
        host=host,
        temperature=temperature,
        timeout=timeout,
    )

    ticket_id: uuid.UUID | None = None
    should_attach = result.should_attach
    if should_attach:
        # candidate_index is optional in the schema (has a default), and the
        # model frequently omits it even when should_attach=true -- when
        # that happens, fall back to candidate 1 (the reranker's top pick,
        # and consistently what the model's own explanation was actually
        # discussing in every observed omission case) rather than silently
        # discarding a positive decision.
        idx = (result.candidate_index - 1) if result.candidate_index is not None else 0
        if 0 <= idx < len(candidates):
            ticket_id = candidates[idx][0].ticket_id
        else:
            should_attach = False

    return DecisionResult(
        should_attach=should_attach and ticket_id is not None,
        ticket_id=ticket_id,
        confidence=result.confidence,
        explanation=result.explanation,
        prompt=user_message,
    )
