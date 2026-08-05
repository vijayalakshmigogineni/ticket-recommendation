"""Shared aggregation logic for eval results -- computes the same clear-case
accuracy / Recall@20 / Recall@3 / hard-case tracking / per-category breakdown
that scripts/run_eval.py has always printed to the console, in one place, so
the CLI report and the debug-dashboard Evaluation page can never drift apart.

Operates purely on the per-query result dicts scripts/run_eval.py builds (and
writes via --output) -- doesn't run the pipeline or touch the database itself.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CategoryBreakdown:
    category: str
    clear_correct: int
    clear_total: int
    recall20_correct: int
    recall20_total: int
    recall3_correct: int
    recall3_total: int
    avg_confidence_correct: float | None


@dataclass
class HardCaseResult:
    key: str
    correct: bool
    actual_ticket_key: str | None
    confidence: float | None
    # None for hard cases predating this taxonomy split, or if the source
    # query dict omitted it -- treated as "single_answer" for reporting
    # purposes (see summarize_results), the more conservative assumption.
    ambiguity_type: str | None = None


@dataclass
class EvalSummary:
    total_queries: int
    clear_correct: int
    clear_total: int
    recall20_correct: int
    recall20_total: int
    recall3_correct: int
    recall3_total: int
    hard_correct: int
    hard_total: int
    hard_cases: list[HardCaseResult]
    categories: list[CategoryBreakdown]
    failed_clear_keys: list[str]
    total_elapsed_s: float
    # Split view of the same hard cases above by ambiguity_type -- a single
    # "hard cases passed" number conflates two different capabilities:
    # multi_acceptable cases (genuinely ambiguous; declining is defensible,
    # not a real gap) and single_answer cases (one correct ticket; declining
    # or a miss IS a real gap). See eval_queries.py's module docstring.
    multi_acceptable_correct: int = 0
    multi_acceptable_total: int = 0
    single_answer_correct: int = 0
    single_answer_total: int = 0


def summarize_results(results: list[dict]) -> EvalSummary:
    clear = [r for r in results if r["difficulty"] == "clear"]
    hard = [r for r in results if r["difficulty"] == "hard"]

    recall20_pool = [r for r in results if r.get("recall20") is not None]
    recall3_pool = [r for r in results if r.get("recall3") is not None]

    hard_cases = [
        HardCaseResult(
            key=r["key"],
            correct=r["correct"],
            actual_ticket_key=r.get("actual_ticket_key"),
            confidence=r.get("confidence"),
            ambiguity_type=r.get("ambiguity_type"),
        )
        for r in hard
    ]
    multi_acceptable = [hc for hc in hard_cases if hc.ambiguity_type == "multi_acceptable"]
    single_answer = [hc for hc in hard_cases if hc.ambiguity_type != "multi_acceptable"]

    categories = sorted({r.get("category", "uncategorized") for r in results})
    category_breakdowns = []
    for cat in categories:
        cat_clear = [r for r in clear if r.get("category", "uncategorized") == cat]
        if not cat_clear:
            continue
        cat_recall20 = [r for r in cat_clear if r.get("recall20") is not None]
        cat_recall3 = [r for r in cat_clear if r.get("recall3") is not None]
        confs_correct = [
            r["confidence"] for r in cat_clear if r["correct"] and r.get("confidence") is not None
        ]
        category_breakdowns.append(
            CategoryBreakdown(
                category=cat,
                clear_correct=sum(r["correct"] for r in cat_clear),
                clear_total=len(cat_clear),
                recall20_correct=sum(r["recall20"] for r in cat_recall20),
                recall20_total=len(cat_recall20),
                recall3_correct=sum(r["recall3"] for r in cat_recall3),
                recall3_total=len(cat_recall3),
                avg_confidence_correct=(
                    sum(confs_correct) / len(confs_correct) if confs_correct else None
                ),
            )
        )

    return EvalSummary(
        total_queries=len(results),
        clear_correct=sum(r["correct"] for r in clear),
        clear_total=len(clear),
        recall20_correct=sum(r["recall20"] for r in recall20_pool),
        recall20_total=len(recall20_pool),
        recall3_correct=sum(r["recall3"] for r in recall3_pool),
        recall3_total=len(recall3_pool),
        hard_correct=sum(r["correct"] for r in hard),
        hard_total=len(hard),
        hard_cases=hard_cases,
        categories=category_breakdowns,
        failed_clear_keys=[r["key"] for r in clear if not r["correct"]],
        total_elapsed_s=sum(r["elapsed_s"] for r in results),
        multi_acceptable_correct=sum(hc.correct for hc in multi_acceptable),
        multi_acceptable_total=len(multi_acceptable),
        single_answer_correct=sum(hc.correct for hc in single_answer),
        single_answer_total=len(single_answer),
    )


def format_console_report(summary: EvalSummary) -> str:
    lines: list[str] = ["\n" + "=" * 60]

    if summary.clear_total:
        pct = 100 * summary.clear_correct / summary.clear_total
        lines.append(
            f"CLEAR-CASE ACCURACY: {summary.clear_correct}/{summary.clear_total} ({pct:.0f}%)"
        )
    else:
        lines.append("No clear-difficulty queries were run.")

    if summary.recall20_total:
        pct = 100 * summary.recall20_correct / summary.recall20_total
        lines.append(
            f"Recall@20 (candidate pool): {summary.recall20_correct}/{summary.recall20_total} ({pct:.0f}%)"
        )
    if summary.recall3_total:
        pct = 100 * summary.recall3_correct / summary.recall3_total
        lines.append(
            f"Recall@3 (reranked top-K):  {summary.recall3_correct}/{summary.recall3_total} ({pct:.0f}%)"
        )

    if summary.hard_total:
        lines.append(
            f"\nHARD/AMBIGUOUS cases (informational only, not in headline accuracy): "
            f"{summary.hard_correct}/{summary.hard_total} passed"
        )
        if summary.single_answer_total:
            lines.append(
                f"  Single-answer (one correct ticket -- a miss here IS a real gap): "
                f"{summary.single_answer_correct}/{summary.single_answer_total} passed"
            )
            for hc in summary.hard_cases:
                if hc.ambiguity_type == "multi_acceptable":
                    continue
                lines.append(
                    f"    {hc.key}: {'PASS' if hc.correct else 'FAIL'} "
                    f"(got {hc.actual_ticket_key}, confidence={hc.confidence})"
                )
        if summary.multi_acceptable_total:
            lines.append(
                f"  Multi-acceptable (genuinely ambiguous -- declining is defensible, "
                f"not necessarily a gap): {summary.multi_acceptable_correct}/{summary.multi_acceptable_total} passed"
            )
            for hc in summary.hard_cases:
                if hc.ambiguity_type != "multi_acceptable":
                    continue
                lines.append(
                    f"    {hc.key}: {'PASS' if hc.correct else 'FAIL'} "
                    f"(got {hc.actual_ticket_key}, confidence={hc.confidence})"
                )

    if summary.failed_clear_keys:
        lines.append(
            f"\nFailed CLEAR-case queries (investigate first): "
            f"{', '.join(summary.failed_clear_keys)}"
        )

    if len(summary.categories) > 1:
        lines.append("\n" + "-" * 60)
        lines.append("PER-CATEGORY BREAKDOWN (clear-difficulty cases only):")
        for cb in summary.categories:
            line = f"  {cb.category}: {cb.clear_correct}/{cb.clear_total} accuracy"
            if cb.recall20_total:
                line += f", Recall@20 {cb.recall20_correct}/{cb.recall20_total}"
            if cb.recall3_total:
                line += f", Recall@3 {cb.recall3_correct}/{cb.recall3_total}"
            if cb.avg_confidence_correct is not None:
                line += f", avg confidence {cb.avg_confidence_correct:.2f}"
            lines.append(line)

    lines.append(
        f"\nTotal eval time: {summary.total_elapsed_s / 60:.1f} min across {summary.total_queries} queries"
    )
    return "\n".join(lines)
