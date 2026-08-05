"""Top-level orchestrator. Builds the manifest (generation.sampling), then runs
each stage (customers -> tickets -> conversations -> [judge1 QA] ->
eval_queries -> labels -> [judge2 QA]) as a generate -> QA -> (requeue
failures) cycle, using generation.state.StateStore as the resume/retry
backbone and generation.qa.gate for verdicts. LLM calls go through
generation.llm_client.OllamaClient (a local server, no batch API) -- fan-out
across units within a stage uses a local thread pool for concurrency instead
of a cloud batch job.
"""

from __future__ import annotations

import json
import random
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable

from pydantic import BaseModel

from app.enums import TERMINAL_TICKET_STATUSES
from generation.llm_client import GenerationError, OllamaClient
from generation.config import GenerationConfig
from generation.prompts import (
    judge1_ticket_consistency,
    judge2_distractor_realism,
    template1_customers,
    template2_tickets,
    template3_conversations,
    template4_eval_queries,
    template5_labels,
)
from generation.qa import gate
from generation.sampling import build_manifest
from generation.schemas import Judge1Output, LabelOutput
from generation.state import ERRORED, INGESTED, QA_FAIL, QA_FLAG, QA_PASS, StateStore

# gate.py's Verdict.status vocabulary ("pass"/"flag"/"fail" -- shared with
# Finding severities and judge verdict strings) is distinct from state.py's
# stored status vocabulary ("qa_pass"/"qa_flag"/"qa_fail") -- this is the one
# translation point between them.
_GATE_TO_STATE = {gate.PASS: QA_PASS, gate.FLAG: QA_FLAG, gate.FAIL: QA_FAIL}


