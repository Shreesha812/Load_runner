import { useEffect, useState } from "react";
import { Clock, ChevronRight, RefreshCw } from "lucide-react";
import { listRuns } from "../api";
import type { RunSummary } from "../types";
import { StatusBadge } from "../components/StatusBadge";

interface Props {
  onSelect: (run: RunSummary) => void;
}

export function HistoryPage({ onSelect }: Props) {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try { setRuns(await listRuns()); }
    catch { /* ignore */ }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const fmtDate = (iso: string) => {
    const d = new Date(iso);
    return d.toLocaleString(undefined, { month: "short", day: "numeric",
      hour: "2-digit", minute: "2-digit" });
  };

  const totalReqs = (run: RunSummary) =>
    run.results.reduce((s, r) => s + r.metrics.total_requests, 0);

  const successRate = (run: RunSummary) => {
    const total = run.results.reduce((s, r) => s + r.metrics.total_requests, 0);
    const ok = run.results.reduce((s, r) => s + r.metrics.successful_requests, 0);
    return total > 0 ? ((ok / total) * 100).toFixed(1) + "%" : "—";
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-white">History</h1>
          <p className="text-gray-400 text-sm mt-0.5">All past test runs</p>
        </div>
        <button onClick={load}
          className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-gray-700
            hover:border-gray-600 text-gray-400 hover:text-white text-sm transition-colors">
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} /> Refresh
        </button>
      </div>

      {loading && (
        <div className="text-center py-16 text-gray-600">Loading…</div>
      )}

      {!loading && runs.length === 0 && (
        <div className="text-center py-16">
          <Clock className="mx-auto text-gray-700 mb-3" size={40} />
          <p className="text-gray-500">No runs yet — start one from the Upload tab.</p>
        </div>
      )}

      {!loading && runs.length > 0 && (
        <div className="space-y-2">
          {runs.map((run) => (
            <button
              key={run.run_id}
              onClick={() => onSelect(run)}
              disabled={run.status === "running" || run.status === "pending"}
              className="w-full text-left rounded-lg border border-gray-800 bg-gray-900/40 p-4
                hover:border-gray-700 hover:bg-gray-900/70 disabled:opacity-50 disabled:cursor-default
                transition-all group"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3 min-w-0">
                  <StatusBadge status={run.status} />
                  <span className="text-white font-medium truncate">{run.filename}</span>
                  <span className="text-gray-600 font-mono text-xs shrink-0">#{run.run_id}</span>
                </div>
                <ChevronRight size={16} className="text-gray-600 group-hover:text-gray-400 shrink-0 ml-2 transition-colors" />
              </div>
              <div className="mt-2 flex flex-wrap gap-x-6 gap-y-1 text-xs text-gray-500">
                <span>{fmtDate(run.started_at)}</span>
                {run.results.length > 0 && (
                  <>
                    <span>{run.results.length} test{run.results.length !== 1 ? "s" : ""}</span>
                    <span>{totalReqs(run)} requests</span>
                    <span className="text-green-500">{successRate(run)} success</span>
                  </>
                )}
                {run.error && (
                  <span className="text-red-400 truncate max-w-xs">{run.error}</span>
                )}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
