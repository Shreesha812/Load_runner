import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from "recharts";
import type { TestResult } from "../types";

const COLORS = { Avg: "#6b7280", P50: "#3b82f6", P95: "#f59e0b", P99: "#f97316" };

export function LatencyChart({ results }: { results: TestResult[] }) {
  if (!results.length) return null;

  const data = results.map((r) => ({
    name: r.test_name.replace(/^Test \d+: /, "").slice(0, 32),
    Avg: parseFloat(r.metrics.avg_latency_ms.toFixed(1)),
    P50: parseFloat(r.metrics.p50_latency_ms.toFixed(1)),
    P95: parseFloat(r.metrics.p95_latency_ms.toFixed(1)),
    P99: parseFloat(r.metrics.p99_latency_ms.toFixed(1)),
  }));

  return (
    <div>
      <div className="flex gap-4 mb-4 text-xs">
        {Object.entries(COLORS).map(([k, c]) => (
          <span key={k} className="flex items-center gap-1.5 text-gray-400">
            <span className="w-2.5 h-2.5 rounded-sm inline-block" style={{ background: c }} />
            {k}
          </span>
        ))}
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} barCategoryGap="20%">
          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
          <XAxis dataKey="name" tick={{ fill: "#6b7280", fontSize: 11 }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fill: "#6b7280", fontSize: 11 }} axisLine={false} tickLine={false}
            tickFormatter={(v) => `${v}ms`} />
          <Tooltip
            contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 8, fontSize: 12 }}
            labelStyle={{ color: "#e5e7eb" }}
            itemStyle={{ color: "#9ca3af" }}
          formatter={(v: unknown) => [`${v} ms`]}
          />
          {Object.entries(COLORS).map(([k, c]) => (
            <Bar key={k} dataKey={k} fill={c} radius={[3, 3, 0, 0]} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