class Pipeline:
    def __init__(self, config: GenerationConfig):
        self.config = config
        self.output_dir = Path(config.paths.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.state = StateStore(config.paths.state_db)
        self.client = OllamaClient(model=config.run.model, host=config.run.host)

    def close(self) -> None:
        self.state.close()

    # --- manifest -------------------------------------------------------------

    def build_manifest(self, seed: int = 0) -> dict:
        manifest_path = self.output_dir / "manifest.json"
        if manifest_path.exists():
            return json.loads(manifest_path.read_text(encoding="utf-8"))

        manifest = build_manifest(self.config.scale, self.config.distributions, seed=seed)
        serializable = {
            "customers": manifest["customers"],
            "tickets": [vars(t) for t in manifest["tickets"]],
            "eval_queries": [vars(q) for q in manifest["eval_queries"]],
        }
        manifest_path.write_text(json.dumps(serializable, indent=2), encoding="utf-8")

        self.state.register_pending("__manifest__", "manifest")
        self.state.mark_succeeded("__manifest__", serializable)
        self.state.mark_qa_verdict("__manifest__", QA_PASS, {"note": "manifest is orchestrator-generated, not QA'd"})
        return serializable

    # --- generic stage runner --------------------------------------------------

    def _submit_and_collect(
        self, stage: str, requests: dict[str, dict]
    ) -> dict[str, BaseModel | GenerationError]:
        """Registers every unit_id in `requests` as pending (idempotent), then
        calls the local Ollama server for everything still pending/retryable
        -- concurrently, bounded by config.run.max_concurrent_requests, since
        there's no cloud batch job to submit-and-poll -- and returns
        {unit_id: parsed_result_or_error} for units that completed this call.
        Units already qa_pass/qa_flag/ingested are skipped entirely."""
        for unit_id in requests:
            self.state.register_pending(unit_id, stage)

        to_run = [
            r.unit_id
            for r in (
                self.state.pending_units(stage)
                + self.state.retryable_units(stage, self.config.run.max_regeneration_attempts)
            )
            if r.unit_id in requests
        ]
        if not to_run:
            return {}

        def _call(unit_id: str) -> tuple[str, BaseModel | GenerationError]:
            try:
                return unit_id, self.client.call_sync(requests[unit_id])
            except GenerationError as exc:
                return unit_id, exc

        results: dict[str, BaseModel | GenerationError] = {}
        max_workers = max(1, self.config.run.max_concurrent_requests)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for unit_id, result in executor.map(_call, to_run):
                self._store_generation_result(unit_id, result)
                results[unit_id] = result

        return results

    def _store_generation_result(self, unit_id: str, result: BaseModel | GenerationError) -> None:
        if isinstance(result, GenerationError):
            self.state.mark_errored(unit_id)
        else:
            self.state.mark_succeeded(unit_id, result.model_dump(mode="json"))

    def _apply_qa(self, unit_id: str, verdict: gate.Verdict) -> None:
        self.state.mark_qa_verdict(
            unit_id, _GATE_TO_STATE[verdict.status], {"findings": [vars(f) for f in verdict.findings]}
        )
        if verdict.status == gate.FAIL:
            self.state.requeue_pending(unit_id)

    def _run_batched_stage(
        self,
        stage: str,
        item_ids_by_group: dict[str, list[str]],
        build_request: Callable[[str, list[str], dict[str, object]], dict],
        extract_items: Callable[[BaseModel], list[tuple[str, object]]],
        qa_check: Callable[[str, object, dict[str, object]], gate.Verdict],
    ) -> dict[str, object]:
        """Shared retry loop for Templates 2/3/4, whose generation unit (one call
        per customer, producing many items) is coarser than their QA unit (one
        verdict per item). A QA-FAIL on a single item must not force
        regenerating its whole customer batch -- each round only re-requests
        the items still outstanding for that customer, narrowing over
        max_regeneration_attempts rounds. Call-level bookkeeping lives under
        f"{stage}__gen" (pending/errored), separate from per-item QA state
        under `stage` itself -- these are genuinely different unit
        granularities and conflating them silently drops per-item retries.
        """
        max_attempts = self.config.run.max_regeneration_attempts
        results: dict[str, object] = {}

        for attempt in range(max_attempts + 1):
            pending_by_group: dict[str, list[str]] = {}
            for group_key, item_ids in item_ids_by_group.items():
                still_needed = []
                for item_id in item_ids:
                    record = self.state.get(item_id)
                    if record is None:
                        still_needed.append(item_id)
                    elif record.status in (QA_PASS, QA_FLAG, INGESTED):
                        results[item_id] = record.raw_result
                    elif record.status in (ERRORED, QA_FAIL) and record.retry_count <= max_attempts:
                        still_needed.append(item_id)
                    # else: permanently failed (retry_count > max_attempts) -- left
                    # in qa_fail/errored for manual review, not retried further.
                if still_needed:
                    pending_by_group[group_key] = still_needed

            if not pending_by_group:
                break

            requests: dict[str, dict] = {}
            for group_key, item_ids in pending_by_group.items():
                batch_key = f"{stage}_{group_key}_{attempt}"
                requests[batch_key] = build_request(group_key, item_ids, results)

            raw = self._submit_and_collect(f"{stage}__gen", requests)

            for _batch_key, result in raw.items():
                if isinstance(result, GenerationError):
                    continue
                for item_id, item_value in extract_items(result):
                    self.state.register_pending(item_id, stage)
                    self.state.mark_succeeded(item_id, item_value)
                    verdict = qa_check(item_id, item_value, results)
                    self._apply_qa(item_id, verdict)
                    if verdict.status != gate.FAIL:
                        results[item_id] = item_value

        return results

    # --- stage 1: customers -----------------------------------------------------

    def run_customers(self) -> dict[str, dict]:
        manifest = self.build_manifest()
        customer_ids = manifest["customers"]
        # One request per customer (n=1) rather than one big N-customer batch call,
        # so a QA-FAIL regeneration only re-runs the failed customer.
        requests = {cid: template1_customers.build_request(n=1) for cid in customer_ids}
        raw_results = self._submit_and_collect("customers", requests)

        customers: dict[str, dict] = {}
        batch_inbox_emails: list[str] = []
        for cid, result in raw_results.items():
            if isinstance(result, GenerationError):
                continue
            item = result.customers[0].model_dump(mode="json")
            item["temp_id"] = cid
            customers[cid] = item
            # _submit_and_collect stored the whole CustomerBatchOutput wrapper
            # (n=1, but still schema-wrapped) as raw_result; overwrite with the
            # unwrapped item so a resumed run reads back the same shape a fresh
            # run produces here.
            self.state.mark_succeeded(cid, item)
            batch_inbox_emails.append(item["production_fields"]["inbox_email"])

        for cid, item in customers.items():
            verdict = gate.gate_customer(item, batch_inbox_emails, avoid_names=[])
            self._apply_qa(cid, verdict)

        return {
            r.unit_id: r.raw_result
            for r in self.state.qa_passed_units("customers")
        }

    # --- stage 2: tickets ---------------------------------------------------

    def run_tickets(self, customers: dict[str, dict]) -> dict[str, dict]:
        manifest = self.build_manifest()
        assignments_by_id = {a["temp_id"]: a for a in manifest["tickets"]}
        assignments_by_customer: dict[str, list[str]] = {}
        for a in manifest["tickets"]:
            if a["customer_temp_id"] in customers:
                assignments_by_customer.setdefault(a["customer_temp_id"], []).append(a["temp_id"])

        def build_request(cid: str, item_ids: list[str], generated: dict[str, dict]) -> dict:
            simple_assignments = [
                {"temp_id": tid, "category": assignments_by_id[tid]["category"], "status": assignments_by_id[tid]["status"]}
                for tid in item_ids
            ]
            sibling_seeds = [
                generated[assignments_by_id[tid]["disambiguation_sibling"]]
                for tid in item_ids
                if assignments_by_id[tid].get("disambiguation_sibling") in generated
            ]
            return template2_tickets.build_request(customers[cid], simple_assignments, sibling_seeds or None)

        def extract_items(result) -> list[tuple[str, dict]]:
            return [(item.temp_id, item.model_dump(mode="json")) for item in result.tickets]

        def qa_check(temp_id: str, item: dict, generated: dict[str, dict]) -> gate.Verdict:
            assignment = assignments_by_id[temp_id]
            sibling_id = assignment.get("disambiguation_sibling")
            sibling_seeds = [generated[sibling_id]] if sibling_id and sibling_id in generated else None
            return gate.gate_ticket_seed(item, assignment, sibling_seeds)

        return self._run_batched_stage("tickets", assignments_by_customer, build_request, extract_items, qa_check)

    # --- stage 3: conversations -----------------------------------------------

    def run_conversations(self, customers: dict[str, dict], tickets: dict[str, dict]) -> dict[str, dict]:
        """Conversation units are tracked under a "conv_"-prefixed unit_id, not
        the bare ticket temp_id -- state.py's table is keyed by unit_id alone
        (no stage column in the key), so reusing "tkt_1_1" here would silently
        collide with the ticket's own already-qa_pass row from the tickets
        stage and short-circuit conversation generation entirely."""
        manifest = self.build_manifest()
        assignments_by_id = {a["temp_id"]: a for a in manifest["tickets"]}
        by_customer: dict[str, list[str]] = {}
        conv_id_to_ticket: dict[str, str] = {}
        for temp_id in tickets:
            cid = assignments_by_id[temp_id]["customer_temp_id"]
            conv_id = f"conv_{temp_id}"
            conv_id_to_ticket[conv_id] = temp_id
            by_customer.setdefault(cid, []).append(conv_id)

        def build_request(cid: str, item_ids: list[str], _generated: dict[str, dict]) -> dict:
            ticket_ids = [conv_id_to_ticket[cid_] for cid_ in item_ids]
            seeds = [tickets[tid] for tid in ticket_ids]
            counts = {tid: assignments_by_id[tid]["message_count"] for tid in ticket_ids}
            return template3_conversations.build_request(customers[cid], seeds, counts)

        def extract_items(result) -> list[tuple[str, dict]]:
            return [(f"conv_{conv.ticket_temp_id}", conv.model_dump(mode="json")) for conv in result.conversations]

        def qa_check(conv_id: str, conv: dict, _generated: dict[str, dict]) -> gate.Verdict:
            return gate.gate_conversation(tickets[conv_id_to_ticket[conv_id]], conv)

        raw = self._run_batched_stage("conversations", by_customer, build_request, extract_items, qa_check)
        return {conv_id_to_ticket[conv_id]: conv for conv_id, conv in raw.items()}

    # --- judge 1: ticket & conversation consistency -----------------------------

    def run_judge1(self, tickets: dict[str, dict], conversations: dict[str, dict]) -> dict[str, Judge1Output]:
        manifest = self.build_manifest()
        assignments_by_id = {a["temp_id"]: a for a in manifest["tickets"]}

        requests: dict[str, dict] = {}
        for temp_id in set(tickets) & set(conversations):
            sibling_id = assignments_by_id[temp_id].get("disambiguation_sibling")
            sibling_seed = tickets.get(sibling_id) if sibling_id else None
            unit_id = f"judge1_{temp_id}"
            requests[unit_id] = judge1_ticket_consistency.build_request(
                tickets[temp_id], conversations[temp_id]["messages"], sibling_seed
            )

        raw_results = self._submit_and_collect("judge1", requests)
        judge1_outputs: dict[str, Judge1Output] = {}
        for unit_id, result in raw_results.items():
            if isinstance(result, GenerationError):
                continue
            self.state.mark_qa_verdict(unit_id, QA_PASS, {"note": "judge output stored, not itself QA'd"})
            judge1_outputs[unit_id.removeprefix("judge1_")] = result
        return judge1_outputs

    # --- stage 4: eval queries -------------------------------------------------

    def _brief_description(self, ticket: dict) -> str:
        meta = ticket.get("generation_metadata", {})
        return meta.get("core_issue_summary") or meta.get("distinguishing_details") or ""

    def run_eval_queries(
        self,
        customers: dict[str, dict],
        tickets: dict[str, dict],
        conversations: dict[str, dict],
    ) -> dict[str, str]:
        manifest = self.build_manifest()
        scenarios_by_id = {s["temp_id"]: s for s in manifest["eval_queries"]}
        by_customer: dict[str, list[str]] = {}
        for s in manifest["eval_queries"]:
            if s["customer_temp_id"] in customers:
                by_customer.setdefault(s["customer_temp_id"], []).append(s["temp_id"])

        def _scenario_payload(temp_id: str) -> dict:
            s = scenarios_by_id[temp_id]
            target = s.get("target_ticket")
            near_miss = s.get("near_miss_ticket")
            candidates = s.get("candidates") or []
            payload = dict(s)
            if target and target in tickets:
                payload["target_ticket_context"] = {
                    "seed": tickets[target],
                    "thread": conversations.get(target, {}).get("messages", []),
                }
            if near_miss and near_miss in tickets:
                payload["near_miss_ticket_context"] = {
                    "subject": tickets[near_miss]["production_fields"]["subject"],
                    "category": tickets[near_miss]["production_fields"]["category"],
                    "brief_description": self._brief_description(tickets[near_miss]),
                }
            if candidates:
                payload["candidate_tickets_context"] = [
                    {
                        "temp_id": c,
                        "subject": tickets[c]["production_fields"]["subject"],
                        "category": tickets[c]["production_fields"]["category"],
                        "brief_description": self._brief_description(tickets[c]),
                    }
                    for c in candidates
                    if c in tickets
                ]
            return payload

        def build_request(cid: str, item_ids: list[str], _generated: dict[str, str]) -> dict:
            enriched = [_scenario_payload(tid) for tid in item_ids]
            return template4_eval_queries.build_request(customers[cid], enriched)

        def extract_items(result) -> list[tuple[str, str]]:
            return [(item.scenario_temp_id, item.email_text) for item in result.eval_queries]

        def qa_check(temp_id: str, email_text: str, _generated: dict[str, str]) -> gate.Verdict:
            s = scenarios_by_id[temp_id]
            return gate.gate_eval_query(email_text, s["tone"], s["length_bucket"], s["noise_level"])

        return self._run_batched_stage("eval_queries", by_customer, build_request, extract_items, qa_check)

    # --- stage 5: labels (blind judge) + judge 2 --------------------------------

    def run_labels(
        self,
        customers: dict[str, dict],
        tickets: dict[str, dict],
        eval_query_emails: dict[str, str],
    ) -> dict[str, LabelOutput]:
        manifest = self.build_manifest()
        scenarios_by_id = {s["temp_id"]: s for s in manifest["eval_queries"]}
        assignments_by_id = {a["temp_id"]: a for a in manifest["tickets"]}

        requests: dict[str, dict] = {}
        label_metadata: dict[str, dict] = {}  # unit_id -> {"labels": {A: temp_id, ...}}
        rng = random.Random(0)

        for temp_id, email_text in eval_query_emails.items():
            s = scenarios_by_id[temp_id]
            cid = s["customer_temp_id"]
            open_ticket_ids = [
                a["temp_id"]
                for a in manifest["tickets"]
                if a["customer_temp_id"] == cid
                and a["status"] not in {st.value for st in TERMINAL_TICKET_STATUSES}
                and a["temp_id"] in tickets
            ]
            rng.shuffle(open_ticket_ids)
            labels = [chr(ord("A") + i) for i in range(len(open_ticket_ids))]
            label_map = dict(zip(labels, open_ticket_ids))
            candidates = [
                {
                    "label": label,
                    "subject": tickets[tid]["production_fields"]["subject"],
                    "category": tickets[tid]["production_fields"]["category"],
                    "brief_description": self._brief_description(tickets[tid]),
                }
                for label, tid in label_map.items()
            ]

            unit_id = f"label_{temp_id}"
            requests[unit_id] = template5_labels.build_request(email_text, candidates)
            label_metadata[unit_id] = {"label_map": label_map, "scenario": s}

        raw_results = self._submit_and_collect("labels", requests)

        labels: dict[str, LabelOutput] = {}
        for unit_id, result in raw_results.items():
            if isinstance(result, GenerationError):
                continue
            meta = label_metadata[unit_id]
            label_map = meta["label_map"]
            s = meta["scenario"]
            temp_id = unit_id.removeprefix("label_")

            judged_target = label_map.get(result.matched_label) if result.matched_label else None
            resolved = LabelOutput(
                matched_label=judged_target,
                should_match=result.should_match,
                difficulty_tier=result.difficulty_tier,
                distractor_labels=[
                    label_map[l] for l in result.distractor_labels if l in label_map
                ],
                reasoning=result.reasoning,
            )
            labels[temp_id] = resolved

            intended_target = s.get("target_ticket")
            verdict = gate.gate_label(intended_target, s["tier"], resolved)
            self._apply_qa(unit_id, verdict)

        return labels

    def run_judge2(
        self,
        tickets: dict[str, dict],
        eval_query_emails: dict[str, str],
        labels: dict[str, LabelOutput],
    ) -> None:
        """Runs only on distractors that pass the rule pre-filter (§5 of
        generation_qa_checklist.md) -- self-distraction / cross-customer
        pairs never reach the LLM judge. Findings are recorded against the
        label unit but don't reopen its ground-truth-match verdict, which is
        judged solely by gate_label -- distractor realism is a separate,
        softer QA concern (a FLAG, not a hard gate)."""
        manifest = self.build_manifest()
        assignments_by_id = {a["temp_id"]: a for a in manifest["tickets"]}

        requests: dict[str, dict] = {}
        pair_metadata: dict[str, tuple[str, str, str]] = {}  # unit_id -> (temp_id, correct, distractor)

        for temp_id, label in labels.items():
            if not label.matched_label or not label.distractor_labels:
                continue
            correct_id = label.matched_label
            correct_customer = assignments_by_id.get(correct_id, {}).get("customer_temp_id")
            for distractor_id in label.distractor_labels:
                same_customer = (
                    assignments_by_id.get(distractor_id, {}).get("customer_temp_id") == correct_customer
                )
                prefilter = gate.check_distractor_prefilter(correct_id, distractor_id, same_customer)
                unit_id = f"judge2_{temp_id}_{distractor_id}"
                if prefilter:
                    self.state.register_pending(unit_id, "judge2")
                    self.state.mark_qa_verdict(unit_id, QA_FAIL, {"findings": [vars(f) for f in prefilter]})
                    continue
                if correct_id not in tickets or distractor_id not in tickets:
                    continue
                req = judge2_distractor_realism.build_request(
                    eval_query_emails[temp_id],
                    {
                        "subject": tickets[correct_id]["production_fields"]["subject"],
                        "category": tickets[correct_id]["production_fields"]["category"],
                        "brief_description": self._brief_description(tickets[correct_id]),
                    },
                    {
                        "subject": tickets[distractor_id]["production_fields"]["subject"],
                        "category": tickets[distractor_id]["production_fields"]["category"],
                        "brief_description": self._brief_description(tickets[distractor_id]),
                    },
                )
                requests[unit_id] = req
                pair_metadata[unit_id] = (temp_id, correct_id, distractor_id)

        raw_results = self._submit_and_collect("judge2", requests)
        for unit_id, result in raw_results.items():
            if isinstance(result, GenerationError):
                continue
            _, correct_id, distractor_id = pair_metadata[unit_id]
            verdict = gate.gate_distractor(correct_id, distractor_id, same_customer=True, judge2=result)
            self._apply_qa(unit_id, verdict)

    # --- full run ---------------------------------------------------------------

    def run_all(self, seed: int = 0, do_ingest: bool = True) -> dict[str, dict]:
        manifest = self.build_manifest(seed=seed)
        customers = self.run_customers()
        tickets = self.run_tickets(customers)
        conversations = self.run_conversations(customers, tickets)
        self.run_judge1(tickets, conversations)
        emails = self.run_eval_queries(customers, tickets, conversations)
        labels = self.run_labels(customers, tickets, emails)
        self.run_judge2(tickets, emails, labels)

        label_dumps = {k: v.model_dump(mode="json") for k, v in labels.items()}
        if do_ingest:
            from generation.ingest import ingest

            ingest(self.state, customers, tickets, conversations, emails, label_dumps, manifest)

        return {
            "customers": customers,
            "tickets": tickets,
            "conversations": conversations,
            "eval_query_emails": emails,
            "labels": label_dumps,
        }
