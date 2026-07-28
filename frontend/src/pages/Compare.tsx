import { useEffect, useState } from "react";
import { ArrowLeftRight, ArrowLeft, RefreshCw, TrendingUp, TrendingDown, Minus } from "lucide-react";
import { listRuns, compareRuns } from "../api";
import type { RunSummary } from "../types";
import { CompareChart } from "../components/CompareChart";

interface Props {
  preselectedA?: string;
  onBack: () => void;
}

interface MetricsRow {
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
}

interface Pair {
  test_name: string;
  run_a: MetricsRow | null;
  run_b: MetricsRow | null;
  delta: Record<string, number> | null;
}

interface CompareResult {
  run_a: { run_id: string; filename: string; started_at: string };
  run_b: { run_id: string; filename: string; started_at: string };
  pairs: Pair[];
}

// Format a delta value with colour and arrow
function Delta({ value, lowerIsBetter = true }: { value: number | null; lowerIsBetter?: boolean }) {
  if (value === null || value === undefined) return <span className="text-gray-600">—</span>;
  if (Math.abs(value) < 0.01) return (
    <span className="flex items-center gap-0.5 text-gray-500 text-xs font-mono">
      <Minus size={10} /> 0
    </span>
  );
  const improved = lowerIsBetter ? value < 0 : value > 0;
  return (
    <span className={`flex items-center gap-0.5 text-xs font-mono font-medium
      ${improved ? "text-green-400" : "text-red-400"}`}>
      {improved ? <TrendingDown size={10} /> : <TrendingUp size={10} />}
      {value > 0 ? "+" : ""}{typeof value === "number" && !Number.isInteger(value)
        ? value.toFixed(1) : value}
    </span>
  );
}

