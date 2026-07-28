import asyncio
import time
from dataclasses import dataclass, field

from models.http_response import HttpResponse


@dataclass
class RequestEntry:
    """One entry in the success or failure list."""
    id: str
    status: int | None
    latency_ms: float
    combination: dict = field(default_factory=dict)


class Metrics:
    """
    Asyncio-safe metrics collector.

    Tracks counts, latency distribution (P50/P95/P99), overall execution
    timing, and per-request success/failure lists with their IDs.
    """

    def __init__(self):
        self.total_requests: int = 0
        self.successful_requests: int = 0
        self.failed_requests: int = 0

        self.total_latency: float = 0.0
        self.min_latency: float = float("inf")
        self.max_latency: float = 0.0

        self._latencies: list[float] = []

        # Per-request detail lists
        self.success_list: list[RequestEntry] = []
        self.failure_list: list[RequestEntry] = []

        self.start_time: float = time.perf_counter()
        self._lock = asyncio.Lock()

    async def record(self, response: HttpResponse) -> None:
        async with self._lock:
            self.total_requests += 1
            self.total_latency += response.latency
            self._latencies.append(response.latency)

            self.min_latency = min(self.min_latency, response.latency)
            self.max_latency = max(self.max_latency, response.latency)

            entry = RequestEntry(
                id=response.request_id,
                status=response.status,
                latency_ms=round(response.latency, 3),
                combination=response.combination,
            )

            if response.status is not None and 200 <= response.status < 400:
                self.successful_requests += 1
                self.success_list.append(entry)
            else:
                self.failed_requests += 1
                self.failure_list.append(entry)

    # ── Computed properties ─────────────────────────────────────────────

    @property
    def average_latency(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_latency / self.total_requests

    @property
    def execution_time(self) -> float:
        return time.perf_counter() - self.start_time

    @property
    def requests_per_second(self) -> float:
        elapsed = self.execution_time
        return 0.0 if elapsed == 0 else self.total_requests / elapsed

    def percentile(self, p: float) -> float:
        if not self._latencies:
            return 0.0
        s = sorted(self._latencies)
        idx = max(0, int(len(s) * p / 100) - 1)
        return s[min(idx, len(s) - 1)]

    @property
    def p50(self) -> float: return self.percentile(50)

    @property
    def p95(self) -> float: return self.percentile(95)

    @property
    def p99(self) -> float: return self.percentile(99)

    @property
    def overall_status(self) -> str:
        if self.total_requests == 0:
            return "no_requests"
        if self.failed_requests == 0:
            return "success"
        if self.successful_requests == 0:
            return "failure"
        return "partial_failure"
