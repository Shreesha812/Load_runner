import { useEffect, useState } from "react";
import { Clock, ChevronRight, RefreshCw, ArrowLeftRight, ChevronDown, ChevronUp } from "lucide-react";
import { listRuns, getOverrides, toggleTest } from "../api";
import type { RunSummary, TestOverride } from "../types";
import { StatusBadge } from "../components/StatusBadge";

interface Props {
  onSelect:  (run: RunSummary) => void;
  onCompare: (runId: string)   => void;
}

// Inline toggle switch component
function Toggle({ enabled, onChange }: { enabled: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      onClick={() => onChange(!enabled)}
      className={`relative inline-flex h-5 w-9 shrink-0 items-center rounded-full
        transition-colors duration-200 focus:outline-none
        ${enabled ? "bg-brand-600" : "bg-gray-700"}`}
    >
      <span
        className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow
          transition-transform duration-200
          ${enabled ? "translate-x-4.5" : "translate-x-0.5"}`}
      />
    </button>
  );
}

// Per-run test override panel
function TestOverrides({ runId }: { runId: string }) {
  const [overrides, setOverrides] = useState<TestOverride[]>([]);
  const [loading, setLoading]     = useState(true);
  const [saving, setSaving]       = useState<number | null>(null);

  useEffect(() => {
    getOverrides(runId)
      .then(setOverrides)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [runId]);

  const handleToggle = async (idx: number, enabled: boolean) => {
    setSaving(idx);
    try {
      await toggleTest(runId, idx, enabled);
      setOverrides((prev) =>
        prev.map((o) => (o.test_idx === idx ? { ...o, enabled } : o))
      );
    } catch { /* ignore */ }
    finally { setSaving(null); }
  };

  if (loading) {
    return <p className="px-4 pb-3 text-xs text-gray-600">Loading…</p>;
  }
  if (!overrides.length) {
    return <p className="px-4 pb-3 text-xs text-gray-600">No test definitions found.</p>;
  }

  return (
    <div className="border-t border-gray-800 divide-y divide-gray-800/60">
      {overrides.map((o) => (
        <div key={o.test_idx}
          className="flex items-center justify-between px-4 py-2.5 hover:bg-gray-900/30">
          <span className={`text-xs font-mono truncate max-w-xs
            ${o.enabled ? "text-gray-300" : "text-gray-600 line-through"}`}>
            {o.test_name.replace(/^Test \d+: /, "")}
          </span>
          <div className="flex items-center gap-2.5 shrink-0 ml-4">
            <span className={`text-xs ${o.enabled ? "text-green-500" : "text-gray-600"}`}>
              {saving === o.test_idx ? "Saving…" : o.enabled ? "Enabled" : "Disabled"}
            </span>
            <Toggle
              enabled={o.enabled}
              onChange={(v) => handleToggle(o.test_idx, v)}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

export function HistoryPage({ onSelect, onCompare }: Props) {
  const [runs, setRuns]           = useState<RunSummary[]>([]);
  const [loading, setLoading]     = useState(true);
  const [expanded, setExpanded]   = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try { setRuns(await listRuns()); }
    catch { /* ignore */ }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const fmtDate = (iso: string) =>
    new Date(iso).toLocaleString(undefined, {
      month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
    });

  const totalReqs = (run: RunSummary) =>
    run.results.reduce((s, r) => s + r.metrics.total_requests, 0);

  const successRate = (run: RunSummary) => {
    const total = run.results.reduce((s, r) => s + r.metrics.total_requests, 0);
    const ok    = run.results.reduce((s, r) => s + r.metrics.successful_requests, 0);
    return total > 0 ? ((ok / total) * 100).toFixed(1) + "%" : "—";
  };

  const toggleExpand = (runId: string) =>
    setExpanded((prev) => (prev === runId ? null : runId));

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

      {loading && <div className="text-center py-16 text-gray-600">Loading…</div>}

      {!loading && runs.length === 0 && (
        <div className="text-center py-16">
          <Clock className="mx-auto text-gray-700 mb-3" size={40} />
          <p className="text-gray-500">No runs yet — start one from the Upload tab.</p>
        </div>
      )}

      {!loading && runs.length > 0 && (
        <div className="space-y-2">
          {runs.map((run) => (
            <div key={run.run_id}
              className="rounded-lg border border-gray-800 bg-gray-900/40
                hover:border-gray-700 transition-colors">

              {/* Main row */}
              <div className="flex items-center p-4 gap-3">
                {/* Clickable area — opens results */}
                <button
                  onClick={() => onSelect(run)}
                  disabled={run.status === "running" || run.status === "pending"}
                  className="flex-1 flex items-center gap-3 min-w-0 text-left
                    disabled:opacity-50 disabled:cursor-default group"
                >
                  <StatusBadge status={run.status} />
                  <span className="text-white font-medium truncate">{run.filename}</span>
                  <span className="text-gray-600 font-mono text-xs shrink-0">#{run.run_id}</span>
                  <ChevronRight size={16}
                    className="text-gray-600 group-hover:text-gray-400 shrink-0 ml-auto transition-colors" />
                </button>

                {/* Compare button */}
                {run.status === "done" && (
                  <button
                    onClick={(e) => { e.stopPropagation(); onCompare(run.run_id); }}
                    className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md border border-gray-700
                      hover:border-brand-600 hover:bg-brand-900/20 text-gray-500 hover:text-brand-400
                      text-xs transition-colors shrink-0 ml-1">
                    <ArrowLeftRight size={12} /> Compare
                  </button>
                )}

                {/* Toggle expand — only for done runs with results */}
                {run.status === "done" && run.results.length > 0 && (
                  <button
                    onClick={() => toggleExpand(run.run_id)}
                    className="flex items-center gap-1 px-2.5 py-1.5 rounded-md border border-gray-700
                      hover:border-gray-600 text-gray-500 hover:text-gray-300
                      text-xs transition-colors shrink-0 ml-1">
                    {expanded === run.run_id
                      ? <><ChevronUp size={12} /> Tests</>
                      : <><ChevronDown size={12} /> Tests</>}
                  </button>
                )}
              </div>

              {/* Meta row */}
              <div className="px-4 pb-3 flex flex-wrap gap-x-6 gap-y-1 text-xs text-gray-500">
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

              {/* Expandable test toggle panel */}
              {expanded === run.run_id && (
                <TestOverrides runId={run.run_id} />
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
