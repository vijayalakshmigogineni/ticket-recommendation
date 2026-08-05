"""Controlled A/B benchmark: runs every query in
data/sample_dataset/eval_queries.py through BOTH the production pipeline
(recommender/pipeline_trace.py, with the cross-encoder reranker) and the
experimental variant (recommender/pipeline_trace_no_reranker.py, which takes
its top candidates directly from grouping's final_score) -- to answer one
question: is the cross-encoder reranker actually earning its keep?

Neither traced pipeline module is modified by this script, and neither is
scripts/run_eval.py: this is a separate, additive harness that reuses the
exact same query set, ground truth, and scoring functions (stable_id,
KEY_BY_ID, _collect_model_info, _select_queries from scripts/run_eval.py;
summarize_results/format_console_report from recommender/eval_reporting.py)
so the two eval paths can never silently drift apart on what "correct" means.

Design choices, and which requirement of the controlled-experiment spec each
one satisfies:

- Warm-up pass (_warm_up): runs one full query through both pipelines before
  any timing is recorded, so the Ollama embedding model, the cross-encoder
  model, and the decision model are all already loaded into memory once the
  timed loop starts. This does NOT warm every customer's rows in Postgres
  (that would mean touching all 73 queries' data before "starting" --
  self-defeating) -- expect small residual per-query DB cache variance
  either pipeline can catch, independent of the reranker. That's normal
  query-to-query noise, not something attributable to the reranker.

- Order alternation (with_first in the main loop): whichever pipeline runs
  first inside a single query always pays a small residual warm/cold tax
  relative to the one that runs second (Postgres statement/page cache,
  mostly). Alternating which pipeline goes first across queries means this
  residual bias lands on each pipeline about equally often across the full
  run instead of always favoring one side.

- Per-stage timing: recommender/pipeline_trace.py and
  recommender/pipeline_trace_no_reranker.py already wrap every stage in a
  _Stopwatch and their total_time_ms is the pipeline_start-to-return wall
  clock -- so total already equals the sum of stages plus negligible
  Python-level bookkeeping between them. Nothing here needed new
  instrumentation; timings_ms is just carried through to the output.

- Validation (_validate_pair): automated per-query checks that both
  pipelines saw the identical pre-rerank candidate pool (grouping is
  untouched code, so this should always hold), sent the same *number* of
  candidates to the LLM, and took the same path (ai_decision /
  auto_attach / unknown_customer). It deliberately does NOT require the two
  pipelines' top-3 *sets* to match -- whether removing the reranker changes
  which 3 candidates get sent to the LLM (and whether that changes the
  final decision) is exactly the thing this experiment measures, not a bug.

Usage:
    python scripts/run_ab_benchmark.py --output data/sample_dataset/ab_benchmark_<date>.json
    python scripts/run_ab_benchmark.py --limit 5   # smoke-test a subset first

WARNING: every query runs through two full pipelines, each of which may call
the local LLM. A full 73-query run can take multiple hours on local
hardware. Use --limit while validating the harness itself.

Do not write --output into the eval_results_*.json naming convention --
api/services/evaluation_service.py globs exactly that pattern for the
single-pipeline eval and would misinterpret this file's two-pipeline shape.
Use ab_benchmark_<date>.json instead (see api/services/evaluation_service.py's
matching ab_benchmark_*.json glob).
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.sample_dataset.eval_queries import EVAL_QUERIES  # noqa: E402
from recommender.db import SessionLocal  # noqa: E402
from recommender.eval_reporting import format_console_report, summarize_results  # noqa: E402
from recommender.pipeline import IncomingEmail  # noqa: E402
from recommender.pipeline_trace import PipelineTrace, run_traced_pipeline  # noqa: E402
from recommender.pipeline_trace_no_reranker import run_traced_pipeline_no_reranker  # noqa: E402
from scripts.run_eval import KEY_BY_ID, _collect_model_info, _select_queries, stable_id  # noqa: E402


def _make_email(q: dict) -> IncomingEmail:
    return IncomingEmail(
        subject=q["subject"],
        body=q["body"],
        sender_email=q["sender_email"],
        message_id=f"<ab-eval-{q['key']}@dashboard.local>",
        conversation_id=q.get("conversation_id"),
        in_reply_to=q.get("in_reply_to"),
        reference_message_ids=q.get("reference_message_ids", []),
    )


def _top_llm_candidate_ids(trace: PipelineTrace) -> set[uuid.UUID]:
    """The ticket IDs actually sent to the LLM decision layer -- reranked
    top-K for the production pipeline, or the (already top-K-sliced)
    contexts for the no-reranker pipeline. This is the one place the two
    traces have a different shape for the "same" concept, so scoring reads
    through this instead of trace.reranked directly (which is always None
    for the no-reranker pipeline, by design -- see that module's docstring)."""
    if trace.reranked is not None:
        return {r.ticket_id for r in trace.reranked}
    if trace.contexts is not None:
        return {c.ticket_id for c in trace.contexts}
    return set()


def _score_result(trace: PipelineTrace, expected_ids: set[uuid.UUID] | None, elapsed_s: float) -> dict:
    actual_id = trace.recommended_ticket_id
    correct = actual_id is None if expected_ids is None else actual_id in expected_ids

    recall20 = recall3 = None
    if expected_ids is not None and trace.candidates is not None:
        recall20 = bool(expected_ids & {c.ticket_id for c in trace.candidates})
    if expected_ids is not None and trace.path == "ai_decision":
        recall3 = bool(expected_ids & _top_llm_candidate_ids(trace))

    return {
        "actual_ticket_key": KEY_BY_ID.get(actual_id) if actual_id else None,
        "correct": correct,
        "recall20": recall20,
        "recall3": recall3,
        "path": trace.path,
        "confidence": trace.decision.confidence if trace.decision is not None else None,
        "explanation": trace.decision.explanation if trace.decision is not None else None,
        "elapsed_s": elapsed_s,
        "timings_ms": trace.timings_ms,
        "total_time_ms": trace.total_time_ms,
    }


def _validate_pair(with_trace: PipelineTrace, no_trace: PipelineTrace) -> dict:
    notes: list[str] = []

    if with_trace.path != no_trace.path:
        notes.append(f"pipeline path differs: with={with_trace.path} no={no_trace.path}")

    with_pool = {c.ticket_id for c in (with_trace.candidates or [])}
    no_pool = {c.ticket_id for c in (no_trace.candidates or [])}
    if with_pool != no_pool:
        notes.append(
            f"grouping candidate pool differs: with={len(with_pool)} candidates, "
            f"no={len(no_pool)} candidates"
        )

    with_sent = len(with_trace.reranked) if with_trace.reranked is not None else 0
    no_sent = len(no_trace.contexts) if no_trace.contexts is not None else 0
    if with_sent != no_sent:
        notes.append(f"candidate count sent to LLM differs: with={with_sent} no={no_sent}")

    with_blocks = with_trace.decision.prompt.count("=== Candidate") if with_trace.decision and with_trace.decision.prompt else 0
    no_blocks = no_trace.decision.prompt.count("=== Candidate") if no_trace.decision and no_trace.decision.prompt else 0
    if with_blocks != no_blocks:
        notes.append(f"candidate blocks in LLM prompt differ: with={with_blocks} no={no_blocks}")

    return {"ok": not notes, "notes": notes}


def _warm_up(session, queries: list[dict]) -> None:
    if not queries:
        return
    warm_email = _make_email(queries[0])
    now = datetime.datetime.now(datetime.timezone.utc)
    print("Warming up (embedding model, cross-encoder model, decision model, DB)...", flush=True)
    run_traced_pipeline(session, warm_email, now=now)
    run_traced_pipeline_no_reranker(session, warm_email, now=now)
    print("Warm-up complete -- starting timed benchmark.\n", flush=True)


def _run_ab_query(session, q: dict, with_first: bool) -> tuple[dict, dict, dict]:
    expected_ids = {stable_id(k) for k in q["expected_ticket_keys"]} if q["expected_ticket_keys"] else None
    email = _make_email(q)
    # Same instant passed to both calls -- group_and_aggregate's recency
    # scoring depends on `now`, so a fresh timestamp per call would leak a
    # (tiny, but avoidable) difference into "same retrieval inputs."
    now = datetime.datetime.now(datetime.timezone.utc)

    def _run_with():
        start = time.perf_counter()
        trace = run_traced_pipeline(session, email, now=now)
        return trace, time.perf_counter() - start

    def _run_no():
        start = time.perf_counter()
        trace = run_traced_pipeline_no_reranker(session, email, now=now)
        return trace, time.perf_counter() - start

    if with_first:
        with_trace, with_elapsed = _run_with()
        no_trace, no_elapsed = _run_no()
    else:
        no_trace, no_elapsed = _run_no()
        with_trace, with_elapsed = _run_with()

    query_meta = {
        "key": q["key"],
        "category": q.get("category", "uncategorized"),
        "difficulty": q["difficulty"],
        "ambiguity_type": q.get("ambiguity_type"),
        "expected_ticket_keys": q["expected_ticket_keys"],
    }
    with_row = {**query_meta, **_score_result(with_trace, expected_ids, with_elapsed)}
    no_row = {**query_meta, **_score_result(no_trace, expected_ids, no_elapsed)}
    validation = {"key": q["key"], **_validate_pair(with_trace, no_trace)}
    return with_row, no_row, validation


def _build_comparison(with_results: list[dict], no_results: list[dict], validations: list[dict]) -> dict:
    n = len(with_results)
    changed = [
        w["key"] for w, r in zip(with_results, no_results) if w["actual_ticket_key"] != r["actual_ticket_key"]
    ]
    cross_encoder_ms = [w["timings_ms"].get("reranking", 0.0) for w in with_results]
    with_summary = summarize_results(with_results)
    no_summary = summarize_results(no_results)

    return {
        "n_queries": n,
        "ticket_selection_changed_count": len(changed),
        "ticket_selection_changed_keys": changed,
        "avg_cross_encoder_ms": sum(cross_encoder_ms) / n if n else 0.0,
        "avg_total_time_s_with_reranker": sum(w["elapsed_s"] for w in with_results) / n if n else 0.0,
        "avg_total_time_s_no_reranker": sum(r["elapsed_s"] for r in no_results) / n if n else 0.0,
        "clear_accuracy_with_reranker": (
            with_summary.clear_correct / with_summary.clear_total if with_summary.clear_total else None
        ),
        "clear_accuracy_no_reranker": (
            no_summary.clear_correct / no_summary.clear_total if no_summary.clear_total else None
        ),
        "recall3_with_reranker": (
            with_summary.recall3_correct / with_summary.recall3_total if with_summary.recall3_total else None
        ),
        "recall3_no_reranker": (
            no_summary.recall3_correct / no_summary.recall3_total if no_summary.recall3_total else None
        ),
        "validation_pass_count": sum(1 for v in validations if v["ok"]),
        "validation_total": len(validations),
        "validation_failures": [v for v in validations if not v["ok"]],
    }


def _print_comparison(cmp: dict) -> None:
    print("\n" + "=" * 60)
    print("A/B COMPARISON -- WITH vs WITHOUT CROSS-ENCODER")
    print("=" * 60)
    print(f"Queries compared: {cmp['n_queries']}")
    print(
        f"Validation: {cmp['validation_pass_count']}/{cmp['validation_total']} query pairs passed "
        f"the automated pre-flight checks (identical grouping pool, identical LLM candidate count, "
        f"identical path)."
    )
    if cmp["validation_failures"]:
        print("  Validation failures:")
        for v in cmp["validation_failures"]:
            for note in v["notes"]:
                print(f"    {v['key']}: {note}")

    def _fmt_pct(x):
        return f"{100 * x:.0f}%" if x is not None else "n/a"

    print(f"\nClear-case accuracy   -- with: {_fmt_pct(cmp['clear_accuracy_with_reranker'])}  "
          f"no: {_fmt_pct(cmp['clear_accuracy_no_reranker'])}")
    print(f"Recall@3 (top-K to LLM) -- with: {_fmt_pct(cmp['recall3_with_reranker'])}  "
          f"no: {_fmt_pct(cmp['recall3_no_reranker'])}")
    print(f"\nAvg cross-encoder time (with-reranker pipeline only): {cmp['avg_cross_encoder_ms']:.0f} ms")
    print(f"Avg total time -- with: {cmp['avg_total_time_s_with_reranker']:.2f}s  "
          f"no: {cmp['avg_total_time_s_no_reranker']:.2f}s")
    print(
        f"\nSelected ticket changed on {cmp['ticket_selection_changed_count']}/{cmp['n_queries']} queries"
        + (f": {', '.join(cmp['ticket_selection_changed_keys'])}" if cmp["ticket_selection_changed_keys"] else "")
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Run only the first N (post --keys filter) queries")
    parser.add_argument(
        "--keys", type=str, default=None,
        help="Comma-separated query keys to run. Applied before --limit.",
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Write full A/B results as JSON to this path. Use ab_benchmark_<date>.json, "
        "NOT eval_results_*.json (see module docstring).",
    )
    parser.add_argument(
        "--skip-warmup", action="store_true",
        help="Skip the warm-up pass (for debugging the harness itself only -- timings from a run "
        "with this flag are not steady-state and should not be used for the actual comparison).",
    )
    args = parser.parse_args()

    queries = _select_queries(args)
    if not queries:
        print("No queries matched --keys/--limit. Nothing to run.")
        return

    model_info = _collect_model_info()

    session = SessionLocal()
    try:
        if not args.skip_warmup:
            _warm_up(session, queries)

        with_results: list[dict] = []
        no_results: list[dict] = []
        validations: list[dict] = []

        for i, q in enumerate(queries, start=1):
            print(f"[{i}/{len(queries)}] {q['key']}: {q['note']}", flush=True)
            with_first = i % 2 == 1  # alternate which pipeline runs first, see module docstring
            with_row, no_row, validation = _run_ab_query(session, q, with_first)
            with_results.append(with_row)
            no_results.append(no_row)
            validations.append(validation)

            rerank_ms = with_row["timings_ms"].get("reranking", 0.0)
            print(
                f"    with-reranker : {'PASS' if with_row['correct'] else 'FAIL'} "
                f"({with_row['elapsed_s']:.1f}s, cross-encoder {rerank_ms:.0f}ms)"
            )
            print(f"    no-reranker   : {'PASS' if no_row['correct'] else 'FAIL'} ({no_row['elapsed_s']:.1f}s)")
            if not validation["ok"]:
                print(f"    VALIDATION WARNING: {validation['notes']}")
    finally:
        session.close()

    print("\n" + "#" * 60)
    print("ORIGINAL PIPELINE (WITH CROSS-ENCODER)")
    print("#" * 60)
    print(format_console_report(summarize_results(with_results)))

    print("\n" + "#" * 60)
    print("EXPERIMENTAL PIPELINE (WITHOUT CROSS-ENCODER)")
    print("#" * 60)
    print(format_console_report(summarize_results(no_results)))

    comparison = _build_comparison(with_results, no_results, validations)
    _print_comparison(comparison)

    if args.output:
        payload = {
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "model_info": model_info,
            "warmup_performed": not args.skip_warmup,
            "with_reranker": {"results": with_results},
            "no_reranker": {"results": no_results},
            "validations": validations,
            "comparison": comparison,
        }
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, default=str)
        print(f"\nFull A/B results written to {args.output}")


if __name__ == "__main__":
    main()
