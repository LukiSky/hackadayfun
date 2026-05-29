import ComboChartWidget from "./ComboChartWidget.jsx";
import ExecutiveSummaryPage from "./ExecutiveSummaryPage.jsx";
import RegionalPivotTable from "./RegionalPivotTable.jsx";
import { buildComboChartData, buildInsightKpis, buildPivotRows } from "../lib/reportData.js";

export default function ReportCanvas({
  aggregates,
  reportCopy,
  filters,
  fields,
  dates,
  ttsAvailable,
  speechLoading,
  onPlayNarrative,
  onPhraseSelect,
  onReportCopyChange,
}) {
  const kpis = buildInsightKpis(aggregates);
  const comboData = buildComboChartData(aggregates);
  const pivotRows = buildPivotRows(aggregates);
  const topRegion = aggregates?.byRegion?.[0]?.name;

  return (
    <div
      className="grid gap-8"
      id="main-report-page"
      data-layout="paginated"
      data-cross-filtering="enabled"
    >
      <ExecutiveSummaryPage
        dates={dates}
        filters={filters}
        kpis={kpis}
        reportCopy={reportCopy}
        speechLoading={speechLoading}
        ttsAvailable={ttsAvailable}
        onPhraseSelect={onPhraseSelect}
        onPlayNarrative={onPlayNarrative}
        onReportCopyChange={onReportCopyChange}
      />

      <section className="report-page grid gap-4" id="page-2-visuals">
        <ComboChartWidget
          annotation={
            topRegion
              ? `${topRegion}: strongest outcome signal in the current filter context.`
              : null
          }
          data={comboData}
          title="Outcome vs. peer target by region (with feedback index)"
        />
        <RegionalPivotTable
          rows={pivotRows}
          title="Comprehensive regional breakdown"
        />
      </section>
    </div>
  );
}
