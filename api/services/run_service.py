from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from api.schemas.common import CustomerRef, TicketRef
from api.schemas.run import (
    AnnSearchTrace,
    ContextBuildingTrace,
    DecisionTrace,
    EmbeddingTrace,
    FusedHitOut,
    FusionTrace,
    GroupingTrace,
    KeywordSearchTrace,
    MatchedInteractionOut,
    PreprocessingTrace,
    RerankedOut,
    RerankingTrace,
    RunCompareResponse,
    RunRequest,
    RunTraceResponse,
    ScoredInteractionRef,
    ThreadDetectionTrace,
    TicketCandidateOut,
    TicketContextOut,
)
from recommender.config import settings
from recommender.decision import SYSTEM_PROMPT
from recommender.models import Interaction, Ticket
from recommender.pipeline import IncomingEmail
from recommender.pipeline_trace import PipelineTrace, run_traced_pipeline
from recommender.pipeline_trace_no_reranker import run_traced_pipeline_no_reranker

PREVIEW_CHARS = 200


class _Lookup:
    """Per-request cache so rendering a trace never re-queries the same
    ticket/interaction twice (a candidate's ticket, its matched interactions,
    and its context all reference the same handful of rows)."""

    def __init__(self, session: Session):
        self.session = session
        self._tickets: dict[uuid.UUID, Ticket] = {}
        self._interactions: dict[uuid.UUID, Interaction] = {}

    def ticket(self, ticket_id: uuid.UUID) -> Ticket | None:
        if ticket_id not in self._tickets:
            self._tickets[ticket_id] = self.session.get(Ticket, ticket_id)
        return self._tickets[ticket_id]

    def ticket_ref(self, ticket_id: uuid.UUID | None) -> TicketRef | None:
        if ticket_id is None:
            return None
        t = self.ticket(ticket_id)
        if t is None:
            return None
        return TicketRef(
            id=t.id, subject=t.subject, category=t.category, status=t.status.value,
            customer_name=t.customer.name,
        )

    def interaction(self, interaction_id: uuid.UUID) -> Interaction | None:
        if interaction_id not in self._interactions:
            self._interactions[interaction_id] = self.session.get(Interaction, interaction_id)
        return self._interactions[interaction_id]

    def preview(self, interaction_id: uuid.UUID) -> str:
        i = self.interaction(interaction_id)
        return i.clean_content[:PREVIEW_CHARS] if i is not None else ""

    def interaction_ticket_ref(self, interaction_id: uuid.UUID) -> TicketRef | None:
        i = self.interaction(interaction_id)
        if i is None or i.ticket_id is None:
            return None
        return self.ticket_ref(i.ticket_id)


def _scored_refs(lookup: _Lookup, hits) -> list[ScoredInteractionRef]:
    return [
        ScoredInteractionRef(
            interaction_id=h.interaction_id,
            ticket=lookup.interaction_ticket_ref(h.interaction_id),
            score=h.score,
            preview=lookup.preview(h.interaction_id),
        )
        for h in hits
    ]


