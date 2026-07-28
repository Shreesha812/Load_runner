import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend,
} from "recharts";

interface Point { t: number; rps: number; avg: number; workers: number }

interface Props {
  points: Point[];
  totalWorkers: number;   // max concurrency — used to scale the workers axis
  isRamping: boolean;     // show workers line only when ramp-up is configured
}

export function LiveChart({ points, totalWorkers, isRamping }: Props) {
  return (
    <ResponsiveContainer width="100%" height={180}>
      <LineChart data={points} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
        <XAxis dataKey="t" hide />

        {/* Left axis — RPS */}
        <YAxis
          yAxisId="rps"
          orientation="left"
          tick={{ fill: "#6b7280", fontSize: 10 }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v) => `${v} rps`}
          width={52}
        />

        {/* Right axis — latency ms */}
        <YAxis
          yAxisId="lat"
          orientation="right"
          tick={{ fill: "#6b7280", fontSize: 10 }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v) => `${v}ms`}
          width={48}
        />

        {/* Second right axis — active workers (only rendered when ramping) */}
        {isRamping && (
          <YAxis
            yAxisId="workers"
            orientation="right"
            domain={[0, totalWorkers]}
            tick={{ fill: "#6b7280", fontSize: 10 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v) => `${v}w`}
            width={36}
          />
        )}

        <Tooltip
          contentStyle={{
            background: "#111827",
            border: "1px solid #374151",
            borderRadius: 8,
            fontSize: 11,
          }}
          formatter={(v: unknown, name: unknown) => {
            if (name === "rps")     return [`${Number(v).toFixed(1)} req/s`, "RPS"];
            if (name === "avg")     return [`${Number(v).toFixed(0)} ms`,    "Avg Latency"];
            if (name === "workers") return [`${Number(v)} / ${totalWorkers}`, "Workers"];
            return [`${v}`, String(name)];
          }}
        />

        <Legend
          verticalAlign="top"
          align="right"
          iconType="plainline"
          iconSize={12}
          wrapperStyle={{ fontSize: 11, color: "#9ca3af", paddingBottom: 4 }}
          formatter={(value) => {
            if (value === "rps")     return <span style={{ color: "#3b82f6" }}>RPS</span>;
            if (value === "avg")     return <span style={{ color: "#f59e0b" }}>Avg latency</span>;
            if (value === "workers") return <span style={{ color: "#a78bfa" }}>Workers</span>;
            return value;
          }}
        />

        <Line
          yAxisId="rps"
          type="monotone"
          dataKey="rps"
          stroke="#3b82f6"
          dot={false}
          strokeWidth={2}
          isAnimationActive={false}
        />

        <Line
          yAxisId="lat"
          type="monotone"
          dataKey="avg"
          stroke="#f59e0b"
          dot={false}
          strokeWidth={2}
          isAnimationActive={false}
        />

        {isRamping && (
          <Line
            yAxisId="workers"
            type="stepAfter"
            dataKey="workers"
            stroke="#a78bfa"
            dot={false}
            strokeWidth={2}
            strokeDasharray="4 2"
            isAnimationActive={false}
          />
        )}
      </LineChart>
    </ResponsiveContainer>
  );
}
