import type { RunStatus } from "../types";

const styles: Record<RunStatus, string> = {
  pending: "bg-gray-800 text-gray-400",
  running: "bg-yellow-900/50 text-yellow-400 animate-pulse",
  done:    "bg-green-900/50 text-green-400",
  error:   "bg-red-900/50 text-red-400",
};

export function StatusBadge({ status }: { status: RunStatus }) {
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${styles[status]}`}>
      {status}
    </span>
  );
}
