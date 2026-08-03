"""FastAPI route definitions."""
from __future__ import annotations

import asyncio
import csv
import json
import os
import tempfile
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from backend.cancel import cancel_registry
from backend.models import RunStatus, RunSummary, TestConfig
from backend.runner import execute_run
from backend.store import store

router = APIRouter()

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "input", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ── POST /api/run ─────────────────────────────────────────────────────────
@router.post("/run")
async def start_run(
    file: UploadFile,
    timeout: int = 30,
    connect_timeout: int = 10,
    pool_size: int = 100,
):
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(400, "Only .xlsx files are supported.")

    run_id = str(uuid.uuid4())[:8]
    dest = os.path.join(UPLOAD_DIR, f"{run_id}_{file.filename}")
    contents = await file.read()
    with open(dest, "wb") as f:
        f.write(contents)

    config = TestConfig(timeout=timeout, connect_timeout=connect_timeout, pool_size=pool_size)
    run = RunSummary(
        run_id=run_id,
        filename=file.filename,
        status=RunStatus.pending,
        started_at=datetime.now(timezone.utc).isoformat(),
    )
    await store.create(run)
    asyncio.create_task(execute_run(run_id, dest, config))
    return {"run_id": run_id}


# ── DELETE /api/run/{run_id} — cancel ─────────────────────────────────────
@router.delete("/run/{run_id}")
async def cancel_run(run_id: str):
    run = await store.get(run_id)
    if not run:
        raise HTTPException(404, f"Run {run_id!r} not found.")
    if run.status not in (RunStatus.pending, RunStatus.running):
        raise HTTPException(409, f"Run {run_id!r} is already {run.status.value}.")
    if not cancel_registry.cancel(run_id):
        raise HTTPException(409, f"Run {run_id!r} has no active cancel token.")
    return {"run_id": run_id, "message": "Cancellation requested."}


# ── GET /api/run/{run_id} ─────────────────────────────────────────────────
@router.get("/run/{run_id}")
async def get_run(run_id: str):
    run = await store.get(run_id)
    if not run:
        raise HTTPException(404, f"Run {run_id!r} not found.")
    return run


# ── GET /api/runs ─────────────────────────────────────────────────────────
@router.get("/runs")
async def list_runs():
    return await store.all()


# ── WS /api/run/{run_id}/live ─────────────────────────────────────────────
@router.websocket("/run/{run_id}/live")
async def live_stream(websocket: WebSocket, run_id: str):
    run = await store.get(run_id)
    if not run:
        await websocket.close(code=4004)
        return

    await websocket.accept()

    if run.status in (RunStatus.done, RunStatus.error):
        event = {
            "type": "done" if run.status == RunStatus.done else "error",
            "results": [r.model_dump() for r in run.results],
            "message": run.error or "",
        }
        await websocket.send_text(json.dumps(event))
        await asyncio.sleep(0.2)
        await websocket.close()
        return

    q = store.subscribe(run_id)
    try:
        while True:
            try:
                event = await asyncio.wait_for(q.get(), timeout=30.0)
                await websocket.send_text(json.dumps(event, default=str))
                if event.get("type") in ("done", "error"):
                    break
            except asyncio.TimeoutError:
                await websocket.send_text(json.dumps({"type": "ping"}))
    except WebSocketDisconnect:
        pass
    finally:
        store.unsubscribe(run_id, q)
        try:
            await websocket.close()
        except Exception:
            pass


# ── GET /api/results/{run_id}/json ────────────────────────────────────────
@router.get("/results/{run_id}/json")
async def download_json(run_id: str):
    run = await store.get(run_id)
    if not run or run.status != RunStatus.done:
        raise HTTPException(404, "Results not available.")

    # Build JSON directly from the already-correct MetricsSnapshot fields.
    # Previously this reconstructed a fake Metrics engine object with only
    # 3 latency samples which produced wrong P50/P95/P99 values.
    records = []
    for result in run.results:
        m = result.metrics
        records.append({
            "test_name":            result.test_name,
            "total_requests":       m.total_requests,
            "successful_requests":  m.successful_requests,
            "failed_requests":      m.failed_requests,
            "avg_latency_ms":       m.avg_latency_ms,
            "min_latency_ms":       m.min_latency_ms,
            "max_latency_ms":       m.max_latency_ms,
            "p50_latency_ms":       m.p50_latency_ms,
            "p95_latency_ms":       m.p95_latency_ms,
            "p99_latency_ms":       m.p99_latency_ms,
            "requests_per_second":  m.requests_per_second,
            "execution_time_s":     m.execution_time_s,
            "overall_status":       m.overall_status,
            "timeout_errors":       m.timeout_errors,
            "connection_errors":    m.connection_errors,
            "client_errors":        m.client_errors,
            "server_errors":        m.server_errors,
            "unknown_errors":       m.unknown_errors,
            "validation_errors":    m.validation_errors,
        })

    import json as _json
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
        path = f.name
        _json.dump(records, f, indent=2)

    return FileResponse(path, filename=f"results_{run_id}.json", media_type="application/json")


