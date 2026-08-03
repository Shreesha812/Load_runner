"""SQLite database initialisation and connection management."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

import aiosqlite

# DB lives in backend/db/ — path is absolute so it works regardless of cwd
DB_PATH = os.path.join(os.path.dirname(__file__), "wolken_loadrunner.db")

CREATE_RUNS = """
CREATE TABLE IF NOT EXISTS runs (
    run_id      TEXT PRIMARY KEY,
    filename    TEXT NOT NULL,
    status      TEXT NOT NULL,
    started_at  TEXT NOT NULL,
    finished_at TEXT,
    error       TEXT
);
"""

CREATE_TEST_RESULTS = """
CREATE TABLE IF NOT EXISTS test_results (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id              TEXT    NOT NULL REFERENCES runs(run_id),
    test_name           TEXT    NOT NULL,
    total_requests      INTEGER DEFAULT 0,
    successful_requests INTEGER DEFAULT 0,
    failed_requests     INTEGER DEFAULT 0,
    avg_latency_ms      REAL    DEFAULT 0,
    min_latency_ms      REAL    DEFAULT 0,
    max_latency_ms      REAL    DEFAULT 0,
    p50_latency_ms      REAL    DEFAULT 0,
    p95_latency_ms      REAL    DEFAULT 0,
    p99_latency_ms      REAL    DEFAULT 0,
    requests_per_second REAL    DEFAULT 0,
    execution_time_s    REAL    DEFAULT 0,
    overall_status      TEXT    DEFAULT 'no_requests'
);
"""

CREATE_REQUEST_ENTRIES = """
CREATE TABLE IF NOT EXISTS request_entries (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    test_result_id INTEGER NOT NULL REFERENCES test_results(id),
    request_id     TEXT    NOT NULL,
    entry_type     TEXT    NOT NULL,
    status_code    INTEGER,
    latency_ms     REAL    NOT NULL,
    combination    TEXT    NOT NULL,
    error_type     TEXT    NOT NULL DEFAULT ''
);
"""

CREATE_TIMESERIES = """
CREATE TABLE IF NOT EXISTS timeseries (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id         TEXT    NOT NULL REFERENCES runs(run_id),
    test_name      TEXT    NOT NULL,
    ts             INTEGER NOT NULL,
    rps            REAL    DEFAULT 0,
    avg_latency_ms REAL    DEFAULT 0,
    total_requests INTEGER DEFAULT 0
);
"""

CREATE_TEST_OVERRIDES = """
CREATE TABLE IF NOT EXISTS test_overrides (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id    TEXT    NOT NULL REFERENCES runs(run_id),
    test_idx  INTEGER NOT NULL,
    enabled   INTEGER NOT NULL DEFAULT 1,
    UNIQUE(run_id, test_idx)
);
"""

CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_test_results_run_id ON test_results(run_id);",
    "CREATE INDEX IF NOT EXISTS idx_request_entries_test_result_id ON request_entries(test_result_id);",
    "CREATE INDEX IF NOT EXISTS idx_timeseries_run_id ON timeseries(run_id);",
]


async def init_db() -> None:
    """Create all tables and indexes. Safe to call on every startup."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA foreign_keys=ON;")
        await db.execute(CREATE_RUNS)
        await db.execute(CREATE_TEST_RESULTS)
        await db.execute(CREATE_REQUEST_ENTRIES)
        await db.execute(CREATE_TIMESERIES)
        await db.execute(CREATE_TEST_OVERRIDES)
        for stmt in CREATE_INDEXES:
            await db.execute(stmt)
        # Migration: add error_type column if it doesn't exist yet
        try:
            await db.execute("ALTER TABLE request_entries ADD COLUMN error_type TEXT NOT NULL DEFAULT ''")
        except Exception:
            pass  # column already exists — safe to ignore
        await db.commit()


@asynccontextmanager
async def get_db():
    """Async context manager yielding an open aiosqlite connection."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys=ON;")
        yield db
