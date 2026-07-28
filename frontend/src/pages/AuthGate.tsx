import { useState } from "react";
import { Zap, KeyRound } from "lucide-react";

interface Props {
  onAuthenticated: () => void;
}

export function AuthGate({ onAuthenticated }: Props) {
  const [key, setKey]       = useState("");
  const [error, setError]   = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!key.trim()) { setError("API key cannot be empty."); return; }
    setLoading(true);
    setError("");
    try {
      const res = await fetch("http://localhost:8000/api/runs", {
        headers: { "X-Api-Key": key.trim() },
      });
      if (res.status === 401) {
        setError("Invalid API key. Check your .env file.");
      } else if (!res.ok) {
        setError(`Server returned ${res.status}.`);
      } else {
        localStorage.setItem("wolken_api_key", key.trim());
        onAuthenticated();
      }
    } catch {
      setError("Cannot reach the server. Is the backend running on port 8000?");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950">
      <div className="w-full max-w-sm px-4">
        <div className="flex items-center justify-center gap-2 mb-8">
          <Zap size={22} className="text-brand-500" />
          <span className="text-xl font-semibold text-white">WolkenLoadRunner</span>
        </div>

        <form
          onSubmit={handleSubmit}
          className="bg-gray-900 border border-gray-800 rounded-xl p-6 space-y-4"
        >
          <div className="flex items-center gap-2 mb-1">
            <KeyRound size={15} className="text-gray-400" />
            <h2 className="text-sm font-medium text-gray-300">Enter your API key</h2>
          </div>

          <input
            type="password"
            value={key}
            onChange={(e) => setKey(e.target.value)}
            placeholder="wolken-dev-key-…"
            autoFocus
            className="w-full bg-gray-950 border border-gray-700 rounded-lg px-3 py-2.5
              text-sm text-white placeholder-gray-600 font-mono
              focus:outline-none focus:border-brand-500 transition-colors"
          />

          {error && <p className="text-red-400 text-xs">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 rounded-lg bg-brand-600 hover:bg-brand-500
              disabled:opacity-40 disabled:cursor-not-allowed
              text-white text-sm font-medium transition-colors"
          >
            {loading ? "Verifying…" : "Continue"}
          </button>

          <p className="text-xs text-gray-600 text-center pt-1">
            Key is stored in browser localStorage only.
          </p>
        </form>
      </div>
    </div>
  );
}
