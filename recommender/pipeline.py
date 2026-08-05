"""Milestone 8 -- End-to-end online pipeline orchestration, wiring every
milestone together in the exact order the locked architecture specifies:

Incoming Email -> Email Preprocessing -> Customer Identification ->
Thread Detection (auto-attach shortcut, no AI) -> Generate Email Embedding ->
Hybrid Retrieval -> Group by Ticket / Aggregate -> Top M Candidates ->
Context Builder -> Cross-Encoder Reranker -> Top K -> LLM Decision Layer ->
Account Manager Recommendation.

Returns every intermediate stage's output (not just the final answer) so
Milestone 8's tests can assert on each stage independently, not just the end
result.
"""

from __future__ import annotations

import datetime
import uuid
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from recommender.config import RecommenderConfig, settings
from recommender.context_builder import TicketContext, build_ticket_context
from recommender.customer_identification import identify_customer
from recommender.decision import DecisionResult, decide
from recommender.grouping import TicketCandidate, group_and_aggregate
from recommender.models import Customer
from recommender.ollama_client import embed_text
from recommender.preprocessing import preprocess_incoming_email
from recommender.reranker import RerankedCandidate, rerank
from recommender.retrieval.hybrid import FusedHit, hybrid_retrieve
from recommender.thread_detection import ThreadMatch, detect_thread


@dataclass
class IncomingEmail:
    subject: str
    body: str
    sender_email: str
    message_id: str
    conversation_id: str | None = None
    in_reply_to: str | None = None
    reference_message_ids: list[str] = field(default_factory=list)


@dataclass
class PipelineResult:
    path: str  # "unknown_customer" | "auto_attach" | "ai_decision"
    customer: Customer | None = None
    thread_match: ThreadMatch | None = None
    fused_hits: list[FusedHit] = field(default_factory=list)
    candidates: list[TicketCandidate] = field(default_factory=list)
    contexts: list[TicketContext] = field(default_factory=list)
    reranked: list[RerankedCandidate] = field(default_factory=list)
    decision: DecisionResult | None = None

    @property
    def recommended_ticket_id(self) -> uuid.UUID | None:
        if self.path == "auto_attach" and self.thread_match is not None:
            return self.thread_match.ticket.id
        if self.path == "ai_decision" and self.decision is not None and self.decision.should_attach:
            return self.decision.ticket_id
        return None


def run_pipeline(
    session: Session,
    email: IncomingEmail,
    config: RecommenderConfig = settings,
    now: datetime.datetime | None = None,
) -> PipelineResult:
    now = now or datetime.datetime.now(datetime.timezone.utc)

    preprocessed = preprocess_incoming_email(email.subject, email.body, email.sender_email)

    customer = identify_customer(session, preprocessed.sender_email)
    if customer is None:
        return PipelineResult(path="unknown_customer")

    if config.thread_detection.enabled:
        thread_match = detect_thread(
            session,
            conversation_id=email.conversation_id,
            in_reply_to=email.in_reply_to,
            reference_message_ids=email.reference_message_ids,
        )
        if thread_match is not None:
            return PipelineResult(path="auto_attach", customer=customer, thread_match=thread_match)

    query_embedding = embed_text(
        preprocessed.embedding_text,
        model=config.ollama.embedding_model,
        host=config.ollama.host,
    )

    fused_hits = hybrid_retrieve(
        session,
        query_text=preprocessed.embedding_text,
        query_embedding=query_embedding,
        customer_id=customer.id,
        keyword_top_n=config.retrieval.keyword_top_n,
        ann_top_n=config.retrieval.ann_top_n,
        rrf_k=config.retrieval.rrf_k,
        fusion_top_n=config.retrieval.fusion_top_n,
    )

    candidates = group_and_aggregate(
        session,
        fused_hits,
        top_m=config.aggregation.top_m_candidates,
        top_k_for_avg=config.aggregation.top_k_for_avg,
        weight_max=config.aggregation.weight_max,
        weight_topk_avg=config.aggregation.weight_topk_avg,
        weight_recency=config.aggregation.weight_recency,
        recency_half_life_days=config.aggregation.recency_half_life_days,
        now=now,
    )

    contexts = [
        build_ticket_context(
            session,
            candidate.ticket_id,
            candidate.matched_interaction_ids,
            max_matched_interactions=config.context_builder.max_matched_interactions_per_ticket,
            neighbors_before=config.context_builder.neighbors_before,
            neighbors_after=config.context_builder.neighbors_after,
        )
        for candidate in candidates
    ]

    reranked = rerank(
        preprocessed.embedding_text,
        contexts,
        model_name=config.reranker.model_name,
        device=config.reranker.device,
        top_k=config.reranker.top_k,
    )

    contexts_by_ticket = {c.ticket_id: c for c in contexts}
    decision_input = [
        (contexts_by_ticket[r.ticket_id], r.rerank_score)
        for r in reranked
        if r.ticket_id in contexts_by_ticket
    ]

    decision = decide(
        preprocessed.embedding_text,
        decision_input,
        model=config.decision.model,
        host=config.ollama.host,
        temperature=config.decision.temperature,
        timeout=config.decision.timeout_s,
    )

    return PipelineResult(
        path="ai_decision",
        customer=customer,
        fused_hits=fused_hits,
        candidates=candidates,
        contexts=contexts,
        reranked=reranked,
        decision=decision,
    )
