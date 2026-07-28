import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from "recharts";

interface Point { t: number; rps: number; avg: number }

export function LiveChart({ points }: { points: Point[] }) {
  return (
    <ResponsiveContainer width="100%" height={160}>
      <LineChart data={points} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
        <XAxis dataKey="t" hide />
        <YAxis yAxisId="rps" orientation="left" tick={{ fill: "#6b7280", fontSize: 10 }}
          axisLine={false} tickLine={false} tickFormatter={(v) => `${v} rps`} width={52} />
        <YAxis yAxisId="lat" orientation="right" tick={{ fill: "#6b7280", fontSize: 10 }}
          axisLine={false} tickLine={false} tickFormatter={(v) => `${v}ms`} width={48} />
        <Tooltip
          contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 8, fontSize: 11 }}
          formatter={(v: unknown, name: unknown) =>
            name === "rps" ? [`${Number(v).toFixed(1)} req/s`, "RPS"] : [`${Number(v).toFixed(0)} ms`, "Avg Latency"]
          }
        />
        <Line yAxisId="rps" type="monotone" dataKey="rps" stroke="#3b82f6"
          dot={false} strokeWidth={2} isAnimationActive={false} />
        <Line yAxisId="lat" type="monotone" dataKey="avg" stroke="#f59e0b"
          dot={false} strokeWidth={2} isAnimationActive={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}
