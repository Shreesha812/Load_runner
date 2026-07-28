"""
SQLite-backed run store.
Persistent across restarts. Pub/sub stays in-memory (only needed for live runs).
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Optional

from backend.db.database import get_db
from backend.models import (
    MetricsSnapshot, RequestEntry, RunStatus, RunSummary, TestResult,
)


class SQLiteRunStore:

    def __init__(self) -> None:
        # In-memory pub/sub — live events only, not persisted
        self._subscribers: dict[str, set[asyncio.Queue]] = {}

    # ── CRUD ─────────────────────────────────────────────────────────────

    async def create(self, run: RunSummary) -> None:
        """Insert a new run row. Call once when the run is created."""
        async with get_db() as db:
            await db.execute(
                """INSERT INTO runs (run_id, filename, status, started_at, finished_at, error)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (run.run_id, run.filename, run.status.value,
                 run.started_at, run.finished_at, run.error),
            )
            await db.commit()
        self._subscribers.setdefault(run.run_id, set())

    async def get(self, run_id: str) -> Optional[RunSummary]:
        """Load a full RunSummary including test_results and request_entries."""
        async with get_db() as db:
            # Load run row
            async with db.execute(
                "SELECT * FROM runs WHERE run_id = ?", (run_id,)
            ) as cur:
                row = await cur.fetchone()
            if row is None:
                return None

            run = RunSummary(
                run_id=row["run_id"],
                filename=row["filename"],
                status=RunStatus(row["status"]),
                started_at=row["started_at"],
                finished_at=row["finished_at"],
                error=row["error"],
            )

            # Load test results
            async with db.execute(
                "SELECT * FROM test_results WHERE run_id = ? ORDER BY id", (run_id,)
            ) as cur:
                tr_rows = await cur.fetchall()

            for tr in tr_rows:
                tr_id = tr["id"]

                # Load request entries for this test result
                async with db.execute(
                    "SELECT * FROM request_entries WHERE test_result_id = ? ORDER BY id",
                    (tr_id,),
                ) as cur:
                    entry_rows = await cur.fetchall()

                success_list = []
                failure_list = []
                for e in entry_rows:
                    entry = RequestEntry(
                        id=e["request_id"],
                        status=e["status_code"],
                        latency_ms=e["latency_ms"],
                        combination=json.loads(e["combination"]),
                    )
                    if e["entry_type"] == "success":
                        success_list.append(entry)
                    else:
                        failure_list.append(entry)

                metrics = MetricsSnapshot(
                    total_requests=tr["total_requests"],
                    successful_requests=tr["successful_requests"],
                    failed_requests=tr["failed_requests"],
                    avg_latency_ms=tr["avg_latency_ms"],
                    min_latency_ms=tr["min_latency_ms"],
                    max_latency_ms=tr["max_latency_ms"],
                    p50_latency_ms=tr["p50_latency_ms"],
                    p95_latency_ms=tr["p95_latency_ms"],
                    p99_latency_ms=tr["p99_latency_ms"],
                    requests_per_second=tr["requests_per_second"],
                    execution_time_s=tr["execution_time_s"],
                    overall_status=tr["overall_status"],
                    success_list=success_list,
                    failure_list=failure_list,
                )
                run.results.append(TestResult(test_name=tr["test_name"], metrics=metrics))

        return run

    async def update(self, run: RunSummary) -> None:
        """Persist run status. If done, also write test_results + request_entries."""
        async with get_db() as db:
            await db.execute(
                """UPDATE runs SET status=?, finished_at=?, error=? WHERE run_id=?""",
                (run.status.value, run.finished_at, run.error, run.run_id),
            )

            if run.status == RunStatus.done and run.results:
                # Delete old test results for this run (idempotent re-save)
                async with db.execute(
                    "SELECT id FROM test_results WHERE run_id=?", (run.run_id,)
                ) as cur:
                    old_ids = [r["id"] for r in await cur.fetchall()]
                for old_id in old_ids:
                    await db.execute(
                        "DELETE FROM request_entries WHERE test_result_id=?", (old_id,)
                    )
                await db.execute(
                    "DELETE FROM test_results WHERE run_id=?", (run.run_id,)
                )

                for result in run.results:
                    m = result.metrics
                    await db.execute(
                        """INSERT INTO test_results
                           (run_id, test_name, total_requests, successful_requests, failed_requests,
                            avg_latency_ms, min_latency_ms, max_latency_ms,
                            p50_latency_ms, p95_latency_ms, p99_latency_ms,
                            requests_per_second, execution_time_s, overall_status)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (run.run_id, result.test_name,
                         m.total_requests, m.successful_requests, m.failed_requests,
                         m.avg_latency_ms, m.min_latency_ms, m.max_latency_ms,
                         m.p50_latency_ms, m.p95_latency_ms, m.p99_latency_ms,
                         m.requests_per_second, m.execution_time_s, m.overall_status),
                    )
                    async with db.execute("SELECT last_insert_rowid()") as cur:
                        tr_id = (await cur.fetchone())[0]

                    all_entries = (
                        [("success", e) for e in m.success_list] +
                        [("failure", e) for e in m.failure_list]
                    )
                    for entry_type, e in all_entries:
                        await db.execute(
                            """INSERT INTO request_entries
                               (test_result_id, request_id, entry_type, status_code, latency_ms, combination)
                               VALUES (?,?,?,?,?,?)""",
                            (tr_id, e.id, entry_type, e.status,
                             e.latency_ms, json.dumps(e.combination)),
                        )

            await db.commit()

    async def all(self) -> list[RunSummary]:
        """List all runs newest-first. Loads test_results summary but NOT request_entries."""
        async with get_db() as db:
            async with db.execute(
                "SELECT * FROM runs ORDER BY started_at DESC"
            ) as cur:
                run_rows = await cur.fetchall()

            results = []
            for row in run_rows:
                run = RunSummary(
                    run_id=row["run_id"],
                    filename=row["filename"],
                    status=RunStatus(row["status"]),
                    started_at=row["started_at"],
                    finished_at=row["finished_at"],
                    error=row["error"],
                )
                # Load summary metrics (no request_entries for perf)
                async with db.execute(
                    "SELECT * FROM test_results WHERE run_id=? ORDER BY id",
                    (row["run_id"],),
                ) as cur:
                    tr_rows = await cur.fetchall()
                for tr in tr_rows:
                    metrics = MetricsSnapshot(
                        total_requests=tr["total_requests"],
                        successful_requests=tr["successful_requests"],
                        failed_requests=tr["failed_requests"],
                        avg_latency_ms=tr["avg_latency_ms"],
                        min_latency_ms=tr["min_latency_ms"],
                        max_latency_ms=tr["max_latency_ms"],
                        p50_latency_ms=tr["p50_latency_ms"],
                        p95_latency_ms=tr["p95_latency_ms"],
                        p99_latency_ms=tr["p99_latency_ms"],
                        requests_per_second=tr["requests_per_second"],
                        execution_time_s=tr["execution_time_s"],
                        overall_status=tr["overall_status"],
                        # Omit success_list/failure_list in list view for performance
                    )
                    run.results.append(TestResult(test_name=tr["test_name"], metrics=metrics))
                results.append(run)

        return results

    # ── Timeseries (for Sprint 3 live chart persistence) ─────────────────

    async def record_timeseries(
        self,
        run_id: str,
        test_name: str,
        rps: float,
        avg_latency: float,
        total_requests: int,
    ) -> None:
        ts = int(time.time() * 1000)
        async with get_db() as db:
            await db.execute(
                """INSERT INTO timeseries (run_id, test_name, ts, rps, avg_latency_ms, total_requests)
                   VALUES (?,?,?,?,?,?)""",
                (run_id, test_name, ts, rps, avg_latency, total_requests),
            )
            await db.commit()

    # ── Pub/sub (in-memory, live runs only) ───────────────────────────────

    def subscribe(self, run_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=256)
        self._subscribers.setdefault(run_id, set()).add(q)
        return q

    def unsubscribe(self, run_id: str, q: asyncio.Queue) -> None:
        self._subscribers.get(run_id, set()).discard(q)

    async def publish(self, run_id: str, event: dict) -> None:
        for q in list(self._subscribers.get(run_id, set())):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass


# Singleton
store = SQLiteRunStore()
