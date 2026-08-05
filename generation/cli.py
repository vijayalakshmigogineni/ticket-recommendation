"""Entrypoint: python -m generation.cli run --config config/generation_config.yaml
[--stage STAGE] [--seed N] [--model MODEL] [--host HOST]

Resume is implicit, not a separate flag: every Pipeline stage method registers
pending units idempotently and only (re)generates units that are still
pending/retryable -- re-running `run` after an interruption (or after a prior
--stage cutoff) picks up exactly where it left off, by construction of
generation.state.StateStore. Requires a local Ollama server running (see
generation/llm_client.py) -- no API key, no cloud dependency.
"""

from __future__ import annotations

import argparse
import time

from generation.config import GenerationConfig
from generation.pipeline import Pipeline

STAGE_ORDER = [
    "manifest", "customers", "tickets", "conversations", "judge1",
    "eval_queries", "labels", "judge2", "ingest",
]


def _log(start_time: float, message: str) -> None:
    print(f"[{time.time() - start_time:8.1f}s] {message}", flush=True)


def _run_through(pipeline: Pipeline, stop_at: str, seed: int) -> None:
    """Local generation against Ollama is slow (tens of seconds per call) and
    a full-scale config means thousands of calls, so this logs progress after
    every stage rather than running silently for hours."""
    t0 = time.time()

    manifest = pipeline.build_manifest(seed=seed)
    _log(t0, f"manifest: {len(manifest['customers'])} customers, {len(manifest['tickets'])} tickets, {len(manifest['eval_queries'])} eval queries")
    if stop_at == "manifest":
        return

    customers = pipeline.run_customers()
    _log(t0, f"customers: {len(customers)}/{len(manifest['customers'])} passed QA")
    if stop_at == "customers":
        return

    tickets = pipeline.run_tickets(customers)
    _log(t0, f"tickets: {len(tickets)}/{len(manifest['tickets'])} passed QA")
    if stop_at == "tickets":
        return

    conversations = pipeline.run_conversations(customers, tickets)
    _log(t0, f"conversations: {len(conversations)}/{len(tickets)} passed QA")
    if stop_at == "conversations":
        return

    judge1_out = pipeline.run_judge1(tickets, conversations)
    _log(t0, f"judge1: {len(judge1_out)} tickets reviewed")
    if stop_at == "judge1":
        return

    emails = pipeline.run_eval_queries(customers, tickets, conversations)
    _log(t0, f"eval_queries: {len(emails)}/{len(manifest['eval_queries'])} passed QA")
    if stop_at == "eval_queries":
        return

    labels = pipeline.run_labels(customers, tickets, emails)
    _log(t0, f"labels: {len(labels)}/{len(emails)} passed QA")
    if stop_at == "labels":
        return

    pipeline.run_judge2(tickets, emails, labels)
    _log(t0, "judge2: distractor realism pass complete")
    if stop_at == "judge2":
        return

    from generation.ingest import ingest

    label_dumps = {k: v.model_dump(mode="json") for k, v in labels.items()}
    id_map = ingest(pipeline.state, customers, tickets, conversations, emails, label_dumps, manifest)
    _log(t0, f"ingest: {len(id_map)} rows mapped to real Postgres IDs -- done")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m generation.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run the generation pipeline")
    run_parser.add_argument("--config", required=True, help="Path to generation_config.yaml")
    run_parser.add_argument(
        "--stage", choices=STAGE_ORDER, default="ingest",
        help="Run through this stage and stop (default: run everything, including ingest)",
    )
    run_parser.add_argument("--seed", type=int, default=0, help="Sampling seed for the manifest")
    run_parser.add_argument(
        "--model", default=None, help="Override the config file's run.model (Ollama model tag)"
    )
    run_parser.add_argument(
        "--host", default=None, help="Override the config file's run.host (local Ollama server URL)"
    )

    args = parser.parse_args(argv)

    if args.command == "run":
        config = GenerationConfig.from_yaml(args.config)
        if args.model:
            config.run.model = args.model
        if args.host:
            config.run.host = args.host

        pipeline = Pipeline(config)
        try:
            _run_through(pipeline, args.stage, args.seed)
        finally:
            pipeline.close()


if __name__ == "__main__":
    main()
