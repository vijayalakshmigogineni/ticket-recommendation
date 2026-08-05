"""Automated eval harness. Runs every query in
data/sample_dataset/eval_queries.py through the real traced pipeline and
scores the result against its committed ground truth -- no manual
Accept/Reject in the Playground needed.

Reports two distinct kinds of reliability:
- Final-decision accuracy (clear-difficulty queries only; hard/ambiguous
  queries are tracked separately so they don't dilute the headline number)
- Recall@20 / Recall@3: whether the expected ticket appeared in the
  candidate pool (post-grouping, pre-rerank) / reranked top-K at all,
  independent of what the LLM ultimately decided -- isolates retrieval
  quality from LLM decision quality, which scripts/compute_metrics.py
  (manager-feedback-based) cannot do, since feedback only ever sees the
  final decision.

WARNING: ai_decision-path queries call the local LLM (qwen3:4b) and can each
take 30s-3min depending on hardware. A full run over ~20 queries can take
20-40+ minutes. Use --limit to run a subset first.

--repeat N runs each selected query N times instead of once, reporting a
pass-rate/distinct-answers distribution per query instead of a single
boolean. This exists because non-determinism has been confirmed at both the
LLM decision layer and the reranker itself (see EVAL_HISTORY.md) -- a single
run's PASS/FAIL has an unknown noise floor, so every prior "no regression"
claim implicitly assumed single-run stability that was never actually
checked except on the handful of cases that happened to fail. Combine with
--keys to target a specific set of queries (known-flaky cases, or a
stratified clear-case sample) rather than repeating the entire suite, which
would be expensive for little marginal value on cases with wide score
margins that are very unlikely to ever flip.

--output with --repeat writes a differently-shaped payload (per-query
"runs" list, not a flat "correct" boolean) than normal single-run output.
Do NOT write it into data/sample_dataset/eval_results_*.json -- the
dashboard's evaluation_service.py globs exactly that filename pattern and
expects the normal single-run shape; use a distinct name (e.g.
noise_floor_<date>.json) instead.

Usage:
    python scripts/run_eval.py             # full eval set
    python scripts/run_eval.py --limit 5    # first 5 queries only
    python scripts/run_eval.py --keys archive_c4_claims_selfresolved,info_ambiguous_archive_boundary --repeat 5
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
from data.sample_dataset.seed_data import TICKETS  # noqa: E402
from recommender.config import settings  # noqa: E402
from recommender.db import SessionLocal  # noqa: E402
from recommender.eval_reporting import format_console_report, summarize_results  # noqa: E402
from recommender.ollama_client import get_model_info  # noqa: E402
from recommender.pipeline import IncomingEmail  # noqa: E402
from recommender.pipeline_trace import run_traced_pipeline  # noqa: E402

# Must match scripts/seed_data.py's NAMESPACE exactly -- this is how a ticket
# "key" like "C1" resolves to the actual UUID seeded into the database.
NAMESPACE = uuid.UUID("a3f5e1b0-5a4e-4b8a-9c1e-2f6d8b1a7c00")


def stable_id(key: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, key)


# Reverse lookup so failure output can show human ticket keys ("E7") instead
# of raw UUIDs.
KEY_BY_ID = {stable_id(t["key"]): t["key"] for t in TICKETS}


def _run_once(session, q: dict, expected_ids: set[uuid.UUID] | None) -> dict:
    """One pipeline run for one query. Returns the per-run outcome only
    (not the query-level metadata like key/category/difficulty, which the
    caller already has and which doesn't vary across repeats)."""
    email = IncomingEmail(
        subject=q["subject"],
        body=q["body"],
        sender_email=q["sender_email"],
        message_id=f"<eval-{q['key']}@dashboard.local>",
        conversation_id=q.get("conversation_id"),
        in_reply_to=q.get("in_reply_to"),
        reference_message_ids=q.get("reference_message_ids", []),
    )

    start = time.perf_counter()
    trace = run_traced_pipeline(session, email, now=datetime.datetime.now(datetime.timezone.utc))
    elapsed = time.perf_counter() - start

    actual_id = trace.recommended_ticket_id
    correct = actual_id is None if expected_ids is None else actual_id in expected_ids

    recall20 = recall3 = None
    if expected_ids is not None and trace.candidates is not None:
        recall20 = bool(expected_ids & {c.ticket_id for c in trace.candidates})
    if expected_ids is not None and trace.reranked is not None:
        recall3 = bool(expected_ids & {r.ticket_id for r in trace.reranked})

    confidence = trace.decision.confidence if trace.decision is not None else None
    explanation = trace.decision.explanation if trace.decision is not None else None

    return {
        "actual_ticket_key": KEY_BY_ID.get(actual_id) if actual_id else None,
        "correct": correct,
        "recall20": recall20,
        "recall3": recall3,
        "path": trace.path,
        "confidence": confidence,
        "explanation": explanation,
        "elapsed_s": elapsed,
    }


def _collect_model_info() -> dict:
    """Model identity metadata (digest, modified_at, quantization) for every
    model this run depends on -- recorded so a future unexplained result
    shift can rule "the model silently changed" in or out, instead of being
    indistinguishable from already-confirmed sampling non-determinism."""
    return {
        "decision_model": get_model_info(settings.decision.model, host=settings.ollama.host),
        "embedding_model": get_model_info(settings.ollama.embedding_model, host=settings.ollama.host),
    }


def _select_queries(args: argparse.Namespace) -> list[dict]:
    queries = EVAL_QUERIES
    if args.keys:
        wanted = {k.strip() for k in args.keys.split(",") if k.strip()}
        by_key = {q["key"]: q for q in queries}
        missing = wanted - by_key.keys()
        if missing:
            print(f"WARNING: unknown query key(s), ignored: {', '.join(sorted(missing))}")
        queries = [q for q in queries if q["key"] in wanted]
    if args.limit:
        queries = queries[: args.limit]
    return queries


def _run_single_pass(session, queries: list[dict]) -> list[dict]:
    results = []
    for i, q in enumerate(queries, start=1):
        expected_ids = (
            {stable_id(k) for k in q["expected_ticket_keys"]} if q["expected_ticket_keys"] else None
        )
        print(f"[{i}/{len(queries)}] {q['key']}: {q['note']}", flush=True)
        run_result = _run_once(session, q, expected_ids)
        results.append(
            {
                "key": q["key"],
                "category": q.get("category", "uncategorized"),
                "difficulty": q["difficulty"],
                "ambiguity_type": q.get("ambiguity_type"),
                "expected_ticket_keys": q["expected_ticket_keys"],
                **run_result,
            }
        )
        print(f"    -> {'PASS' if run_result['correct'] else 'FAIL'} (path={run_result['path']}, {run_result['elapsed_s']:.1f}s)")
    return results


def _run_repeated(session, queries: list[dict], repeat: int) -> list[dict]:
    rows = []
    for qi, q in enumerate(queries, start=1):
        expected_ids = (
            {stable_id(k) for k in q["expected_ticket_keys"]} if q["expected_ticket_keys"] else None
        )
        print(f"\n[{qi}/{len(queries)}] {q['key']}: {q['note']}", flush=True)
        runs = []
        for attempt in range(1, repeat + 1):
            run_result = _run_once(session, q, expected_ids)
            runs.append(run_result)
            print(
                f"    attempt {attempt}/{repeat}: {'PASS' if run_result['correct'] else 'FAIL'} "
                f"(got={run_result['actual_ticket_key']}, confidence={run_result['confidence']}, "
                f"{run_result['elapsed_s']:.1f}s)"
            )
        pass_count = sum(r["correct"] for r in runs)
        distinct_answers = sorted(
            {r["actual_ticket_key"] for r in runs}, key=lambda x: (x is None, x)
        )
        rows.append(
            {
                "key": q["key"],
                "category": q.get("category", "uncategorized"),
                "difficulty": q["difficulty"],
                "ambiguity_type": q.get("ambiguity_type"),
                "expected_ticket_keys": q["expected_ticket_keys"],
                "runs": runs,
                "pass_count": pass_count,
                "run_count": len(runs),
                "pass_rate": pass_count / len(runs),
                "distinct_answers": distinct_answers,
                "stable": len(distinct_answers) <= 1,
            }
        )
    return rows


def _print_repeat_summary(rows: list[dict]) -> None:
    print("\n" + "=" * 60)
    print(f"NOISE-FLOOR SUMMARY ({rows[0]['run_count']}x each, {len(rows)} queries)")
    print("=" * 60)
    for row in rows:
        flag = "" if row["stable"] else "  <-- UNSTABLE (different answers across repeats)"
        print(
            f"  {row['key']}: {row['pass_count']}/{row['run_count']} passed, "
            f"answers seen={row['distinct_answers']}{flag}"
        )
    unstable = [r for r in rows if not r["stable"]]
    print(
        f"\n{len(unstable)}/{len(rows)} queries showed run-to-run instability "
        f"(different actual_ticket_key across identical repeated inputs)."
    )
    if unstable:
        print("Unstable query keys: " + ", ".join(r["key"] for r in unstable))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Run only the first N (post --keys filter) queries")
    parser.add_argument(
        "--keys", type=str, default=None,
        help="Comma-separated query keys to run (e.g. known-flaky cases + a stratified clear sample). "
        "Applied before --limit.",
    )
    parser.add_argument(
        "--repeat", type=int, default=1,
        help="Run each selected query this many times and report a pass-rate/distinct-answers "
        "distribution instead of a single boolean. See module docstring before running this over "
        "the full suite -- target --keys to a small set instead.",
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Write full per-query results as JSON to this path. With --repeat > 1, do NOT use the "
        "eval_results_*.json naming convention -- see module docstring.",
    )
    args = parser.parse_args()

    queries = _select_queries(args)
    if not queries:
        print("No queries matched --keys/--limit. Nothing to run.")
        return

    model_info = _collect_model_info()

    session = SessionLocal()
    try:
        if args.repeat > 1:
            rows = _run_repeated(session, queries, args.repeat)
        else:
            results = _run_single_pass(session, queries)
    finally:
        session.close()

    if args.repeat > 1:
        _print_repeat_summary(rows)
        if args.output:
            payload = {
                "mode": "repeat",
                "repeat_count": args.repeat,
                "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "model_info": model_info,
                "queries": rows,
            }
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, default=str)
            print(f"\nFull per-query repeat results written to {args.output}")
        return

    summary = summarize_results(results)
    print(format_console_report(summary))

    if args.output:
        output_payload = {
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "model_info": model_info,
            "results": results,
        }
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(output_payload, f, indent=2, default=str)
        print(f"\nFull per-query results written to {args.output}")


if __name__ == "__main__":
    main()
