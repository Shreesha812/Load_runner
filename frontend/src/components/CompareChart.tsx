import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend,
} from "recharts";

interface MetricsRow {
  avg_latency_ms: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
}

interface Pair {
  test_name: string;
  run_a: MetricsRow | null;
  run_b: MetricsRow | null;
}

interface Props {
  pairs: Pair[];
  labelA: string;
  labelB: string;
}

const COLORS = { a: "#3b82f6", b: "#f59e0b" };

export function CompareChart({ pairs, labelA, labelB }: Props) {
  // One data point per latency metric, each bar = one run
  const metrics: { key: keyof MetricsRow; label: string }[] = [
    { key: "avg_latency_ms", label: "Avg" },
    { key: "p50_latency_ms", label: "P50" },
    { key: "p95_latency_ms", label: "P95" },
    { key: "p99_latency_ms", label: "P99" },
  ];

  // Flatten: one row per (test × metric)
  const data = pairs.flatMap((pair) =>
    metrics.map(({ key, label }) => ({
      name: pairs.length > 1
        ? `${pair.test_name.replace(/^Test \d+: /, "").slice(0, 18)} · ${label}`
        : label,
      [labelA]: pair.run_a ? parseFloat(pair.run_a[key].toFixed(1)) : 0,
      [labelB]: pair.run_b ? parseFloat(pair.run_b[key].toFixed(1)) : 0,
    }))
  );

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} barCategoryGap="25%" barGap={3}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
        <XAxis
          dataKey="name"
          tick={{ fill: "#6b7280", fontSize: 10 }}
          axisLine={false}
          tickLine={false}
          interval={0}
        />
        <YAxis
          tick={{ fill: "#6b7280", fontSize: 10 }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v) => `${v}ms`}
        />
        <Tooltip
          contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 8, fontSize: 12 }}
          formatter={(v: unknown) => [`${v} ms`]}
          labelStyle={{ color: "#e5e7eb" }}
        />
        <Legend
          verticalAlign="top"
          align="right"
          iconType="square"
          iconSize={10}
          wrapperStyle={{ fontSize: 11, color: "#9ca3af", paddingBottom: 6 }}
        />
        <Bar dataKey={labelA} fill={COLORS.a} radius={[3, 3, 0, 0]} maxBarSize={28} />
        <Bar dataKey={labelB} fill={COLORS.b} radius={[3, 3, 0, 0]} maxBarSize={28} />
      </BarChart>
    </ResponsiveContainer>
  );
}