function fmtDate(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

export function ComparePage({ preselectedA, onBack }: Props) {
  const [runs, setRuns]       = useState<RunSummary[]>([]);
  const [runA, setRunA]       = useState(preselectedA ?? "");
  const [runB, setRunB]       = useState("");
  const [result, setResult]   = useState<CompareResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState("");

  useEffect(() => {
    listRuns()
      .then((all: RunSummary[]) => setRuns(all.filter((r) => r.status === "done")))
      .catch(() => {});
  }, []);

  const handleCompare = async () => {
    if (!runA || !runB) { setError("Select both runs."); return; }
    if (runA === runB)  { setError("Select two different runs."); return; }
    setError("");
    setLoading(true);
    try {
      setResult(await compareRuns(runA, runB));
    } catch (e: any) {
      setError(e.message || "Compare failed.");
    } finally {
      setLoading(false);
    }
  };

  const labelA = result ? `#${result.run_a.run_id}` : "Run A";
  const labelB = result ? `#${result.run_b.run_id}` : "Run B";

  const METRICS: { key: keyof MetricsRow; label: string; lowerIsBetter: boolean; unit: string }[] = [
    { key: "total_requests",      label: "Total requests",  lowerIsBetter: false, unit: ""   },
    { key: "successful_requests", label: "Success",         lowerIsBetter: false, unit: ""   },
    { key: "failed_requests",     label: "Failed",          lowerIsBetter: true,  unit: ""   },
    { key: "avg_latency_ms",      label: "Avg latency",     lowerIsBetter: true,  unit: "ms" },
    { key: "p50_latency_ms",      label: "P50",             lowerIsBetter: true,  unit: "ms" },
    { key: "p95_latency_ms",      label: "P95",             lowerIsBetter: true,  unit: "ms" },
    { key: "p99_latency_ms",      label: "P99",             lowerIsBetter: true,  unit: "ms" },
    { key: "requests_per_second", label: "RPS",             lowerIsBetter: false, unit: ""   },
    { key: "execution_time_s",    label: "Execution time",  lowerIsBetter: true,  unit: "s"  },
  ];

  return (
    <div className="max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <button onClick={onBack}
          className="flex items-center gap-1.5 text-gray-400 hover:text-white text-sm transition-colors">
          <ArrowLeft size={16} /> Back
        </button>
        <div className="flex-1">
          <h1 className="text-2xl font-semibold text-white">Compare runs</h1>
          <p className="text-gray-500 text-sm mt-0.5">Side-by-side metrics with delta indicators</p>
        </div>
        <ArrowLeftRight size={20} className="text-gray-600" />
      </div>

      {/* Run selectors */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        {[
          { label: "Run A (baseline)", value: runA, set: setRunA },
          { label: "Run B (compare)",  value: runB, set: setRunB },
        ].map(({ label, value, set }) => (
          <div key={label}>
            <p className="text-xs text-gray-500 mb-1.5">{label}</p>
            <select
              value={value}
              onChange={(e) => set(e.target.value)}
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2.5
                text-sm text-white focus:outline-none focus:border-brand-500 transition-colors"
            >
              <option value="">— select a run —</option>
              {runs.map((r) => (
                <option key={r.run_id} value={r.run_id}>
                  #{r.run_id} · {r.filename} · {fmtDate(r.started_at)}
                </option>
              ))}
            </select>
          </div>
        ))}
      </div>

      {error && <p className="text-red-400 text-sm mb-3">{error}</p>}

      <button
        onClick={handleCompare}
        disabled={loading || !runA || !runB}
        className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-brand-600 hover:bg-brand-500
          disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium
          transition-colors mb-8"
      >
        <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
        {loading ? "Comparing…" : "Compare"}
      </button>

      {/* Results */}
      {result && (
        <>
          {/* Run metadata row */}
          <div className="grid grid-cols-2 gap-4 mb-6">
            {(
              [
                { meta: result.run_a, label: "Run A — baseline", border: "border-blue-800",  bg: "bg-blue-900/10"  },
                { meta: result.run_b, label: "Run B — compare",  border: "border-amber-800", bg: "bg-amber-900/10" },
              ] as const
            ).map(({ meta, label, border, bg }) => (
              <div key={meta.run_id} className={`rounded-lg border ${border} ${bg} px-4 py-3`}>
                <p className="text-xs text-gray-500 mb-1">{label}</p>
                <p className="text-white font-mono text-sm font-medium">#{meta.run_id}</p>
                <p className="text-gray-400 text-xs truncate">{meta.filename}</p>
                <p className="text-gray-600 text-xs">{fmtDate(meta.started_at)}</p>
              </div>
            ))}
          </div>

          {/* Chart */}
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-5 mb-6">
            <p className="text-sm font-medium text-gray-300 mb-4">
              Latency comparison —{" "}
              <span className="text-blue-400">{labelA}</span>
              {" vs "}
              <span className="text-amber-400">{labelB}</span>
            </p>
            <CompareChart pairs={result.pairs} labelA={labelA} labelB={labelB} />
          </div>

          {/* Per-test delta tables */}
          {result.pairs.map((pair, pi) => (
            <div key={pi} className="mb-6">
              <p className="text-sm font-medium text-gray-400 font-mono mb-3 truncate">
                {pair.test_name}
              </p>
              <div className="rounded-lg border border-gray-800 overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-900 text-gray-500 text-xs">
                      <th className="px-4 py-2.5 text-left font-medium">Metric</th>
                      <th className="px-4 py-2.5 text-right font-medium">
                        <span className="text-blue-400">{labelA}</span> (baseline)
                      </th>
                      <th className="px-4 py-2.5 text-right font-medium">
                        <span className="text-amber-400">{labelB}</span>
                      </th>
                      <th className="px-4 py-2.5 text-right font-medium">Delta</th>
                    </tr>
                  </thead>
                  <tbody>
                    {METRICS.map(({ key, label, lowerIsBetter, unit }) => {
                      const va = pair.run_a?.[key] as number | undefined;
                      const vb = pair.run_b?.[key] as number | undefined;
                      const d  = pair.delta?.[key] ?? null;
                      return (
                        <tr key={key} className="border-t border-gray-800 hover:bg-gray-900/40">
                          <td className="px-4 py-2.5 text-gray-400">{label}</td>
                          <td className="px-4 py-2.5 text-right font-mono text-gray-300">
                            {va !== undefined ? `${Number.isInteger(va) ? va : va.toFixed(1)}${unit ? " " + unit : ""}` : "—"}
                          </td>
                          <td className="px-4 py-2.5 text-right font-mono text-gray-300">
                            {vb !== undefined ? `${Number.isInteger(vb) ? vb : vb.toFixed(1)}${unit ? " " + unit : ""}` : "—"}
                          </td>
                          <td className="px-4 py-2.5 text-right">
                            <Delta value={d} lowerIsBetter={lowerIsBetter} />
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
        </>
      )}
    </div>
  );
}
