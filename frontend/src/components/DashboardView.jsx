import { useCallback, useEffect, useState } from "react";
import { fetchDashboardMetrics } from "../api/client.js";
import { orchestrateLLM } from "../lib/dashboardOrchestrator.js";
import { applyStatefulMutations } from "../lib/statefulMutations.js";
import DashboardCanvas from "./DashboardCanvas.jsx";

const SUGGESTIONS = [
  "Add a bar chart of attendance by program",
  "Add a pie chart of feedback sentiment",
  "Add a line chart of quarterly attendance trend",
  "Which program has the lowest attendance?",
  "Change the last chart to a pie chart",
  "Clear all widgets",
];

function buildStarterWidgets(metrics) {
  const programs = (metrics?.programs || []).slice(0, 8);
  return [
    {
      id: "widget-starter-attendance",
      type: "bar-chart",
      title: "Attendance by program",
      labels: programs.map((p) => p.name.slice(0, 24)),
      values: programs.map((p) => Math.round((p.attendance_rate || 0) * 100)),
    },
    {
      id: "widget-starter-kpi",
      type: "kpi-card",
      title: "Average attendance",
      value: `${Math.round((metrics?.summary?.avg_attendance || 0) * 100)}%`,
    },
  ];
}

export default function DashboardView() {
  const [metrics, setMetrics] = useState(null);
  const [widgets, setWidgets] = useState([]);
  const [dashboardState, setDashboardState] = useState({
    pageTitle: "Impact Dashboard",
    editMode: false,
  });
  const [messages, setMessages] = useState([]);
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(true);
  const [chatLoading, setChatLoading] = useState(false);
  const [error, setError] = useState(null);
  const [chains, setChains] = useState([]);

  useEffect(() => {
    fetchDashboardMetrics()
      .then((data) => {
        setMetrics(data);
        setWidgets((prev) => (prev.length ? prev : buildStarterWidgets(data)));
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const applyMutations = useCallback((mutationList) => {
    setWidgets((prev) =>
      applyStatefulMutations(prev, mutationList, {
        onDashboardState: (patch) =>
          setDashboardState((s) => ({ ...s, ...patch })),
      }),
    );
  }, []);

  const updateWidget = useCallback((id, patch) => {
    setWidgets((prev) =>
      prev.map((w) => (w.id === id ? { ...w, ...patch } : w)),
    );
  }, []);

  const deleteWidget = useCallback((id) => {
    setWidgets((prev) => prev.filter((w) => w.id !== id));
  }, []);

  async function sendPrompt(text) {
    const userPrompt = (text || prompt).trim();
    if (!userPrompt || chatLoading) return;
    setChatLoading(true);
    setError(null);
    setMessages((m) => [...m, { role: "user", content: userPrompt }]);
    setPrompt("");

    try {
      const result = await orchestrateLLM({
        userPrompt,
        currentDashboardWidgets: widgets,
        dashboardState,
        interactive: true,
      });

      setChains(result.chainsExecuted || []);
      applyMutations(result.mutations || []);
      applyMutations(result.dashboardMutations || []);
      if (result.dashboardState?.pageTitle) {
        setDashboardState((s) => ({
          ...s,
          pageTitle: result.dashboardState.pageTitle,
        }));
      }

      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content: result.botResponseText || "Done.",
          source: result.source,
          followUps: result.followUpQuestions,
        },
      ]);
    } catch (err) {
      setError(err.message);
      setMessages((m) => [
        ...m,
        { role: "assistant", content: `Error: ${err.message}`, source: "error" },
      ]);
    } finally {
      setChatLoading(false);
    }
  }

  if (loading) return <p className="text-slate-600">Loading dashboard…</p>;

  const summary = metrics?.summary;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-900">{dashboardState.pageTitle}</h2>
          {metrics?.dataset && (
            <p className="text-sm text-slate-600">
              {metrics.dataset.dataset_name} · {metrics.dataset.record_count?.toLocaleString()}{" "}
              records
            </p>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className={dashboardState.editMode ? "btn-primary" : "btn-secondary"}
            onClick={() =>
              setDashboardState((s) => ({ ...s, editMode: !s.editMode }))
            }
          >
            {dashboardState.editMode ? "Done editing" : "Edit widgets"}
          </button>
          <button
            type="button"
            className="btn-secondary text-sm"
            onClick={() => metrics && setWidgets(buildStarterWidgets(metrics))}
          >
            Reset layout
          </button>
        </div>
      </div>

      {summary && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {[
            ["Programs", summary.total_programs],
            ["Sessions", summary.total_sessions],
            ["Schools", summary.unique_schools],
            ["At-risk", summary.at_risk_count],
          ].map(([label, value]) => (
            <div key={label} className="rounded-lg border border-slate-200 bg-white px-4 py-3">
              <p className="text-xs text-slate-500">{label}</p>
              <p className="text-lg font-bold">{value}</p>
            </div>
          ))}
        </div>
      )}

      <DashboardCanvas
        widgets={widgets}
        editMode={dashboardState.editMode}
        onUpdateWidget={updateWidget}
        onDeleteWidget={deleteWidget}
      />

      <div className="card">
        <div className="flex items-center justify-between gap-2">
          <h3 className="font-semibold">Dashboard copilot</h3>
          {chains.length > 0 && (
            <span className="text-xs text-slate-500">
              Chains: {chains.join(" → ")}
            </span>
          )}
        </div>
        <p className="mt-1 text-sm text-slate-600">
          Ask questions or generate any chart (bar, line, pie, KPI). Edits apply to the canvas
          above; use Edit mode for manual tweaks.
        </p>

        <form
          className="mt-4 flex flex-col gap-2 sm:flex-row"
          onSubmit={(e) => {
            e.preventDefault();
            sendPrompt();
          }}
        >
          <input
            className="input flex-1"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder='e.g. "Add a pie chart of top themes"'
            disabled={chatLoading}
          />
          <button type="submit" className="btn-primary" disabled={chatLoading}>
            {chatLoading ? "Thinking…" : "Send"}
          </button>
        </form>

        <div className="mt-3 flex flex-wrap gap-2">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              type="button"
              className="btn-secondary text-xs"
              onClick={() => sendPrompt(s)}
              disabled={chatLoading}
            >
              {s}
            </button>
          ))}
        </div>

        {error && <p className="mt-2 text-sm text-red-600">{error}</p>}

        <div className="mt-4 max-h-64 space-y-3 overflow-y-auto">
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`rounded-lg px-3 py-2 text-sm ${
                msg.role === "user"
                  ? "ml-8 bg-brand-50 text-brand-900"
                  : "mr-8 bg-slate-100 text-slate-800"
              }`}
            >
              <p className="whitespace-pre-wrap">{msg.content}</p>
              {msg.followUps?.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {msg.followUps.map((f) => (
                    <button
                      key={f}
                      type="button"
                      className="rounded bg-white px-2 py-0.5 text-xs text-brand-700 hover:bg-brand-50"
                      onClick={() => sendPrompt(f)}
                    >
                      {f}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
