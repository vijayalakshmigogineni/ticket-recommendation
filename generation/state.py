"""SQLite-backed state store -- the resume/retry backbone.

One row per generation unit (a customer, a customer's ticket batch, a ticket's
conversation, an eval query, a label, a Judge 1 call, a Judge 2 call). unit_id
doubles as the Batches API custom_id. See docs/... Phase 6 plan: resume means
re-polling an in-flight batch_id rather than resubmitting; retry-only-failed
means requeueing exactly the units whose status is `errored`/`qa_fail` under
the retry cap.
"""

from __future__ import annotations

import datetime
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

PENDING = "pending"
SUBMITTED = "submitted"
SUCCEEDED = "succeeded"
ERRORED = "errored"
QA_PASS = "qa_pass"
QA_FLAG = "qa_flag"
QA_FAIL = "qa_fail"
INGESTED = "ingested"

RETRYABLE_STATUSES = (ERRORED, QA_FAIL)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS generation_units (
    unit_id TEXT PRIMARY KEY,
    stage TEXT NOT NULL,
    status TEXT NOT NULL,
    batch_id TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    raw_result TEXT,
    qa_verdict TEXT,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_generation_units_stage_status
    ON generation_units (stage, status);
CREATE INDEX IF NOT EXISTS ix_generation_units_batch_id
    ON generation_units (batch_id);
"""


@dataclass
class UnitRecord:
    unit_id: str
    stage: str
    status: str
    batch_id: str | None
    retry_count: int
    raw_result: dict | list | None
    qa_verdict: dict | None
    updated_at: str

    @classmethod
    def _from_row(cls, row: sqlite3.Row) -> "UnitRecord":
        return cls(
            unit_id=row["unit_id"],
            stage=row["stage"],
            status=row["status"],
            batch_id=row["batch_id"],
            retry_count=row["retry_count"],
            raw_result=json.loads(row["raw_result"]) if row["raw_result"] else None,
            qa_verdict=json.loads(row["qa_verdict"]) if row["qa_verdict"] else None,
            updated_at=row["updated_at"],
        )


class StateStore:
    def __init__(self, db_path: str | Path):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "StateStore":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    def _now(self) -> str:
        return datetime.datetime.utcnow().isoformat()

    def register_pending(self, unit_id: str, stage: str) -> None:
        """Adds a unit as `pending` if it doesn't already exist. Idempotent --
        safe to call every run so a resumed run doesn't reset already-progressed
        units back to pending."""
        self._conn.execute(
            "INSERT OR IGNORE INTO generation_units "
            "(unit_id, stage, status, retry_count, updated_at) VALUES (?, ?, ?, 0, ?)",
            (unit_id, stage, PENDING, self._now()),
        )
        self._conn.commit()

    def mark_submitted(self, unit_id: str, batch_id: str | None) -> None:
        self._conn.execute(
            "UPDATE generation_units SET status = ?, batch_id = ?, updated_at = ? "
            "WHERE unit_id = ?",
            (SUBMITTED, batch_id, self._now(), unit_id),
        )
        self._conn.commit()

    def mark_succeeded(self, unit_id: str, raw_result: dict | list) -> None:
        self._conn.execute(
            "UPDATE generation_units SET status = ?, raw_result = ?, updated_at = ? "
            "WHERE unit_id = ?",
            (SUCCEEDED, json.dumps(raw_result), self._now(), unit_id),
        )
        self._conn.commit()

    def mark_errored(self, unit_id: str) -> None:
        self._conn.execute(
            "UPDATE generation_units SET status = ?, retry_count = retry_count + 1, "
            "updated_at = ? WHERE unit_id = ?",
            (ERRORED, self._now(), unit_id),
        )
        self._conn.commit()

    def mark_qa_verdict(self, unit_id: str, verdict: str, qa_verdict: dict) -> None:
        """verdict is one of QA_PASS / QA_FLAG / QA_FAIL."""
        status = verdict
        increment = "retry_count = retry_count + 1, " if verdict == QA_FAIL else ""
        self._conn.execute(
            f"UPDATE generation_units SET status = ?, {increment}qa_verdict = ?, "
            "updated_at = ? WHERE unit_id = ?",
            (status, json.dumps(qa_verdict), self._now(), unit_id),
        )
        self._conn.commit()

    def mark_ingested(self, unit_id: str) -> None:
        self._conn.execute(
            "UPDATE generation_units SET status = ?, updated_at = ? WHERE unit_id = ?",
            (INGESTED, self._now(), unit_id),
        )
        self._conn.commit()

    def requeue_pending(self, unit_id: str) -> None:
        """Moves a retryable unit back to `pending` so it joins the next batch."""
        self._conn.execute(
            "UPDATE generation_units SET status = ?, batch_id = NULL, updated_at = ? "
            "WHERE unit_id = ?",
            (PENDING, self._now(), unit_id),
        )
        self._conn.commit()

    def get(self, unit_id: str) -> UnitRecord | None:
        row = self._conn.execute(
            "SELECT * FROM generation_units WHERE unit_id = ?", (unit_id,)
        ).fetchone()
        return UnitRecord._from_row(row) if row else None

    def list_by_stage_status(self, stage: str, status: str) -> list[UnitRecord]:
        rows = self._conn.execute(
            "SELECT * FROM generation_units WHERE stage = ? AND status = ? "
            "ORDER BY unit_id",
            (stage, status),
        ).fetchall()
        return [UnitRecord._from_row(r) for r in rows]

    def pending_units(self, stage: str) -> list[UnitRecord]:
        return self.list_by_stage_status(stage, PENDING)

    def submitted_units(self, stage: str | None = None) -> list[UnitRecord]:
        if stage is None:
            rows = self._conn.execute(
                "SELECT * FROM generation_units WHERE status = ? ORDER BY unit_id",
                (SUBMITTED,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM generation_units WHERE stage = ? AND status = ? "
                "ORDER BY unit_id",
                (stage, SUBMITTED),
            ).fetchall()
        return [UnitRecord._from_row(r) for r in rows]

    def retryable_units(self, stage: str, max_attempts: int) -> list[UnitRecord]:
        rows = self._conn.execute(
            "SELECT * FROM generation_units WHERE stage = ? "
            "AND status IN (?, ?) AND retry_count < ? ORDER BY unit_id",
            (stage, ERRORED, QA_FAIL, max_attempts),
        ).fetchall()
        return [UnitRecord._from_row(r) for r in rows]

    def permanently_failed_units(self, stage: str, max_attempts: int) -> list[UnitRecord]:
        rows = self._conn.execute(
            "SELECT * FROM generation_units WHERE stage = ? "
            "AND status IN (?, ?) AND retry_count >= ? ORDER BY unit_id",
            (stage, ERRORED, QA_FAIL, max_attempts),
        ).fetchall()
        return [UnitRecord._from_row(r) for r in rows]

    def qa_passed_units(self, stage: str) -> list[UnitRecord]:
        return self.list_by_stage_status(stage, QA_PASS) + self.list_by_stage_status(
            stage, QA_FLAG
        )

    def stage_complete(self, stage: str) -> bool:
        """True once every unit in the stage has reached a terminal state
        (qa_pass/qa_flag/ingested) or exhausted its retries (checked by the
        caller, since the cap is config-driven, not stored here)."""
        row = self._conn.execute(
            "SELECT COUNT(*) as n FROM generation_units WHERE stage = ? "
            "AND status NOT IN (?, ?, ?)",
            (stage, QA_PASS, QA_FLAG, INGESTED),
        ).fetchone()
        return row["n"] == 0