def _trace_to_response(
    session: Session, trace: PipelineTrace, original_subject: str, original_body: str
) -> RunTraceResponse:
    lookup = _Lookup(session)

    customer = (
        CustomerRef(id=trace.customer.id, name=trace.customer.name, inbox_email=trace.customer.inbox_email)
        if trace.customer is not None
        else None
    )

    preprocessing = None
    if trace.preprocessed is not None:
        preprocessing = PreprocessingTrace(
            original_subject=original_subject,
            original_body=original_body,
            clean_body=trace.preprocessed.clean_body,
            embedding_text=trace.preprocessed.embedding_text,
            time_ms=trace.timings_ms.get("preprocessing", 0.0),
        )

    thread_detection = None
    if "thread_detection" in trace.timings_ms or trace.thread_match is not None:
        thread_detection = ThreadDetectionTrace(
            enabled=True,
            matched=trace.thread_match is not None,
            matched_on=trace.thread_match.matched_on if trace.thread_match else None,
            ticket=lookup.ticket_ref(trace.thread_match.ticket.id) if trace.thread_match else None,
            matched_interaction_id=trace.thread_match.matched_interaction.id if trace.thread_match else None,
            time_ms=trace.timings_ms.get("thread_detection", 0.0),
        )

    embedding = None
    if trace.query_embedding_stats is not None:
        s = trace.query_embedding_stats
        embedding = EmbeddingTrace(
            model=s.model, dimension=s.dimension, time_ms=trace.timings_ms.get("embedding", 0.0),
            norm=s.norm, min=s.min, max=s.max, preview_first_20=s.preview_first_20,
        )

    keyword_search = None
    if trace.keyword_hits is not None:
        keyword_search = KeywordSearchTrace(
            top_n=len(trace.keyword_hits), time_ms=trace.timings_ms.get("keyword_search", 0.0),
            hits=_scored_refs(lookup, trace.keyword_hits),
        )

    ann_search = None
    if trace.ann_hits is not None:
        ann_search = AnnSearchTrace(
            top_n=len(trace.ann_hits), time_ms=trace.timings_ms.get("ann_search", 0.0),
            hits=_scored_refs(lookup, trace.ann_hits),
        )

    fusion = None
    if trace.fused_hits is not None:
        fusion = FusionTrace(
            rrf_k=settings.retrieval.rrf_k, fusion_top_n=len(trace.fused_hits),
            time_ms=trace.timings_ms.get("hybrid_retrieval", 0.0),
            hits=[
                FusedHitOut(
                    interaction_id=h.interaction_id,
                    ticket=lookup.interaction_ticket_ref(h.interaction_id),
                    preview=lookup.preview(h.interaction_id),
                    fused_score=h.fused_score,
                    keyword_score=h.keyword_score,
                    ann_score=h.ann_score,
                )
                for h in trace.fused_hits
            ],
        )

    grouping = None
    if trace.candidates is not None:
        grouping = GroupingTrace(
            time_ms=trace.timings_ms.get("grouping", 0.0),
            candidates=[
                TicketCandidateOut(
                    ticket=lookup.ticket_ref(c.ticket_id),
                    max_score=c.max_score, topk_avg=c.topk_avg,
                    recency_score=c.recency_score, final_score=c.final_score,
                    matched_interactions=[
                        MatchedInteractionOut(
                            interaction_id=m.interaction_id, match_score=m.match_score,
                            preview=lookup.preview(m.interaction_id),
                        )
                        for m in c.matched_interactions
                    ],
                )
                for c in trace.candidates
            ],
        )

    context_building = None
    if trace.contexts is not None:
        context_building = ContextBuildingTrace(
            time_ms=trace.timings_ms.get("context_building", 0.0),
            contexts=[
                TicketContextOut(
                    ticket=lookup.ticket_ref(ctx.ticket_id), text=ctx.text, char_count=len(ctx.text)
                )
                for ctx in trace.contexts
            ],
        )

    reranking = None
    if trace.reranked is not None:
        reranking = RerankingTrace(
            model_name=settings.reranker.model_name, time_ms=trace.timings_ms.get("reranking", 0.0),
            scores=[
                RerankedOut(ticket=lookup.ticket_ref(r.ticket_id), rerank_score=r.rerank_score)
                for r in trace.reranked
            ],
        )

    decision = None
    if trace.decision is not None:
        decision = DecisionTrace(
            model=settings.decision.model, time_ms=trace.timings_ms.get("llm_decision", 0.0),
            system_prompt=SYSTEM_PROMPT, user_prompt=trace.decision.prompt,
            should_attach=trace.decision.should_attach,
            ticket=lookup.ticket_ref(trace.decision.ticket_id),
            confidence=trace.decision.confidence, explanation=trace.decision.explanation,
        )

    return RunTraceResponse(
        path=trace.path,
        total_time_ms=trace.total_time_ms,
        recommended_ticket_id=trace.recommended_ticket_id,
        customer=customer,
        preprocessing=preprocessing,
        thread_detection=thread_detection,
        embedding=embedding,
        keyword_search=keyword_search,
        ann_search=ann_search,
        fusion=fusion,
        grouping=grouping,
        context_building=context_building,
        reranking=reranking,
        decision=decision,
        stage_timings_ms=trace.timings_ms,
    )


def _email_from_request(request: RunRequest) -> IncomingEmail:
    message_id = request.message_id or f"<debug-{uuid.uuid4()}@dashboard.local>"
    return IncomingEmail(
        subject=request.subject,
        body=request.body,
        sender_email=request.sender_email,
        message_id=message_id,
        conversation_id=request.conversation_id,
        in_reply_to=request.in_reply_to,
        reference_message_ids=request.reference_message_ids,
    )


def run_pipeline_traced(session: Session, request: RunRequest) -> RunTraceResponse:
    email = _email_from_request(request)
    trace = run_traced_pipeline(session, email, now=request.now)
    return _trace_to_response(session, trace, request.subject, request.body)


def run_pipeline_no_reranker_traced(session: Session, request: RunRequest) -> RunTraceResponse:
    """Experimental variant of run_pipeline_traced -- same request/response
    shape, but backed by run_traced_pipeline_no_reranker (see that module's
    docstring). run_pipeline_traced and run_traced_pipeline above are
    untouched."""
    email = _email_from_request(request)
    trace = run_traced_pipeline_no_reranker(session, email, now=request.now)
    response = _trace_to_response(session, trace, request.subject, request.body)
    return response.model_copy(update={"pipeline_variant": "no_reranker"})


def run_pipeline_compare(session: Session, request: RunRequest) -> RunCompareResponse:
    """Runs both pipelines against the identical email/now so the dashboard
    can render them side by side in one round trip."""
    return RunCompareResponse(
        with_reranker=run_pipeline_traced(session, request),
        no_reranker=run_pipeline_no_reranker_traced(session, request),
    )
