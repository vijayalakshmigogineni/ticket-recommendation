"""Experimental, debug-dashboard-only traced pipeline that isolates the
cross-encoder reranker's contribution to end-to-end latency (see
recommender/reranker.py's docstring for why the reranker was suspected as a
bottleneck). NOT a modification of recommender/pipeline.py or
recommender/pipeline_trace.py -- a second parallel orchestration, following
pipeline_trace.py's own precedent, that calls the exact same public stage
functions those two call (importing nothing new, inventing no new
scoring/decision logic), except it never calls recommender/reranker.py's
rerank().

Everything through grouping is identical to pipeline_trace.py. From there:
  - Skip the cross-encoder entirely.
  - Take the top `config.reranker.top_k` candidates directly from grouping's
    own final_score ordering (group_and_aggregate already sorts by
    final_score descending) instead of the reranked order.
  - Build context only for those candidates (not all top_m_candidates) --
    context was only ever built for all of them so the cross-encoder had
    text to score; skipping the cross-encoder removes that need too.
  - Pass final_score to the LLM decision layer in place of a rerank score,
    with a neutral prompt label ("match score") so the LLM isn't told a
    cross-encoder ran when it didn't.

recommender/pipeline.py, recommender/pipeline_trace.py, recommender/reranker.py,
recommender/decision.py's default behavior, and every other stage module are
untouched by this file's existence.
"""

from __future__ import annotations

import datetime
import time

from sqlalchemy.orm import Session

from recommender.config import RecommenderConfig, settings
from recommender.context_builder import build_ticket_context
from recommender.customer_identification import identify_customer
from recommender.decision import decide
from recommender.grouping import group_and_aggregate
from recommender.ollama_client import embed_text
from recommender.pipeline_trace import (
    EmbeddingStats,
    PipelineTrace,
    _Stopwatch,
    _with_matched_scores,
)
from recommender.preprocessing import preprocess_incoming_email
from recommender.retrieval.ann_search import ann_search
from recommender.retrieval.hybrid import reciprocal_rank_fusion
from recommender.retrieval.keyword_search import keyword_search
from recommender.thread_detection import detect_thread

SCORE_LABEL = "match score"


def run_traced_pipeline_no_reranker(
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

    thread_match = None
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
        ann_hits = ann_search(session, query_embedding, customer.id, config.retrieval.ann_top_n)
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

    # group_and_aggregate already sorts by final_score descending -- this is
    # the one substantive difference from pipeline_trace.py: instead of
    # building context for all top_m_candidates and letting the
    # cross-encoder narrow to top_k, take top_k directly off that ordering.
    top_candidates = candidates[: config.reranker.top_k]

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
            for candidate in top_candidates
        ]
    timings["context_building"] = sw.elapsed_ms

    # No cross-encoder call at all -- recorded as 0ms (not "missing") so the
    # dashboard timeline can render an explicit "0 ms / bypassed" stage
    # instead of silently omitting it.
    timings["reranking"] = 0.0

    decision_input = list(zip(contexts, [c.final_score for c in top_candidates]))

    with _Stopwatch() as sw:
        decision = decide(
            preprocessed.embedding_text,
            decision_input,
            model=config.decision.model,
            host=config.ollama.host,
            temperature=config.decision.temperature,
            timeout=config.decision.timeout_s,
            score_label=SCORE_LABEL,
        )
    timings["llm_decision"] = sw.elapsed_ms

    return PipelineTrace(
        path="ai_decision",
        customer=customer,
        preprocessed=preprocessed,
        query_embedding_stats=embedding_stats,
        keyword_hits=keyword_hits,
        ann_hits=ann_hits,
        fused_hits=fused_hits,
        candidates=_with_matched_scores(candidates, fused_hits),
        contexts=contexts,
        reranked=None,
        decision=decision,
        timings_ms=timings,
        total_time_ms=(time.perf_counter() - pipeline_start) * 1000.0,
    )
