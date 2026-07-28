import { useState, useRef, DragEvent } from "react";
import { Upload as UploadIcon, FileSpreadsheet, ChevronDown, ChevronUp } from "lucide-react";
import { startRun } from "../api";

interface Props {
  onRunStarted: (runId: string) => void;
}

export function UploadPage({ onRunStarted }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [opts, setOpts] = useState({ timeout: 30, connect_timeout: 10, pool_size: 100 });
  const inputRef = useRef<HTMLInputElement>(null);

  const accept = (f: File) => {
    if (!f.name.endsWith(".xlsx")) { setError("Only .xlsx files are supported."); return; }
    setFile(f); setError("");
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault(); setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) accept(f);
  };

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) accept(f);
  };

  const handleRun = async () => {
    if (!file) return;
    setLoading(true); setError("");
    try {
      const { run_id } = await startRun(file, opts);
      onRunStarted(run_id);
    } catch (e: any) {
      setError(e.message || "Failed to start run.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-semibold text-white mb-1">New Test Run</h1>
      <p className="text-gray-400 text-sm mb-8">Upload an Excel file and configure run parameters.</p>

      {/* Drop zone */}
      <div
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={`
          relative flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed
          p-12 cursor-pointer transition-all
          ${dragging ? "border-brand-500 bg-brand-900/20" : "border-gray-700 hover:border-gray-600 bg-gray-900/40"}
        `}
      >
        <input ref={inputRef} type="file" accept=".xlsx" className="hidden" onChange={onFileChange} />
        {file ? (
          <>
            <FileSpreadsheet className="text-green-400" size={40} />
            <p className="text-white font-medium">{file.name}</p>
            <p className="text-gray-400 text-sm">{(file.size / 1024).toFixed(1)} KB — click to change</p>
          </>
        ) : (
          <>
            <UploadIcon className="text-gray-500" size={40} />
            <p className="text-gray-300 font-medium">Drop your Excel file here</p>
            <p className="text-gray-500 text-sm">or click to browse — .xlsx only</p>
          </>
        )}
      </div>

      {/* Advanced settings */}
      <div className="mt-4 rounded-lg border border-gray-800 overflow-hidden">
        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="w-full flex items-center justify-between px-4 py-3 text-sm text-gray-400 hover:text-gray-300 hover:bg-gray-900/40 transition-colors"
        >
          <span>Advanced settings</span>
          {showAdvanced ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>
        {showAdvanced && (
          <div className="px-4 pb-4 grid grid-cols-3 gap-4 bg-gray-900/20">
            {[
              { key: "timeout",         label: "Request timeout",  unit: "s" },
              { key: "connect_timeout", label: "Connect timeout",  unit: "s" },
              { key: "pool_size",       label: "Connection pool",  unit: "conn" },
            ].map(({ key, label, unit }) => (
              <div key={key}>
                <label className="block text-xs text-gray-500 mb-1">{label}</label>
                <div className="flex items-center gap-1.5">
                  <input
                    type="number"
                    value={opts[key as keyof typeof opts]}
                    onChange={(e) => setOpts({ ...opts, [key]: Number(e.target.value) })}
                    className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1.5 text-sm text-white focus:outline-none focus:border-brand-500"
                  />
                  <span className="text-gray-500 text-xs shrink-0">{unit}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {error && <p className="mt-3 text-red-400 text-sm">{error}</p>}

      <button
        onClick={handleRun}
        disabled={!file || loading}
        className="mt-6 w-full py-3 rounded-lg bg-brand-600 hover:bg-brand-500 disabled:opacity-40 disabled:cursor-not-allowed
          text-white font-medium transition-colors text-sm"
      >
        {loading ? "Starting…" : "Run Load Test"}
      </button>

      {/* Format reminder */}
      <div className="mt-8 rounded-lg border border-gray-800 p-4 bg-gray-900/30">
        <p className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-3">Expected Excel columns</p>
        <div className="grid grid-cols-2 gap-x-8 gap-y-1.5 text-xs text-gray-500 font-mono">
          {[
            ["URL",                    "Target endpoint"],
            ["HTTP Method",            "GET / POST / PUT…"],
            ["Headers",                "Key: Value per line"],
            ["Request message Template","Body with <var>"],
            ["variable list Order",    "sequential / random"],
            ["List Of values",         "v1:a,b,c  or  v1:{a,b}"],
            ["variables",              "v1:fixed_value"],
            ["Total concurrent request","Number of workers"],
            ["Response Structure",     "id,name,status"],
            ["Enable",                 "Enable / Disable"],
          ].map(([col, desc]) => (
            <div key={col} className="flex gap-2">
              <span className="text-gray-300 shrink-0">{col}</span>
              <span className="text-gray-600">—</span>
              <span>{desc}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
