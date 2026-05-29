import { useEffect, useState } from "react";
import { fetchLangchainStatus } from "./api/client.js";
import DashboardView from "./components/DashboardView.jsx";
import AnalyzeView from "./components/AnalyzeView.jsx";
import AskView from "./components/AskView.jsx";
import ReportView from "./components/ReportView.jsx";
import StoryView from "./components/StoryView.jsx";

const TABS = [
  { id: "dashboard", label: "Dashboard" },
  { id: "analyze", label: "Analyse Data" },
  { id: "ask", label: "Ask Questions" },
  { id: "report", label: "Generate Report" },
  { id: "story", label: "Impact Story" },
];

export default function App() {
  const [tab, setTab] = useState("dashboard");
  const [llmStatus, setLlmStatus] = useState(null);

  useEffect(() => {
    fetchLangchainStatus()
      .then(setLlmStatus)
      .catch(() => setLlmStatus({ llm_configured: false, mode: "offline" }));
  }, []);

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-6 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-brand-600">
              Lifechanger
            </p>
            <h1 className="text-2xl font-bold text-slate-900">ImpactLens AI</h1>
            <p className="text-sm text-slate-600">
              Interactive dashboard + LangChain-style copilot — mock data only
            </p>
            {llmStatus && (
              <p className="mt-1 text-xs text-slate-500">
                LLM:{" "}
                <span
                  className={
                    llmStatus.llm_configured ? "font-medium text-emerald-700" : "text-amber-700"
                  }
                >
                  {llmStatus.llm_configured ? llmStatus.model : "local fallback (set HF_TOKEN)"}
                </span>
              </p>
            )}
          </div>
          <nav className="flex flex-wrap gap-2">
            {TABS.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => setTab(t.id)}
                className={`rounded-lg px-3 py-1.5 text-sm font-medium transition ${
                  tab === t.id
                    ? "bg-brand-600 text-white"
                    : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                }`}
              >
                {t.label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8">
        {tab === "dashboard" && <DashboardView />}
        {tab === "analyze" && <AnalyzeView />}
        {tab === "ask" && <AskView />}
        {tab === "report" && <ReportView />}
        {tab === "story" && <StoryView />}
      </main>
    </div>
  );
}
