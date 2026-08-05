from __future__ import annotations

import datetime
import uuid

from pydantic import BaseModel

from api.schemas.common import CustomerRef, TicketRef


class RunRequest(BaseModel):
    subject: str
    body: str
    sender_email: str
    message_id: str | None = None
    conversation_id: str | None = None
    in_reply_to: str | None = None
    reference_message_ids: list[str] = []
    now: datetime.datetime | None = None


class ScoredInteractionRef(BaseModel):
    interaction_id: uuid.UUID
    ticket: TicketRef | None
    score: float
    preview: str


class PreprocessingTrace(BaseModel):
    original_subject: str
    original_body: str
    clean_body: str
    embedding_text: str
    time_ms: float


class ThreadDetectionTrace(BaseModel):
    enabled: bool
    matched: bool
    matched_on: str | None
    ticket: TicketRef | None
    matched_interaction_id: uuid.UUID | None
    time_ms: float


class EmbeddingTrace(BaseModel):
    model: str
    dimension: int
    time_ms: float
    norm: float
    min: float
    max: float
    preview_first_20: list[float]


class KeywordSearchTrace(BaseModel):
    top_n: int
    time_ms: float
    hits: list[ScoredInteractionRef]


class AnnSearchTrace(BaseModel):
    top_n: int
    time_ms: float
    hits: list[ScoredInteractionRef]


class FusedHitOut(BaseModel):
    interaction_id: uuid.UUID
    ticket: TicketRef | None
    preview: str
    fused_score: float
    keyword_score: float | None
    ann_score: float | None


class FusionTrace(BaseModel):
    rrf_k: int
    fusion_top_n: int
    time_ms: float
    hits: list[FusedHitOut]


class MatchedInteractionOut(BaseModel):
    interaction_id: uuid.UUID
    match_score: float
    preview: str


class TicketCandidateOut(BaseModel):
    ticket: TicketRef
    max_score: float
    topk_avg: float
    recency_score: float
    final_score: float
    matched_interactions: list[MatchedInteractionOut]


class GroupingTrace(BaseModel):
    time_ms: float
    candidates: list[TicketCandidateOut]


class TicketContextOut(BaseModel):
    ticket: TicketRef
    text: str
    char_count: int


class ContextBuildingTrace(BaseModel):
    time_ms: float
    contexts: list[TicketContextOut]


class RerankedOut(BaseModel):
    ticket: TicketRef
    rerank_score: float


class RerankingTrace(BaseModel):
    model_name: str
    time_ms: float
    scores: list[RerankedOut]


class DecisionTrace(BaseModel):
    model: str
    time_ms: float
    system_prompt: str
    user_prompt: str | None
    should_attach: bool
    ticket: TicketRef | None
    confidence: float
    explanation: str


class RunTraceResponse(BaseModel):
    path: str
    total_time_ms: float
    recommended_ticket_id: uuid.UUID | None
    customer: CustomerRef | None
    preprocessing: PreprocessingTrace | None
    thread_detection: ThreadDetectionTrace | None
    embedding: EmbeddingTrace | None
    keyword_search: KeywordSearchTrace | None
    ann_search: AnnSearchTrace | None
    fusion: FusionTrace | None
    grouping: GroupingTrace | None
    context_building: ContextBuildingTrace | None
    reranking: RerankingTrace | None
    decision: DecisionTrace | None
    stage_timings_ms: dict[str, float]
    # Default keeps the existing /api/run response unchanged for every
    # current caller; only the /api/run/compare experimental endpoint sets
    # this to "no_reranker".
    pipeline_variant: str = "with_reranker"


class RunCompareResponse(BaseModel):
    """Both pipelines run against the same email, for side-by-side
    comparison in the dashboard. Each half is a plain RunTraceResponse --
    same shape the Pipeline Explorer already renders."""

    with_reranker: RunTraceResponse
    no_reranker: RunTraceResponse
