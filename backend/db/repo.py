"""Repository layer for SQLite job and output persistence."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Iterable

from backend.db.models import OutputRecord
from backend.db.sqlite import connect_and_initialize
from backend.jobs import Job, JobStatus

_VALID_STATUSES = {status.value for status in JobStatus}
_MAX_ERROR_LEN = 2048
_ERR_EMPTY_JOB_ID = "job_id must be a non-empty string"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dt_to_iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _iso_to_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


def _normalize_error(error: str | None) -> str | None:
    if error is None:
        return None
    if len(error) <= _MAX_ERROR_LEN:
        return error
    return error[:_MAX_ERROR_LEN]


def _require_path_string(path_value: Any, *, field_name: str) -> str:
    if not isinstance(path_value, str):
        raise ValueError(f"{field_name} must be a string path")
    return path_value


class SQLiteJobRepository:
    """Small repository interface to keep SQL isolated from API/worker modules."""

    def __init__(self, db_path: str) -> None:
        self._conn = connect_and_initialize(db_path)

    @property
    def connection(self) -> sqlite3.Connection:
        return self._conn

    def close(self) -> None:
        self._conn.close()

    def initialize_schema(self) -> None:
        from backend.db.sqlite import initialize_schema

        initialize_schema(self._conn)

    def create_job(self, job: Job) -> None:
        if not job.id or not job.id.strip():
            raise ValueError(_ERR_EMPTY_JOB_ID)

        self._conn.execute(
            """
            INSERT INTO jobs (
                id, type, status, progress, created_at, started_at, finished_at, error, params_json, result_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                type=excluded.type,
                status=excluded.status,
                progress=excluded.progress,
                created_at=excluded.created_at,
                started_at=excluded.started_at,
                finished_at=excluded.finished_at,
                error=excluded.error,
                params_json=excluded.params_json,
                result_json=excluded.result_json
            """,
            (
                job.id,
                job.type,
                job.status.value,
                float(job.progress),
                _dt_to_iso(job.created_at) or _utc_now_iso(),
                _dt_to_iso(job.started_at),
                _dt_to_iso(job.finished_at),
                job.error,
                json.dumps(job.params or {}, sort_keys=True),
                json.dumps(job.result, sort_keys=True) if job.result is not None else None,
            ),
        )
        self._conn.commit()

    def update_job_status(
        self,
        job_id: str,
        status: str,
        *,
        progress: float | None = None,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
        error: str | None = None,
        result: dict[str, Any] | None = None,
    ) -> bool:
        if not isinstance(job_id, str) or not job_id.strip():
            raise ValueError(_ERR_EMPTY_JOB_ID)
        if status not in _VALID_STATUSES:
            raise ValueError(f"invalid status: {status}")

        cur = self._conn.execute(
            """
            UPDATE jobs
            SET
                status = ?,
                progress = COALESCE(?, progress),
                started_at = COALESCE(?, started_at),
                finished_at = COALESCE(?, finished_at),
                error = ?,
                result_json = ?
            WHERE id = ?
            """,
            (
                status,
                progress,
                _dt_to_iso(started_at),
                _dt_to_iso(finished_at),
                _normalize_error(error),
                json.dumps(result, sort_keys=True) if result is not None else None,
                job_id,
            ),
        )
        self._conn.commit()
        return cur.rowcount > 0

    def get_job(self, job_id: str) -> Job | None:
        if not isinstance(job_id, str) or not job_id.strip():
            raise ValueError(_ERR_EMPTY_JOB_ID)

        row = self._conn.execute(
            """
            SELECT id, type, status, progress, created_at, started_at, finished_at, error, params_json, result_json
            FROM jobs
            WHERE id = ?
            """,
            (job_id,),
        ).fetchone()
        if row is None:
            return None

        return Job(
            id=row["id"],
            type=row["type"],
            status=JobStatus(row["status"]),
            progress=float(row["progress"]),
            created_at=_iso_to_dt(row["created_at"]) or datetime.now(timezone.utc),
            started_at=_iso_to_dt(row["started_at"]),
            finished_at=_iso_to_dt(row["finished_at"]),
            error=row["error"],
            params=json.loads(row["params_json"] or "{}"),
            result=json.loads(row["result_json"]) if row["result_json"] else None,
        )

    def save_outputs(self, job_id: str, outputs: Iterable[OutputRecord]) -> int:
        if not isinstance(job_id, str) or not job_id.strip():
            raise ValueError(_ERR_EMPTY_JOB_ID)

        inserted = 0
        for output in outputs:
            if not output.path.strip():
                raise ValueError("output path must be non-empty")
            if not output.kind.strip():
                raise ValueError("output kind must be non-empty")

            cur = self._conn.execute(
                """
                INSERT OR IGNORE INTO outputs (job_id, kind, path, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    output.kind,
                    output.path,
                    json.dumps(output.metadata or {}, sort_keys=True),
                    _dt_to_iso(output.created_at) or _utc_now_iso(),
                ),
            )
            inserted += int(cur.rowcount > 0)

        self._conn.commit()
        return inserted

    def save_job_outputs(self, job_id: str, outputs: dict[str, Any]) -> bool:
        """
        Persist output paths from a job.result-like dict.

        Returns False when job_id does not exist. Raises ValueError when any
        provided path value is not a string.
        """
        if not isinstance(job_id, str) or not job_id.strip():
            raise ValueError(_ERR_EMPTY_JOB_ID)
        if not isinstance(outputs, dict):
            raise ValueError("outputs must be a dict")

        exists_row = self._conn.execute(
            "SELECT 1 FROM jobs WHERE id = ?",
            (job_id,),
        ).fetchone()
        if exists_row is None:
            return False

        output_rows: list[OutputRecord] = []
        for key, value in outputs.items():
            if key == "paths":
                if value is None:
                    continue
                if not isinstance(value, list):
                    raise ValueError("paths must be a list of string paths")
                for index, item in enumerate(value):
                    output_rows.append(
                        OutputRecord(
                            job_id=job_id,
                            kind="path",
                            path=_require_path_string(item, field_name=f"paths[{index}]"),
                        )
                    )
                continue

            if key.endswith("_path") or key.endswith("_dir"):
                if value is None:
                    continue
                output_rows.append(
                    OutputRecord(
                        job_id=job_id,
                        kind=key,
                        path=_require_path_string(value, field_name=key),
                    )
                )

        # Replace previous outputs for this job with the latest final outputs.
        self._conn.execute("DELETE FROM outputs WHERE job_id = ?", (job_id,))
        self.save_outputs(job_id, output_rows)
        return True

    def get_job_outputs(self, job_id: str) -> dict[str, Any] | None:
        """
        Return persisted output paths shaped like job.result path fields.

        Returns:
        - None if job does not exist
        - {} if job exists but has no persisted outputs
        """
        if not isinstance(job_id, str) or not job_id.strip():
            raise ValueError(_ERR_EMPTY_JOB_ID)

        exists_row = self._conn.execute(
            "SELECT 1 FROM jobs WHERE id = ?",
            (job_id,),
        ).fetchone()
        if exists_row is None:
            return None

        rows = self.list_outputs(job_id)
        if not rows:
            return {}

        out: dict[str, Any] = {}
        list_paths: list[str] = []
        for row in rows:
            if row.kind == "path":
                list_paths.append(row.path)
            else:
                out[row.kind] = row.path

        if list_paths:
            out["paths"] = list_paths
        return out

    def list_outputs(self, job_id: str) -> list[OutputRecord]:
        if not isinstance(job_id, str) or not job_id.strip():
            raise ValueError(_ERR_EMPTY_JOB_ID)

        rows = self._conn.execute(
            """
            SELECT job_id, kind, path, metadata_json, created_at
            FROM outputs
            WHERE job_id = ?
            ORDER BY id ASC
            """,
            (job_id,),
        ).fetchall()
        return [
            OutputRecord(
                job_id=row["job_id"],
                kind=row["kind"],
                path=row["path"],
                metadata=json.loads(row["metadata_json"] or "{}"),
                created_at=_iso_to_dt(row["created_at"]),
            )
            for row in rows
        ]
