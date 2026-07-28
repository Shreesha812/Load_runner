import { useEffect, useRef, useState } from "react";
import { Square, TrendingUp } from "lucide-react";
import { WS_BASE, getRun, cancelRun } from "../api";
import type { MetricsSnapshot, TestResult, WsEvent } from "../types";
import { MetricCard } from "../components/MetricCard";
import { LiveChart } from "../components/LiveChart";
import { StatusBadge } from "../components/StatusBadge";

interface Props {
  runId: string;
  onDone: (results: TestResult[]) => void;
}

interface LivePoint { t: number; rps: number; avg: number; workers: number }

export function LivePage({ runId, onDone }: Props) {
  const [status, setStatus]           = useState("Connecting…");
  const [testName, setTestName]       = useState("");
  const [testIdx, setTestIdx]         = useState(0);
  const [testTotal, setTestTotal]     = useState(0);
  const [concurrency, setConcurrency] = useState(0);
  const [rampUp, setRampUp]           = useState(0);   // ramp_up_seconds for current test
  const [activeWorkers, setActive]    = useState(0);   // live count from server
  const [metrics, setMetrics]         = useState<MetricsSnapshot | null>(null);
  const [points, setPoints]           = useState<LivePoint[]>([]);
  const [runDone, setRunDone]         = useState(false);
  const [wsError, setWsError]         = useState(false);
  const [cancelling, setCancelling]   = useState(false);

  const tRef        = useRef(0);
  const receivedAny = useRef(false);
  const doneRef     = useRef(false);

  const pollForResult = async () => {
    try {
      const run = await getRun(runId);
      if (run.status === "done" && run.results?.length > 0) {
        doneRef.current = true;
        setRunDone(true);
        setTimeout(() => onDone(run.results), 400);
      } else if (run.status === "error") {
        setWsError(true);
        setStatus(run.error || "Run failed.");
      } else {
        setTimeout(pollForResult, 1500);
      }
    } catch {
      setWsError(true);
      setStatus("Could not reach the server.");
    }
  };

  const handleStop = async () => {
    setCancelling(true);
    try {
      await cancelRun(runId);
      setStatus("Cancellation requested — finishing in-flight requests…");
    } catch (e: any) {
      setStatus(`Stop failed: ${e.message}`);
      setCancelling(false);
    }
  };

  useEffect(() => {
    const ws = new WebSocket(`${WS_BASE}/run/${runId}/live`);

    ws.onmessage = (e) => {
      receivedAny.current = true;
      const evt: WsEvent = JSON.parse(e.data);
      if (evt.type === "ping") return;

      if (evt.type === "status") {
        setStatus(evt.message);

      } else if (evt.type === "test_start") {
        setTestName(evt.test_name);
        setTestIdx(evt.index);
        setTestTotal(evt.total);
        setConcurrency(evt.concurrency);
        setRampUp(evt.ramp_up_seconds ?? 0);
        setActive(evt.ramp_up_seconds > 0 ? 0 : evt.concurrency);
        setStatus(
          evt.ramp_up_seconds > 0
            ? `Ramping up — 0 / ${evt.concurrency} workers over ${evt.ramp_up_seconds}s`
            : `Running — ${evt.concurrency} workers, ${evt.strategy}`
        );
        setPoints([]);
        tRef.current = 0;

      } else if (evt.type === "live_metrics") {
        const w = evt.active_workers ?? concurrency;
        setActive(w);
        setMetrics(evt.metrics);
        tRef.current += 1;
        setPoints((prev) => [
          ...prev.slice(-60),
          {
            t: tRef.current,
            rps: evt.metrics.requests_per_second,
            avg: evt.metrics.avg_latency_ms,
            workers: w,
          },
        ]);
        // Keep status line fresh during ramp
        if (rampUp > 0 && w < concurrency) {
          setStatus(`Ramping up — ${w} / ${concurrency} workers active`);
        } else if (rampUp > 0 && w >= concurrency) {
          setStatus(`Running at full load — ${concurrency} workers`);
        }

      } else if (evt.type === "test_done") {
        setMetrics(evt.metrics);

      } else if (evt.type === "done") {
        doneRef.current = true;
        setRunDone(true);
        setTimeout(() => onDone(evt.results), 600);

      } else if (evt.type === "error") {
        setWsError(true);
        setStatus((evt as any).message || "Run encountered an error.");
      }
    };

    ws.onclose = () => {
      if (doneRef.current) return;
      if (!receivedAny.current) { setStatus("Connecting via fallback…"); pollForResult(); return; }
      if (!doneRef.current)     { setStatus("Fetching final results…");  pollForResult(); }
    };

    ws.onerror = () => { /* handled by onclose */ };

    return () => { doneRef.current = true; ws.close(); };
  }, [runId]);

  const progress      = testTotal > 0 ? ((testIdx - 1) / testTotal) * 100 : 0;
  const rampProgress  = concurrency > 0 ? (activeWorkers / concurrency) * 100 : 100;
  const currentStatus = runDone ? "done" : wsError ? "error" : "running";
  const canStop       = !runDone && !wsError && !cancelling;
  const isRamping     = rampUp > 0;

  return (
    <div className="max-w-4xl mx-auto">

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-white">Live Run</h1>
          <p className="text-gray-500 text-sm font-mono mt-0.5">{runId}</p>
        </div>
        <div className="flex items-center gap-3">
          {/* Ramp-up badge */}
          {isRamping && !runDone && (
            <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full
              bg-purple-900/30 border border-purple-800 text-purple-400 text-xs font-medium">
              <TrendingUp size={11} />
              Ramp-up {rampUp}s
            </span>
          )}
          {canStop && (
            <button onClick={handleStop}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-red-800
                bg-red-900/20 text-red-400 hover:bg-red-900/40 text-sm transition-colors">
              <Square size={13} /> Stop
            </button>
          )}
          {cancelling && !runDone && (
            <span className="text-xs text-yellow-400 animate-pulse">Stopping…</span>
          )}
          <StatusBadge status={currentStatus as any} />
        </div>
      </div>

      {/* Test progress bar */}
      {testTotal > 0 && (
        <div className="mb-4">
          <div className="flex justify-between text-xs text-gray-500 mb-1.5">
            <span className="truncate max-w-xs">{testName || "Initialising…"}</span>
            <span className="shrink-0 ml-4">{testIdx} / {testTotal}</span>
          </div>
          <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
            <div className="h-full bg-brand-500 rounded-full transition-all duration-500"
              style={{ width: `${Math.max(5, progress)}%` }} />
          </div>
        </div>
      )}

      {/* Ramp-up progress bar — only visible during ramp phase */}
      {isRamping && !runDone && activeWorkers < concurrency && (
        <div className="mb-4">
          <div className="flex justify-between text-xs text-gray-500 mb-1.5">
            <span className="text-purple-400">Ramping workers</span>
            <span className="text-purple-400">{activeWorkers} / {concurrency}</span>
          </div>
          <div className="h-1 bg-gray-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-purple-500 rounded-full transition-all duration-300"
              style={{ width: `${Math.max(2, rampProgress)}%` }}
            />
          </div>
        </div>
      )}

      {/* Status line */}
      <p className={`text-sm mb-6 ${wsError ? "text-red-400" : "text-gray-400"}`}>
        {status}
      </p>

      {/* Live chart */}
      {points.length > 1 && (
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 mb-6">
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-3">
            Live —{" "}
            <span className="text-blue-400">RPS</span>
            {" & "}
            <span className="text-yellow-400">Avg Latency</span>
            {isRamping && (
              <>{" & "}<span className="text-purple-400">Workers</span></>
            )}
          </p>
          <LiveChart
            points={points}
            totalWorkers={concurrency}
            isRamping={isRamping}
          />
        </div>
      )}

      {/* Metric cards */}
      {metrics && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <MetricCard label="Requests"    value={metrics.total_requests} highlight />
          <MetricCard
            label="Success rate"
            value={metrics.total_requests > 0
              ? `${((metrics.successful_requests / metrics.total_requests) * 100).toFixed(1)}%`
              : "—"}
            highlight
          />
          {/* Show active workers card only when ramp-up is configured */}
          {isRamping ? (
            <MetricCard
              label="Active workers"
              value={`${activeWorkers} / ${concurrency}`}
              sub={activeWorkers >= concurrency ? "full load" : "ramping…"}
            />
          ) : (
            <MetricCard label="RPS" value={metrics.requests_per_second.toFixed(1)} />
          )}
          <MetricCard label="Avg latency" value={`${metrics.avg_latency_ms.toFixed(0)} ms`} />
          <MetricCard label="P50"         value={`${metrics.p50_latency_ms.toFixed(0)} ms`} />
          <MetricCard label="P95"         value={`${metrics.p95_latency_ms.toFixed(0)} ms`} />
          <MetricCard label="P99"         value={`${metrics.p99_latency_ms.toFixed(0)} ms`} />
          <MetricCard label="Elapsed"     value={`${metrics.execution_time_s.toFixed(1)} s`} />
        </div>
      )}

      {runDone && (
        <div className="mt-6 p-3 rounded-lg bg-green-900/30 border border-green-800 text-green-400 text-sm">
          Run complete — loading results…
        </div>
      )}
    </div>
  );
}
