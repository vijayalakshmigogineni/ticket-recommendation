"""Debug-dashboard-only traced pipeline runner. NOT a modification of
recommender/pipeline.py's run_pipeline -- a parallel orchestration that calls
the exact same public stage functions run_pipeline calls (importing nothing
new, inventing no new scoring/decision logic), wrapping each with timing and
retaining every intermediate value instead of discarding it.

recommender/pipeline.py, its tests, and every other stage module are
untouched by this file's existence.
"""

from __future__ import annotations

import datetime
import time
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
from recommender.preprocessing import PreprocessedEmail, preprocess_incoming_email
from recommender.reranker import RerankedCandidate, rerank
from recommender.retrieval.ann_search import AnnHit, ann_search
from recommender.retrieval.hybrid import FusedHit, reciprocal_rank_fusion
from recommender.retrieval.keyword_search import KeywordHit, keyword_search
from recommender.thread_detection import ThreadMatch, detect_thread


class _Stopwatch:
    def __enter__(self) -> "_Stopwatch":
        self._start = time.perf_counter()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.elapsed_ms = (time.perf_counter() - self._start) * 1000.0


@dataclass
class EmbeddingStats:
    model: str
    dimension: int
    norm: float
    min: float
    max: float
    preview_first_20: list[float]


@dataclass
class MatchedInteraction:
    interaction_id: uuid.UUID
    match_score: float


@dataclass
class TicketCandidateTrace:
    ticket_id: uuid.UUID
    max_score: float
    topk_avg: float
    recency_score: float
    final_score: float
    matched_interactions: list[MatchedInteraction]


@dataclass
class PipelineTrace:
    path: str  # "unknown_customer" | "auto_attach" | "ai_decision"
    customer: Customer | None = None
    preprocessed: PreprocessedEmail | None = None
    thread_match: ThreadMatch | None = None
    query_embedding_stats: EmbeddingStats | None = None
    keyword_hits: list[KeywordHit] | None = None
    ann_hits: list[AnnHit] | None = None
    fused_hits: list[FusedHit] | None = None
    candidates: list[TicketCandidateTrace] | None = None
    contexts: list[TicketContext] | None = None
    reranked: list[RerankedCandidate] | None = None
    decision: DecisionResult | None = None
    timings_ms: dict[str, float] = field(default_factory=dict)
    total_time_ms: float = 0.0

    @property
    def recommended_ticket_id(self) -> uuid.UUID | None:
        if self.path == "auto_attach" and self.thread_match is not None:
            return self.thread_match.ticket.id
        if self.path == "ai_decision" and self.decision is not None and self.decision.should_attach:
            return self.decision.ticket_id
        return None


def _match_score(hit: FusedHit) -> float:
    # Same selection rule grouping.py's own (private) aggregation uses --
    # duplicated here (not imported) since it's a 3-line display concern,
    # not business logic being re-implemented.
    if hit.ann_score is not None:
        return hit.ann_score
    if hit.keyword_score is not None:
        return hit.keyword_score
    return 0.0


def _with_matched_scores(
    candidates: list[TicketCandidate], fused_hits: list[FusedHit]
) -> list[TicketCandidateTrace]:
    score_by_interaction = {hit.interaction_id: _match_score(hit) for hit in fused_hits}
    return [
        TicketCandidateTrace(
            ticket_id=c.ticket_id,
            max_score=c.max_score,
            topk_avg=c.topk_avg,
            recency_score=c.recency_score,
            final_score=c.final_score,
            matched_interactions=[
                MatchedInteraction(
                    interaction_id=iid, match_score=score_by_interaction.get(iid, 0.0)
                )
                for iid in c.matched_interaction_ids
            ],
        )
        for c in candidates
    ]


