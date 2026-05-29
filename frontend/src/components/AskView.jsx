import { useState } from "react";
import { askQuestion } from "../api/client.js";

const SUGGESTIONS = [
  "Which program has the lowest attendance?",
  "How many participants are in the mock dataset?",
  "What are the main negative feedback themes?",
  "What is the average attendance?",
];

export default function AskView() {
  const [question, setQuestion] = useState("");
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function submit(e) {
    e.preventDefault();
    const q = question.trim();
    if (!q || loading) return;
    setLoading(true);
    setError(null);
    try {
      const result = await askQuestion(q);
      setHistory((h) => [...h, result]);
      setQuestion("");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="card">
        <h2 className="text-lg font-semibold">Ask the data</h2>
        <p className="mt-1 text-sm text-slate-600">
          Plain-English Q&A from the Lifechanger dataset. Works without an API key using local
          analytics; set <code className="text-xs">HF_TOKEN</code> in{" "}
          <code className="text-xs">backend/.env</code> for Gemma answers. To{" "}
          <strong>generate charts</strong>, use the <strong>Dashboard</strong> tab copilot.
        </p>
        <form onSubmit={submit} className="mt-4 flex flex-col gap-3 sm:flex-row">
          <input
            className="input flex-1"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="e.g. Which cohort is at risk?"
          />
          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? "Thinking…" : "Ask"}
          </button>
        </form>
        <div className="mt-3 flex flex-wrap gap-2">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              type="button"
              className="btn-secondary text-xs"
              onClick={() => setQuestion(s)}
            >
              {s}
            </button>
          ))}
        </div>
        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
      </div>

      <div className="space-y-4">
        {history.map((item, i) => (
          <div key={i} className="card">
            <p className="text-sm font-medium text-brand-700">Q: {item.question}</p>
            {item.source && (
              <p className="mt-1 text-xs text-slate-500">
                via {item.source === "local" ? "local analytics" : "LLM"}
              </p>
            )}
            <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed">{item.answer}</p>
            {item.citations?.length > 0 && (
              <p className="mt-2 text-xs text-slate-500">{item.citations[0]}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
