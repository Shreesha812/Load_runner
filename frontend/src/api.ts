const BASE = "http://localhost:8000/api";
export const WS_BASE = "ws://localhost:8000/api";

export async function startRun(
  file: File,
  opts: { timeout: number; connect_timeout: number; pool_size: number }
): Promise<{ run_id: string }> {
  const form = new FormData();
  form.append("file", file);
  const url = new URL(`${BASE}/run`);
  url.searchParams.set("timeout", String(opts.timeout));
  url.searchParams.set("connect_timeout", String(opts.connect_timeout));
  url.searchParams.set("pool_size", String(opts.pool_size));
  const res = await fetch(url.toString(), { method: "POST", body: form });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function cancelRun(runId: string): Promise<void> {
  const res = await fetch(`${BASE}/run/${runId}`, { method: "DELETE" });
  if (!res.ok) throw new Error(await res.text());
}

export async function getRun(runId: string) {
  const res = await fetch(`${BASE}/run/${runId}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function listRuns() {
  const res = await fetch(`${BASE}/runs`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export const downloadJson = (runId: string) =>
  window.open(`${BASE}/results/${runId}/json`, "_blank");

export const downloadCsv = (runId: string) =>
  window.open(`${BASE}/results/${runId}/csv`, "_blank");

export async function compareRuns(runA: string, runB: string) {
  const res = await fetch(`${BASE}/compare?run_a=${runA}&run_b=${runB}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getOverrides(runId: string) {
  const res = await fetch(`${BASE}/run/${runId}/overrides`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function toggleTest(runId: string, testIdx: number, enabled: boolean) {
  const res = await fetch(
    `${BASE}/run/${runId}/toggle?test_idx=${testIdx}&enabled=${enabled}`,
    { method: "PATCH" }
  );
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
