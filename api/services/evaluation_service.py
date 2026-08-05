"""Reads eval-run result files scripts/run_eval.py writes via --output and
summarizes them for the debug dashboard's Evaluation page. Pure filesystem
read -- no database session, no pipeline execution -- this only reports on
runs that have already happened.
"""

from __future__ import annotations

import json
from pathlib import Path

from recommender.config import REPO_ROOT
from recommender.eval_reporting import summarize_results

from api.schemas.evaluation import (
    ABBenchmarkResponse,
    ABComparisonSummary,
    ABPipelineRun,
    ABQueryResult,
    CategoryBreakdown,
    EvalQueryResult,
    EvalRunDetail,
    EvalRunSummary,
    EvaluationStatusResponse,
    HardCaseResult,
)

RESULTS_DIR = REPO_ROOT / "data" / "sample_dataset"
RESULTS_GLOB = "eval_results_*.json"
AB_RESULTS_GLOB = "ab_benchmark_*.json"

NO_RUNS_MESSAGE = (
    "No eval run results found yet. Generate one with: "
    "python scripts/run_eval.py --output data/sample_dataset/eval_results_<date>.json"
)

NO_AB_RUNS_MESSAGE = (
    "No A/B benchmark results found yet. Generate one with: "
    "python scripts/run_ab_benchmark.py --output data/sample_dataset/ab_benchmark_<date>.json"
)


def _load_run_file(path: Path) -> tuple[str | None, list[dict]]:
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)
    if isinstance(payload, list):
        # Pre-2026-08-03 flat-list format, if an older file is ever restored.
        return None, payload
    return payload.get("generated_at"), payload.get("results", [])


def _to_category_schema(categories) -> list[CategoryBreakdown]:
    return [
        CategoryBreakdown(
            category=c.category,
            clear_correct=c.clear_correct,
            clear_total=c.clear_total,
            recall20_correct=c.recall20_correct,
            recall20_total=c.recall20_total,
            recall3_correct=c.recall3_correct,
            recall3_total=c.recall3_total,
            avg_confidence_correct=c.avg_confidence_correct,
        )
        for c in categories
    ]


def _to_summary_schema(source_file: str, generated_at: str | None, summary) -> EvalRunSummary:
    return EvalRunSummary(
        generated_at=generated_at,
        source_file=source_file,
        total_queries=summary.total_queries,
        clear_correct=summary.clear_correct,
        clear_total=summary.clear_total,
        recall20_correct=summary.recall20_correct,
        recall20_total=summary.recall20_total,
        recall3_correct=summary.recall3_correct,
        recall3_total=summary.recall3_total,
        hard_correct=summary.hard_correct,
        hard_total=summary.hard_total,
        categories=_to_category_schema(summary.categories),
    )


def get_evaluation_status() -> EvaluationStatusResponse:
    paths = sorted(RESULTS_DIR.glob(RESULTS_GLOB))
    if not paths:
        return EvaluationStatusResponse(implemented=True, message=NO_RUNS_MESSAGE, latest=None, history=[])

    runs: list[tuple[str, str | None, list[dict]]] = []
    for path in paths:
        generated_at, results = _load_run_file(path)
        runs.append((path.name, generated_at, results))

    # Sort chronologically by generated_at when present, falling back to
    # filename (both embed a sortable date) so ordering is stable either way.
    runs.sort(key=lambda r: r[1] or r[0])

    history = [
        _to_summary_schema(name, generated_at, summarize_results(results))
        for name, generated_at, results in runs
    ]

    latest_name, latest_generated_at, latest_results = runs[-1]
    latest_summary = summarize_results(latest_results)
    latest = EvalRunDetail(
        **_to_summary_schema(latest_name, latest_generated_at, latest_summary).model_dump(),
        hard_cases=[
            HardCaseResult(
                key=hc.key,
                correct=hc.correct,
                actual_ticket_key=hc.actual_ticket_key,
                confidence=hc.confidence,
            )
            for hc in latest_summary.hard_cases
        ],
        failed_clear_keys=latest_summary.failed_clear_keys,
        results=[EvalQueryResult(**r) for r in latest_results],
    )

    return EvaluationStatusResponse(implemented=True, latest=latest, history=history)


def get_ab_benchmark_status() -> ABBenchmarkResponse:
    """Reads the latest ab_benchmark_*.json written by
    scripts/run_ab_benchmark.py -- same pure-filesystem-read pattern as
    get_evaluation_status above, a distinct glob so the two never collide."""
    paths = sorted(RESULTS_DIR.glob(AB_RESULTS_GLOB))
    if not paths:
        return ABBenchmarkResponse(implemented=True, message=NO_AB_RUNS_MESSAGE)

    path = paths[-1]
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)

    generated_at = payload.get("generated_at")
    source_file = path.name

    with_results = payload["with_reranker"]["results"]
    no_results = payload["no_reranker"]["results"]

    return ABBenchmarkResponse(
        implemented=True,
        generated_at=generated_at,
        source_file=source_file,
        warmup_performed=payload.get("warmup_performed"),
        with_reranker=ABPipelineRun(
            summary=_to_summary_schema(source_file, generated_at, summarize_results(with_results)),
            results=[ABQueryResult(**r) for r in with_results],
        ),
        no_reranker=ABPipelineRun(
            summary=_to_summary_schema(source_file, generated_at, summarize_results(no_results)),
            results=[ABQueryResult(**r) for r in no_results],
        ),
        comparison=ABComparisonSummary(**payload["comparison"]),
    )
