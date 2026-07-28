import type { TestResult } from "../types";

function fmt(n: number, unit = "ms") {
  return `${n.toFixed(2)} ${unit}`;
}

export function MetricsTable({ results }: { results: TestResult[] }) {
  if (!results.length) return null;

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-800">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-gray-900 text-gray-400 text-left">
            <th className="px-4 py-3 font-medium">Test</th>
            <th className="px-4 py-3 font-medium text-right">Total</th>
            <th className="px-4 py-3 font-medium text-right">Pass</th>
            <th className="px-4 py-3 font-medium text-right">Fail</th>
            <th className="px-4 py-3 font-medium text-right">Avg</th>
            <th className="px-4 py-3 font-medium text-right">P50</th>
            <th className="px-4 py-3 font-medium text-right">P95</th>
            <th className="px-4 py-3 font-medium text-right">P99</th>
            <th className="px-4 py-3 font-medium text-right">RPS</th>
            <th className="px-4 py-3 font-medium text-right">Time</th>
          </tr>
        </thead>
        <tbody>
          {results.map((r, i) => {
            const m = r.metrics;
            const failRate = m.total_requests > 0 ? m.failed_requests / m.total_requests : 0;
            return (
              <tr key={i} className="border-t border-gray-800 hover:bg-gray-900/50 transition-colors">
                <td className="px-4 py-3 text-gray-300 max-w-xs truncate font-mono text-xs">
                  {r.test_name}
                </td>
                <td className="px-4 py-3 text-right font-mono text-white">{m.total_requests}</td>
                <td className="px-4 py-3 text-right font-mono text-green-400">{m.successful_requests}</td>
                <td className={`px-4 py-3 text-right font-mono ${failRate > 0 ? "text-red-400" : "text-gray-500"}`}>
                  {m.failed_requests}
                </td>
                <td className="px-4 py-3 text-right font-mono text-gray-300">{fmt(m.avg_latency_ms)}</td>
                <td className="px-4 py-3 text-right font-mono text-gray-300">{fmt(m.p50_latency_ms)}</td>
                <td className="px-4 py-3 text-right font-mono text-yellow-400">{fmt(m.p95_latency_ms)}</td>
                <td className="px-4 py-3 text-right font-mono text-orange-400">{fmt(m.p99_latency_ms)}</td>
                <td className="px-4 py-3 text-right font-mono text-brand-400">{m.requests_per_second.toFixed(1)}</td>
                <td className="px-4 py-3 text-right font-mono text-gray-400">{m.execution_time_s.toFixed(2)}s</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
