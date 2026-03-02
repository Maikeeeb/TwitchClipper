"""SQLite connection and schema initialization helpers."""

from __future__ import annotations

import sqlite3


def connect(db_path: str) -> sqlite3.Connection:
    """
    Open a SQLite connection with row access and FK constraints enabled.

    Raises ValueError for an empty path. sqlite3 errors propagate for
    invalid/unwritable paths.
    """
    if not isinstance(db_path, str) or not db_path.strip():
        raise ValueError("db_path must be a non-empty string")

    # FastAPI handlers may run in worker threads, so allow cross-thread usage.
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_schema(conn: sqlite3.Connection) -> None:
    """Create required persistence tables if they do not exist."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            status TEXT NOT NULL,
            progress REAL NOT NULL DEFAULT 0.0,
            created_at TEXT NOT NULL,
            started_at TEXT,
            finished_at TEXT,
            error TEXT,
            params_json TEXT NOT NULL,
            result_json TEXT
        );

        CREATE TABLE IF NOT EXISTS outputs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT NOT NULL,
            kind TEXT NOT NULL,
            path TEXT NOT NULL,
            metadata_json TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE,
            UNIQUE(job_id, kind, path)
        );

        CREATE INDEX IF NOT EXISTS idx_outputs_job_id ON outputs(job_id);
        """
    )
    conn.commit()


def connect_and_initialize(db_path: str) -> sqlite3.Connection:
    """Open SQLite DB and ensure schema exists."""
    conn = connect(db_path)
    initialize_schema(conn)
    return conn
