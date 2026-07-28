import { useState } from "react";
import { Download, ArrowLeft, ChevronDown, ChevronUp, CheckCircle, XCircle } from "lucide-react";
import type { TestResult, RequestEntry } from "../types";
import { MetricCard } from "../components/MetricCard";
import { MetricsTable } from "../components/MetricsTable";
import { LatencyChart } from "../components/LatencyChart";
import { downloadJson, downloadCsv } from "../api";

interface Props {
  runId: string;
  results: TestResult[];
  onBack: () => void;
}

function aggregate(results: TestResult[]) {
  if (!results.length) return null;
  const total   = results.reduce((s, r) => s + r.metrics.total_requests, 0);
  const success = results.reduce((s, r) => s + r.metrics.successful_requests, 0);
  const failed  = results.reduce((s, r) => s + r.metrics.failed_requests, 0);
  const avgLat  = results.reduce((s, r) => s + r.metrics.avg_latency_ms, 0) / results.length;
  const p99     = Math.max(...results.map((r) => r.metrics.p99_latency_ms));
  const rps     = results.reduce((s, r) => s + r.metrics.requests_per_second, 0);
  const totalTime = Math.max(...results.map((r) => r.metrics.execution_time_s));
  const statuses  = results.map((r) => r.metrics.overall_status);
  const overallStatus = statuses.every((s) => s === "success")
    ? "success"
    : statuses.every((s) => s === "failure")
    ? "failure"
    : "partial_failure";
  return { total, success, failed, avgLat, p99, rps, totalTime, overallStatus };
}

// Inline collapsible request list
function RequestList({ entries, type }: { entries: RequestEntry[]; type: "success" | "failure" }) {
  const [open, setOpen] = useState(false);
  if (!entries.length) return null;
  const isSuccess = type === "success";
  return (
    <div className={`rounded-lg border ${isSuccess ? "border-green-900" : "border-red-900"} overflow-hidden`}>
      <button
        onClick={() => setOpen(!open)}
        className={`w-full flex items-center justify-between px-4 py-3 text-sm font-medium
          ${isSuccess ? "bg-green-900/20 text-green-400" : "bg-red-900/20 text-red-400"}
          hover:opacity-80 transition-opacity`}
      >
        <span className="flex items-center gap-2">
          {isSuccess
            ? <CheckCircle size={15} />
            : <XCircle size={15} />}
          {isSuccess ? "Success list" : "Failure list"} — {entries.length} request{entries.length !== 1 ? "s" : ""}
        </span>
        {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      </button>
      {open && (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-gray-900 text-gray-500">
                <th className="px-4 py-2 text-left font-medium">Request ID</th>
                <th className="px-4 py-2 text-left font-medium">Status</th>
                <th className="px-4 py-2 text-right font-medium">Latency</th>
                <th className="px-4 py-2 text-left font-medium">Variables</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e, i) => (
                <tr key={i} className="border-t border-gray-800 hover:bg-gray-900/30">
                  <td className="px-4 py-2 font-mono text-gray-300">{e.id}</td>
                  <td className={`px-4 py-2 font-mono font-medium
                    ${e.status && e.status < 400 ? "text-green-400" : "text-red-400"}`}>
                    {e.status ?? "error"}
                  </td>
                  <td className="px-4 py-2 font-mono text-gray-300 text-right">
                    {e.latency_ms.toFixed(1)} ms
                  </td>
                  <td className="px-4 py-2 text-gray-500 font-mono">
                    {Object.entries(e.combination).map(([k, v]) => `${k}=${v}`).join(", ") || "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// Status badge for the overall test run
function OverallStatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    success:          "bg-green-900/40 text-green-400 border-green-800",
    failure:          "bg-red-900/40 text-red-400 border-red-800",
    partial_failure:  "bg-yellow-900/40 text-yellow-400 border-yellow-800",
    no_requests:      "bg-gray-800 text-gray-500 border-gray-700",
  };
  const label: Record<string, string> = {
    success:         "Success",
    failure:         "Failure",
    partial_failure: "Partial Failure",
    no_requests:     "No Requests",
  };
  return (
    <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium border ${styles[status] ?? styles.no_requests}`}>
      {label[status] ?? status}
    </span>
  );
}

export function ResultsPage({ runId, results, onBack }: Props) {
  const agg = aggregate(results);

  return (
    <div className="max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <button onClick={onBack}
          className="flex items-center gap-1.5 text-gray-400 hover:text-white text-sm transition-colors">
          <ArrowLeft size={16} /> Back
        </button>
        <div className="flex-1">
          <h1 className="text-2xl font-semibold text-white">Results</h1>
          <p className="text-gray-500 text-sm font-mono">{runId}</p>
        </div>
        {agg && <OverallStatusBadge status={agg.overallStatus} />}
        <div className="flex gap-2">
          <button onClick={() => downloadJson(runId)}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-gray-700
              hover:border-gray-600 text-gray-300 hover:text-white text-sm transition-colors">
            <Download size={14} /> JSON
          </button>
          <button onClick={() => downloadCsv(runId)}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-gray-700
              hover:border-gray-600 text-gray-300 hover:text-white text-sm transition-colors">
            <Download size={14} /> CSV
          </button>
        </div>
      </div>

      {/* Aggregate summary cards */}
      {agg && (
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3 mb-8">
          <MetricCard label="Total time"     value={`${agg.totalTime.toFixed(2)} s`} highlight />
          <MetricCard label="Total requests" value={agg.total} />
          <MetricCard label="Success"        value={agg.success} />
          <MetricCard label="Failed"         value={agg.failed}
            sub={agg.failed > 0 ? "see failure list" : "all good"} />
          <MetricCard label="Avg latency"    value={`${agg.avgLat.toFixed(0)} ms`} />
          <MetricCard label="P99 latency"    value={`${agg.p99.toFixed(0)} ms`} />
          <MetricCard label="Total RPS"      value={agg.rps.toFixed(1)} />
        </div>
      )}

      {/* Latency chart */}
      <div className="bg-gray-900 border border-gray-800 rounded-lg p-5 mb-6">
        <p className="text-sm font-medium text-gray-300 mb-4">Latency breakdown — per test</p>
        <LatencyChart results={results} />
      </div>

      {/* Per-test metrics table */}
      <div className="mb-6">
        <p className="text-sm font-medium text-gray-300 mb-3">Per-test metrics</p>
        <MetricsTable results={results} />
      </div>

      {/* Per-test response structure: success + failure lists */}
      {results.map((r, i) => {
        const hasList = r.metrics.success_list.length > 0 || r.metrics.failure_list.length > 0;
        if (!hasList) return null;
        return (
          <div key={i} className="mb-6">
            <p className="text-sm font-medium text-gray-400 mb-2 font-mono truncate">
              {r.test_name}
            </p>
            <div className="space-y-2">
              <RequestList entries={r.metrics.success_list} type="success" />
              <RequestList entries={r.metrics.failure_list} type="failure" />
            </div>
          </div>
        );
      })}
    </div>
  );
}