# ── GET /api/results/{run_id}/csv ─────────────────────────────────────────
@router.get("/results/{run_id}/csv")
async def download_csv(run_id: str):
    run = await store.get(run_id)
    if not run or run.status != RunStatus.done:
        raise HTTPException(404, "Results not available.")

    fields = [
        "test_name", "total_requests", "successful_requests", "failed_requests",
        "avg_latency_ms", "min_latency_ms", "max_latency_ms",
        "p50_latency_ms", "p95_latency_ms", "p99_latency_ms",
        "requests_per_second", "execution_time_s", "overall_status",
        "timeout_errors", "connection_errors", "client_errors",
        "server_errors", "unknown_errors", "validation_errors",
    ]
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w", newline="") as f:
        path = f.name
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for result in run.results:
            m = result.metrics
            writer.writerow({
                "test_name":           result.test_name,
                "total_requests":      m.total_requests,
                "successful_requests": m.successful_requests,
                "failed_requests":     m.failed_requests,
                "avg_latency_ms":      m.avg_latency_ms,
                "min_latency_ms":      m.min_latency_ms,
                "max_latency_ms":      m.max_latency_ms,
                "p50_latency_ms":      m.p50_latency_ms,
                "p95_latency_ms":      m.p95_latency_ms,
                "p99_latency_ms":      m.p99_latency_ms,
                "requests_per_second": m.requests_per_second,
                "execution_time_s":    m.execution_time_s,
                "overall_status":      m.overall_status,
                "timeout_errors":      m.timeout_errors,
                "connection_errors":   m.connection_errors,
                "client_errors":       m.client_errors,
                "server_errors":       m.server_errors,
                "unknown_errors":      m.unknown_errors,
                "validation_errors":   m.validation_errors,
            })

    return FileResponse(path, filename=f"results_{run_id}.csv", media_type="text/csv")


# ── PATCH /api/run/{run_id}/toggle — enable/disable a test definition ────
@router.patch("/run/{run_id}/toggle")
async def toggle_test(run_id: str, test_idx: int, enabled: bool):
    """
    Set the enabled/disabled override for a test definition inside a run.
    test_idx is 0-based index into the run's results list.
    """
    run = await store.get(run_id)
    if not run:
        raise HTTPException(404, f"Run {run_id!r} not found.")
    if test_idx < 0 or test_idx >= len(run.results):
        raise HTTPException(400, f"test_idx {test_idx} out of range (0–{len(run.results)-1}).")
    await store.set_test_enabled(run_id, test_idx, enabled)
    return {"run_id": run_id, "test_idx": test_idx, "enabled": enabled}


# ── GET /api/run/{run_id}/overrides — fetch current toggle state ──────────
@router.get("/run/{run_id}/overrides")
async def get_overrides(run_id: str):
    run = await store.get(run_id)
    if not run:
        raise HTTPException(404, f"Run {run_id!r} not found.")
    overrides = await store.get_test_overrides(run_id)
    # Build full list using stored override or original enabled value from test_name
    result = []
    for idx, tr in enumerate(run.results):
        result.append({
            "test_idx":  idx,
            "test_name": tr.test_name,
            "enabled":   overrides.get(idx, True),  # default True if never toggled
        })
    return result


# ── GET /api/compare ──────────────────────────────────────────────────────
@router.get("/compare")
async def compare_runs(run_a: str, run_b: str):
    """
    Return both runs side by side with per-metric deltas.
    Delta = run_b value - run_a value (positive = run_b is higher).
    """
    a = await store.get(run_a)
    b = await store.get(run_b)

    if not a:
        raise HTTPException(404, f"Run {run_a!r} not found.")
    if not b:
        raise HTTPException(404, f"Run {run_b!r} not found.")
    if a.status != RunStatus.done:
        raise HTTPException(409, f"Run {run_a!r} is not complete yet.")
    if b.status != RunStatus.done:
        raise HTTPException(409, f"Run {run_b!r} is not complete yet.")

    def _metrics_dict(m) -> dict:
        return {
            "total_requests":      m.total_requests,
            "successful_requests": m.successful_requests,
            "failed_requests":     m.failed_requests,
            "avg_latency_ms":      m.avg_latency_ms,
            "min_latency_ms":      m.min_latency_ms,
            "max_latency_ms":      m.max_latency_ms,
            "p50_latency_ms":      m.p50_latency_ms,
            "p95_latency_ms":      m.p95_latency_ms,
            "p99_latency_ms":      m.p99_latency_ms,
            "requests_per_second": m.requests_per_second,
            "execution_time_s":    m.execution_time_s,
            "overall_status":      m.overall_status,
        }

    def _delta(ma: dict, mb: dict) -> dict:
        numeric_keys = [k for k, v in ma.items() if isinstance(v, (int, float))]
        return {k: round(mb[k] - ma[k], 3) for k in numeric_keys}

    # Pair test results by position (same index) or by matching test name
    paired = []
    a_names = {r.test_name: r for r in a.results}
    b_names = {r.test_name: r for r in b.results}

    # First try name-matching
    all_names = list(dict.fromkeys(list(a_names) + list(b_names)))
    for name in all_names:
        ra = a_names.get(name)
        rb = b_names.get(name)
        ma = _metrics_dict(ra.metrics) if ra else None
        mb = _metrics_dict(rb.metrics) if rb else None
        paired.append({
            "test_name": name,
            "run_a":     ma,
            "run_b":     mb,
            "delta":     _delta(ma, mb) if ma and mb else None,
        })

    return {
        "run_a": {
            "run_id":     a.run_id,
            "filename":   a.filename,
            "started_at": a.started_at,
        },
        "run_b": {
            "run_id":     b.run_id,
            "filename":   b.filename,
            "started_at": b.started_at,
        },
        "pairs": paired,
    }
