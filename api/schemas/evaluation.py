from __future__ import annotations

from pydantic import BaseModel


class CategoryBreakdown(BaseModel):
    category: str
    clear_correct: int
    clear_total: int
    recall20_correct: int
    recall20_total: int
    recall3_correct: int
    recall3_total: int
    avg_confidence_correct: float | None


class HardCaseResult(BaseModel):
    key: str
    correct: bool
    actual_ticket_key: str | None
    confidence: float | None


class EvalQueryResult(BaseModel):
    key: str
    category: str
    difficulty: str
    expected_ticket_keys: list[str] | None
    actual_ticket_key: str | None
    correct: bool
    recall20: bool | None
    recall3: bool | None
    path: str
    confidence: float | None
    explanation: str | None
    elapsed_s: float


class EvalRunSummary(BaseModel):
    generated_at: str | None
    source_file: str
    total_queries: int
    clear_correct: int
    clear_total: int
    recall20_correct: int
    recall20_total: int
    recall3_correct: int
    recall3_total: int
    hard_correct: int
    hard_total: int
    categories: list[CategoryBreakdown]


class EvalRunDetail(EvalRunSummary):
    hard_cases: list[HardCaseResult]
    failed_clear_keys: list[str]
    results: list[EvalQueryResult]


class EvaluationStatusResponse(BaseModel):
    implemented: bool
    message: str | None = None
    latest: EvalRunDetail | None = None
    history: list[EvalRunSummary] = []


# --- A/B benchmark (with vs. without the cross-encoder reranker) ---


class ABQueryResult(EvalQueryResult):
    """Same shape as EvalQueryResult (so scripts/run_eval.py's
    summarize_results/format_console_report work on these rows unmodified),
    plus the per-stage timings the A/B harness records that the
    single-pipeline eval doesn't currently persist."""

    timings_ms: dict[str, float]
    total_time_ms: float


class ABPipelineRun(BaseModel):
    summary: EvalRunSummary
    results: list[ABQueryResult]


class ABComparisonSummary(BaseModel):
    n_queries: int
    ticket_selection_changed_count: int
    ticket_selection_changed_keys: list[str]
    avg_cross_encoder_ms: float
    avg_total_time_s_with_reranker: float
    avg_total_time_s_no_reranker: float
    clear_accuracy_with_reranker: float | None
    clear_accuracy_no_reranker: float | None
    recall3_with_reranker: float | None
    recall3_no_reranker: float | None
    validation_pass_count: int
    validation_total: int
    validation_failures: list[dict] = []


class ABBenchmarkResponse(BaseModel):
    implemented: bool
    message: str | None = None
    generated_at: str | None = None
    source_file: str | None = None
    warmup_performed: bool | None = None
    with_reranker: ABPipelineRun | None = None
    no_reranker: ABPipelineRun | None = None
    comparison: ABComparisonSummary | None = None
