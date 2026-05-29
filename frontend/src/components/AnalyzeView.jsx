import { useEffect, useState } from "react";
import { fetchAnalysis } from "../api/client.js";

export default function AnalyzeView() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAnalysis()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-slate-600">Running analysis…</p>;
  if (error) return <p className="text-red-600">Error: {error}</p>;
  if (!data) return null;

  const { analysis, sentiment, risks_and_opportunities } = data;

  return (
    <div className="space-y-6">
      <div className="card">
        <h2 className="text-lg font-semibold">Overall summary</h2>
        <pre className="mt-3 overflow-x-auto rounded-lg bg-slate-50 p-3 text-sm">
          {JSON.stringify(analysis.overall_summary, null, 2)}
        </pre>
        <ul className="mt-3 list-inside list-disc text-sm text-slate-600">
          {analysis.citations.map((c, i) => (
            <li key={i}>{c}</li>
          ))}
        </ul>
      </div>

      <div className="card">
        <h2 className="text-lg font-semibold">Program insights</h2>
        <div className="mt-4 space-y-3">
          {analysis.program_insights.map((p) => (
            <div
              key={p.program_id}
              className={`rounded-lg border p-4 ${p.flagged ? "border-amber-300 bg-amber-50" : "border-slate-200"}`}
            >
              <p className="font-medium">
                {p.name}{" "}
                {p.flagged && (
                  <span className="ml-2 text-xs font-semibold text-amber-700">FLAGGED</span>
                )}
              </p>
              <p className="text-sm text-slate-600">{p.cohort}</p>
              <p className="mt-2 text-sm">
                Attendance {(p.attendance_rate * 100).toFixed(0)}% · Wellbeing {p.wellbeing_score_avg} ·
                Sentiment: +{p.sentiment_breakdown.positive} / ~{p.sentiment_breakdown.mixed} / −
                {p.sentiment_breakdown.negative}
              </p>
            </div>
          ))}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card">
          <h2 className="font-semibold">Sentiment trends</h2>
          <pre className="mt-3 overflow-x-auto rounded-lg bg-slate-50 p-3 text-xs">
            {JSON.stringify(sentiment.sentiment_distribution, null, 2)}
          </pre>
        </div>
        <div className="card">
          <h2 className="font-semibold">Risks & opportunities</h2>
          <p className="mt-2 text-sm text-slate-600">
            {risks_and_opportunities.risks.length} risk(s),{" "}
            {risks_and_opportunities.opportunities.length} opportunity(ies)
          </p>
          <ul className="mt-3 space-y-2 text-sm">
            {risks_and_opportunities.risks.map((r, i) => (
              <li key={i} className="rounded border border-red-100 bg-red-50 p-2">
                <strong>{r.program_name}</strong>: {r.type} ({r.metric})
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
