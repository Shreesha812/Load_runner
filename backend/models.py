"""Pydantic models for the API layer."""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel


class RunStatus(str, Enum):
    pending  = "pending"
    running  = "running"
    done     = "done"
    error    = "error"


class TestConfig(BaseModel):
    timeout: int = 30
    connect_timeout: int = 10
    pool_size: int = 100


class RequestEntry(BaseModel):
    id: str
    status: Optional[int] = None
    latency_ms: float
    combination: dict = {}
    error_type: str = ""                  # timeout | connection_error | 4xx | 5xx | unknown | validation_failed
    validation_failures: list[str] = []   # rules that failed, e.g. ["missing:token", "status=success (got 'error')"]


class MetricsSnapshot(BaseModel):
    # Counts
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    # Latency
    avg_latency_ms: float = 0.0
    min_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    # Throughput
    requests_per_second: float = 0.0
    execution_time_s: float = 0.0
    # Status summary
    overall_status: str = "no_requests"
    # Error breakdown
    timeout_errors: int = 0
    connection_errors: int = 0
    client_errors: int = 0
    server_errors: int = 0
    unknown_errors: int = 0
    validation_errors: int = 0
    # Per-request detail
    success_list: list[RequestEntry] = []
    failure_list: list[RequestEntry] = []


class TestResult(BaseModel):
    test_name: str
    metrics: MetricsSnapshot


class RunSummary(BaseModel):
    run_id: str
    filename: str
    status: RunStatus
    started_at: str
    finished_at: Optional[str] = None
    results: list[TestResult] = []
    error: Optional[str] = None
