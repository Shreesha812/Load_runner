"""
Async runner — bridges the load-runner engine with the API.
Supports graceful cancellation via asyncio.Event from cancel_registry.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from backend.cancel import cancel_registry
from backend.models import MetricsSnapshot, RunStatus, RunSummary, TestResult
from backend.store import store

logger = logging.getLogger(__name__)


def _snapshot(metrics) -> MetricsSnapshot:
    from backend.models import RequestEntry as ApiEntry

    def _entries(lst):
        return [
            ApiEntry(id=e.id, status=e.status, latency_ms=e.latency_ms,
                     combination=e.combination, error_type=e.error_type)
            for e in lst
        ]

    return MetricsSnapshot(
        total_requests=metrics.total_requests,
        successful_requests=metrics.successful_requests,
        failed_requests=metrics.failed_requests,
        avg_latency_ms=round(metrics.average_latency, 3),
        min_latency_ms=round(metrics.min_latency if metrics.total_requests > 0 else 0.0, 3),
        max_latency_ms=round(metrics.max_latency, 3),
        p50_latency_ms=round(metrics.p50, 3),
        p95_latency_ms=round(metrics.p95, 3),
        p99_latency_ms=round(metrics.p99, 3),
        requests_per_second=round(metrics.requests_per_second, 3),
        execution_time_s=round(metrics.execution_time, 3),
        overall_status=metrics.overall_status,
        timeout_errors=metrics.timeout_errors,
        connection_errors=metrics.connection_errors,
        client_errors=metrics.client_errors,
        server_errors=metrics.server_errors,
        unknown_errors=metrics.unknown_errors,
        success_list=_entries(metrics.success_list),
        failure_list=_entries(metrics.failure_list),
    )


async def execute_run(run_id: str, xlsx_path: str, config) -> None:
    from factory.configuration_factory import ConfigurationFactory
    from generator.combination_generator import CombinationGenerator
    from metrics.metrics import Metrics
    from parser.excel_parser import ExcelParser
    from scheduler.scheduler import Scheduler
    from validator.configuration_validator import ConfigurationValidator

    run = await store.get(run_id)
    if run is None:
        return

    # Register a cancellation event — DELETE /api/run/{id} will set this
    cancel_event = cancel_registry.register(run_id)

    async def emit(event_type: str, payload: dict) -> None:
        await store.publish(run_id, {"type": event_type, **payload})

    try:
        await emit("status", {"status": RunStatus.running, "message": "Parsing Excel file..."})
        wb = ExcelParser(xlsx_path).parse()

        await emit("status", {"status": RunStatus.running, "message": "Building configuration..."})
        cfg = ConfigurationFactory().build(wb)
        errors = ConfigurationValidator().validate(cfg)
        if errors:
            raise ValueError("; ".join(errors))

        enabled = [td for td in cfg.test_definitions if td.enabled]
        await emit("status", {
            "status": RunStatus.running,
            "message": f"Found {len(enabled)} enabled test(s). Starting...",
        })

        generator = CombinationGenerator()
        scheduler = Scheduler()
        results: list[TestResult] = []

        for idx, test_def in enumerate(enabled, 1):
            # Check cancellation between tests
            if cancel_event.is_set():
                logger.info("Run %s cancelled before test %d.", run_id, idx)
                break

            test_name = f"Test {idx}: {test_def.method} {test_def.url}"
            ramp_up = getattr(test_def, "ramp_up_seconds", 0) or 0
            await emit("test_start", {
                "index": idx,
                "total": len(enabled),
                "test_name": test_name,
                "concurrency": test_def.concurrency,
                "strategy": test_def.strategy,
                "ramp_up_seconds": ramp_up,
            })

            metrics = Metrics()

            async def stream_live(m=metrics, name=test_name, sched=scheduler):
                while True:
                    await asyncio.sleep(0.5)
                    active = (
                        sched.ramp_controller.active_workers
                        if sched.ramp_controller is not None
                        else test_def.concurrency
                    )
                    await emit("live_metrics", {
                        "test_name": name,
                        "metrics": _snapshot(m).model_dump(),
                        "active_workers": active,
                    })
                    await store.record_timeseries(
                        run_id, name,
                        m.requests_per_second, m.average_latency, m.total_requests,
                    )

            stream_task = asyncio.create_task(stream_live())

            try:
                await scheduler.run(
                    test_def,
                    generator.generate(test_def),
                    metrics,
                    http_timeout=config.timeout,
                    http_connect_timeout=config.connect_timeout,
                    http_pool_size=config.pool_size,
                    cancel_event=cancel_event,
                )
            finally:
                stream_task.cancel()
                try:
                    await stream_task
                except asyncio.CancelledError:
                    pass

            final = _snapshot(metrics)
            results.append(TestResult(test_name=test_name, metrics=final))
            await emit("test_done", {"index": idx, "test_name": test_name, "metrics": final.model_dump()})

        # Determine final status
        if cancel_event.is_set():
            run.status = RunStatus.error
            run.error = "Cancelled by user."
            run.results = results   # save partial results
            run.finished_at = datetime.now(timezone.utc).isoformat()
            await store.update(run)
            await emit("error", {"message": "Cancelled by user."})
        else:
            run.results = results
            run.status = RunStatus.done
            run.finished_at = datetime.now(timezone.utc).isoformat()
            await store.update(run)
            await emit("done", {"results": [r.model_dump() for r in results]})

    except Exception as exc:
        logger.exception("Run %s failed: %s", run_id, exc)
        run.status = RunStatus.error
        run.error = str(exc)
        run.finished_at = datetime.now(timezone.utc).isoformat()
        await store.update(run)
        await emit("error", {"message": str(exc)})
    finally:
        cancel_registry.remove(run_id)
