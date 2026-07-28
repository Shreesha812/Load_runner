interface Props {
  label: string;
  value: string | number;
  sub?: string;
  highlight?: boolean;
}

export function MetricCard({ label, value, sub, highlight }: Props) {
  return (
    <div className={`rounded-lg p-4 ${highlight ? "bg-brand-900/60 border border-brand-700" : "bg-gray-900 border border-gray-800"}`}>
      <p className="text-xs text-gray-400 uppercase tracking-wider mb-1">{label}</p>
      <p className={`text-2xl font-semibold font-mono ${highlight ? "text-brand-400" : "text-white"}`}>
        {value}
      </p>
      {sub && <p className="text-xs text-gray-500 mt-1">{sub}</p>}
    </div>
  );
}
