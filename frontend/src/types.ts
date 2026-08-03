export type RunStatus = "pending" | "running" | "done" | "error";

export interface RequestEntry {
  id: string;
  status: number | null;
  latency_ms: number;
  combination: Record<string, string>;
  error_type: string;
  validation_failures: string[];  // failed rule descriptions, e.g. ["missing:token"]
}

export interface MetricsSnapshot {
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  avg_latency_ms: number;
  min_latency_ms: number;
  max_latency_ms: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
  requests_per_second: number;
  execution_time_s: number;
  overall_status: string;
  // Error breakdown
  timeout_errors: number;
  connection_errors: number;
  client_errors: number;
  server_errors: number;
  unknown_errors: number;
  validation_errors: number;
  success_list: RequestEntry[];
  failure_list: RequestEntry[];
}

export interface TestOverride {
  test_idx: number;
  test_name: string;
  enabled: boolean;
}

export interface TestResult {
  test_name: string;
  metrics: MetricsSnapshot;
}

export interface RunSummary {
  run_id: string;
  filename: string;
  status: RunStatus;
  started_at: string;
  finished_at: string | null;
  results: TestResult[];
  error: string | null;
}

// WebSocket event shapes
export type WsEvent =
  | { type: "status";       status: RunStatus; message: string }
  | { type: "test_start";   index: number; total: number; test_name: string; concurrency: number; strategy: string; ramp_up_seconds: number }
  | { type: "live_metrics"; test_name: string; metrics: MetricsSnapshot; active_workers: number }
  | { type: "test_done";    index: number; test_name: string; metrics: MetricsSnapshot }
  | { type: "done";         results: TestResult[] }
  | { type: "error";        message: string }
  | { type: "ping" };
