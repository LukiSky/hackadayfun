import { useState } from "react";
import { generateReport } from "../api/client.js";

const AUDIENCES = [
  { id: "funders", label: "Funders" },
  { id: "schools", label: "School partners" },
  { id: "board", label: "Board" },
  { id: "internal", label: "Internal team" },
];

export default function ReportView() {
  const [audience, setAudience] = useState("funders");
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleGenerate() {
    setLoading(true);
    setError(null);
    try {
      const result = await generateReport(audience);
      setReport(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="card">
        <h2 className="text-lg font-semibold">Generate impact report</h2>
        <p className="mt-1 text-sm text-slate-600">Tailored narrative for your audience (LLM-powered).</p>
        <div className="mt-4 flex flex-wrap gap-2">
          {AUDIENCES.map((a) => (
            <button
              key={a.id}
              type="button"
              onClick={() => setAudience(a.id)}
              className={`rounded-lg px-3 py-1.5 text-sm font-medium ${
                audience === a.id ? "bg-brand-600 text-white" : "bg-slate-100"
              }`}
            >
              {a.label}
            </button>
          ))}
        </div>
        <button type="button" className="btn-primary mt-4" onClick={handleGenerate} disabled={loading}>
          {loading ? "Generating…" : "Generate report"}
        </button>
        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
      </div>

      {report && (
        <div className="card">
          <h3 className="font-semibold capitalize">Report for {report.audience}</h3>
          <div className="prose prose-sm mt-4 max-w-none whitespace-pre-wrap text-sm leading-relaxed">
            {report.report}
          </div>
        </div>
      )}
    </div>
  );
}
