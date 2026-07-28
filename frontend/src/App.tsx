import { useState } from "react";
import { UploadCloud, History, Zap } from "lucide-react";
import { UploadPage } from "./pages/Upload";
import { LivePage } from "./pages/Live";
import { ResultsPage } from "./pages/Results";
import { HistoryPage } from "./pages/History";
import type { RunSummary, TestResult } from "./types";

type View = "upload" | "live" | "results" | "history";

export default function App() {
  const [view, setView]       = useState<View>("upload");
  const [runId, setRunId]     = useState("");
  const [results, setResults] = useState<TestResult[]>([]);

  const handleRunStarted = (id: string) => { setRunId(id); setResults([]); setView("live"); };
  const handleDone       = (r: TestResult[]) => { setResults(r); setView("results"); };
  const handleHistorySelect = (run: RunSummary) => {
    setRunId(run.run_id); setResults(run.results); setView("results");
  };

  const nav = [
    { id: "upload",  label: "New Run", icon: UploadCloud },
    { id: "history", label: "History", icon: History },
  ] as const;

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-gray-800 bg-gray-950/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-6 flex items-center justify-between h-14">
          <div className="flex items-center gap-2.5">
            <Zap size={18} className="text-brand-500" />
            <span className="font-semibold text-white">WolkenLoadRunner</span>
            <span className="text-xs text-gray-600 ml-1">v2</span>
          </div>
          <nav className="flex items-center gap-1">
            {nav.map(({ id, label, icon: Icon }) => (
              <button key={id} onClick={() => setView(id as View)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm transition-colors
                  ${view === id || (view === "results" && id === "history")
                    ? "bg-gray-800 text-white"
                    : "text-gray-400 hover:text-gray-200 hover:bg-gray-900"}`}>
                <Icon size={15} />{label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      <main className="flex-1 max-w-5xl mx-auto w-full px-6 py-10">
        {view === "upload"  && <UploadPage onRunStarted={handleRunStarted} />}
        {view === "live"    && <LivePage runId={runId} onDone={handleDone} />}
        {view === "results" && <ResultsPage runId={runId} results={results} onBack={() => setView("history")} />}
        {view === "history" && <HistoryPage onSelect={handleHistorySelect} />}
      </main>
    </div>
  );
}
