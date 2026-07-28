export type RunStatus = "pending" | "running" | "done" | "error";

export interface RequestEntry {
  id: string;
  status: number | null;
  latency_ms: number;
  combination: Record<string, string>;
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
  success_list: RequestEntry[];
  failure_list: RequestEntry[];
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
  | { type: "test_start";   index: number; total: number; test_name: string; concurrency: number; strategy: string }
  | { type: "live_metrics"; test_name: string; metrics: MetricsSnapshot }
  | { type: "test_done";    index: number; test_name: string; metrics: MetricsSnapshot }
  | { type: "done";         results: TestResult[] }
  | { type: "error";        message: string }
  | { type: "ping" };