def run_traced_pipeline(
    session: Session,
    email,  # recommender.pipeline.IncomingEmail
    config: RecommenderConfig = settings,
    now: datetime.datetime | None = None,
) -> PipelineTrace:
    now = now or datetime.datetime.now(datetime.timezone.utc)
    timings: dict[str, float] = {}
    pipeline_start = time.perf_counter()

    with _Stopwatch() as sw:
        preprocessed = preprocess_incoming_email(email.subject, email.body, email.sender_email)
    timings["preprocessing"] = sw.elapsed_ms

    with _Stopwatch() as sw:
        customer = identify_customer(session, preprocessed.sender_email)
    timings["customer_identification"] = sw.elapsed_ms

    if customer is None:
        return PipelineTrace(
            path="unknown_customer",
            preprocessed=preprocessed,
            timings_ms=timings,
            total_time_ms=(time.perf_counter() - pipeline_start) * 1000.0,
        )

    thread_match: ThreadMatch | None = None
    if config.thread_detection.enabled:
        with _Stopwatch() as sw:
            thread_match = detect_thread(
                session,
                conversation_id=email.conversation_id,
                in_reply_to=email.in_reply_to,
                reference_message_ids=email.reference_message_ids,
            )
        timings["thread_detection"] = sw.elapsed_ms

        if thread_match is not None:
            return PipelineTrace(
                path="auto_attach",
                customer=customer,
                preprocessed=preprocessed,
                thread_match=thread_match,
                timings_ms=timings,
                total_time_ms=(time.perf_counter() - pipeline_start) * 1000.0,
            )

    with _Stopwatch() as sw:
        query_embedding = embed_text(
            preprocessed.embedding_text,
            model=config.ollama.embedding_model,
            host=config.ollama.host,
        )
    timings["embedding"] = sw.elapsed_ms
    embedding_stats = EmbeddingStats(
        model=config.ollama.embedding_model,
        dimension=len(query_embedding),
        norm=sum(x * x for x in query_embedding) ** 0.5,
        min=min(query_embedding),
        max=max(query_embedding),
        preview_first_20=query_embedding[:20],
    )

    with _Stopwatch() as sw:
        keyword_hits = keyword_search(
            session, preprocessed.embedding_text, customer.id, config.retrieval.keyword_top_n
        )
    timings["keyword_search"] = sw.elapsed_ms

    with _Stopwatch() as sw:
        ann_hits = ann_search(
            session, query_embedding, customer.id, config.retrieval.ann_top_n
        )
    timings["ann_search"] = sw.elapsed_ms

    with _Stopwatch() as sw:
        keyword_scores = {h.interaction_id: h.score for h in keyword_hits}
        ann_scores = {h.interaction_id: h.score for h in ann_hits}
        fused_hits = reciprocal_rank_fusion(
            [h.interaction_id for h in keyword_hits],
            [h.interaction_id for h in ann_hits],
            keyword_scores,
            ann_scores,
            k=config.retrieval.rrf_k,
            top_n=config.retrieval.fusion_top_n,
        )
    timings["hybrid_retrieval"] = sw.elapsed_ms

    with _Stopwatch() as sw:
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
    timings["grouping"] = sw.elapsed_ms

    with _Stopwatch() as sw:
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
    timings["context_building"] = sw.elapsed_ms

    with _Stopwatch() as sw:
        reranked = rerank(
            preprocessed.embedding_text,
            contexts,
            model_name=config.reranker.model_name,
            device=config.reranker.device,
            top_k=config.reranker.top_k,
        )
    timings["reranking"] = sw.elapsed_ms

    contexts_by_ticket = {c.ticket_id: c for c in contexts}
    decision_input = [
        (contexts_by_ticket[r.ticket_id], r.rerank_score)
        for r in reranked
        if r.ticket_id in contexts_by_ticket
    ]

    with _Stopwatch() as sw:
        decision = decide(
            preprocessed.embedding_text,
            decision_input,
            model=config.decision.model,
            host=config.ollama.host,
            temperature=config.decision.temperature,
            timeout=config.decision.timeout_s,
        )
    timings["llm_decision"] = sw.elapsed_ms

    trace = PipelineTrace(
        path="ai_decision",
        customer=customer,
        preprocessed=preprocessed,
        query_embedding_stats=embedding_stats,
        keyword_hits=keyword_hits,
        ann_hits=ann_hits,
        fused_hits=fused_hits,
        candidates=_with_matched_scores(candidates, fused_hits),
        contexts=contexts,
        reranked=reranked,
        decision=decision,
        timings_ms=timings,
        total_time_ms=(time.perf_counter() - pipeline_start) * 1000.0,
    )
    return trace
