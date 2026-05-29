import { Volume2 } from "lucide-react";
import { fiscalPeriodLabel } from "../lib/reportData.js";

function KpiBox({ label, value, subtext, status }) {
  const border =
    status === "positive"
      ? "border-green-600"
      : status === "warning"
        ? "border-amber-500"
        : "border-red-500";
  return (
    <div className={`rounded-xl border-l-4 bg-white p-4 shadow-sm ${border}`}>
      <p className="text-xs font-bold uppercase tracking-wider text-black/45">{label}</p>
      <p className="mt-2 font-garage text-2xl font-black">{value}</p>
      <p className="mt-1 text-xs font-semibold text-black/55">{subtext}</p>
    </div>
  );
}

export default function ExecutiveSummaryPage({
  kpis,
  reportCopy,
  filters,
  dates,
  ttsAvailable,
  speechLoading,
  onPlayNarrative,
  onPhraseSelect,
  onReportCopyChange,
}) {
  const period = fiscalPeriodLabel(filters, dates);

  function updateField(field, value) {
    onReportCopyChange?.({ ...reportCopy, [field]: value });
  }

  return (
    <section className="report-page" id="page-1-executive-summary">
      <article
        className="rounded-xl border border-black/10 bg-white p-6 lg:p-8"
        id="exec-narrative"
      >
        <div className="report-typography-serif">
          <header className="mb-6 border-b border-black/10 pb-4">
            <input
              aria-label="Executive briefing title"
              className="report-editable font-garage text-3xl font-black text-black"
              type="text"
              value={reportCopy.executiveTitle}
              onChange={(event) => updateField("executiveTitle", event.target.value)}
            />
            <p className="mt-1 text-sm font-semibold text-black/55">
              Prepared by AI Copilot | {period}
            </p>
          </header>

          <div className="grid gap-6 md:grid-cols-2">
            <div>
              <textarea
                aria-label="Executive summary paragraph one"
                className="report-editable min-h-[120px] text-base"
                value={reportCopy.headline}
                onChange={(event) => updateField("headline", event.target.value)}
              />
              <button
                className="mt-2 text-xs font-bold text-[#2b5c8f] underline print-exclude"
                type="button"
                onClick={() =>
                  onPhraseSelect?.("Analyze the leading regional outcome in this briefing.")
                }
              >
                Analyze phrase
              </button>
            </div>
            <textarea
              aria-label="Executive summary paragraph two"
              className="report-editable min-h-[120px] text-base"
              value={reportCopy.caution}
              onChange={(event) => updateField("caution", event.target.value)}
            />
          </div>

          <div className="mt-8 grid gap-4 md:grid-cols-3">
            {kpis.map((kpi) => (
              <KpiBox key={kpi.label} {...kpi} />
            ))}
          </div>
        </div>

        <div
          className="audio-player mt-6 flex flex-col gap-3 rounded-xl border border-black/10 bg-[#FFD100]/20 p-4 print-hidden"
          data-print-visibility="hidden"
        >
          <button
            className="inline-flex w-fit items-center gap-2 rounded-full bg-black px-4 py-2 text-sm font-bold text-white disabled:opacity-50"
            disabled={!ttsAvailable || speechLoading || !reportCopy.briefing?.trim()}
            type="button"
            onClick={() => onPlayNarrative?.(reportCopy.briefing)}
          >
            <Volume2 size={16} />
            {speechLoading ? "Generating audio…" : "Listen to briefing"}
          </button>
          <textarea
            aria-label="Briefing narrative"
            className="report-editable min-h-[80px] text-sm font-semibold text-black/65"
            value={reportCopy.briefing}
            onChange={(event) => updateField("briefing", event.target.value)}
          />
        </div>

        <p className="mt-4 text-xs font-semibold text-black/45 print-exclude">
          All narrative fields are editable. Changes appear in PDF export.
        </p>
      </article>
    </section>
  );
}
