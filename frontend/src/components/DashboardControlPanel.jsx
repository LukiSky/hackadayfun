import {
  ChevronLeft,
  ChevronRight,
  FileDown,
  Link2,
  RefreshCcw,
  SlidersHorizontal,
} from "lucide-react";
import { exportReportToPdf, formatReportDate } from "../lib/documentModel.js";
import SlicerBar from "./SlicerBar.jsx";

function FilterSelect({ label, value, options, disabled, onChange }) {
  return (
    <label className="grid gap-2 text-sm font-bold text-black/70">
      {label}
      <select
        className="min-h-9 rounded-lg border border-black/10 bg-white px-3 text-sm font-semibold outline-none ring-[#87BAE5] focus:ring-2 disabled:bg-black/[0.04]"
        disabled={disabled}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        <option>All</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  );
}

function Section({ title, defaultOpen = true, children }) {
  return (
    <details className="group border-b border-black/8" open={defaultOpen}>
      <summary className="cursor-pointer list-none py-3 text-xs font-bold uppercase tracking-[0.12em] text-black/50">
        <span className="flex items-center justify-between gap-2">
          {title}
          <span className="text-black/30 group-open:rotate-90">›</span>
        </span>
      </summary>
      <div className="pb-4">{children}</div>
    </details>
  );
}

export default function DashboardControlPanel({
  collapsed,
  width,
  filters,
  fields,
  rows,
  dates,
  themeOptions,
  filterFieldList,
  sentimentOptions,
  dashboardState,
  editMode,
  onToggleCollapsed,
  onResizeStart,
  onFilterChange,
  onDateChange,
  onResetFilters,
  onShare,
  onThemeChange,
  onEditModeChange,
  onRefreshData,
  onOpenAdvancedSettings,
}) {
  if (collapsed) {
    return (
      <aside
        className="print-exclude flex h-full flex-col items-center gap-3 border-r border-black/10 bg-white py-4"
        id="left-dashboard-controls"
        style={{ width: 76 }}
      >
        <button
          aria-label="Expand dashboard controls"
          className="rounded-full border border-black/10 p-2 hover:bg-black/[0.04]"
          type="button"
          onClick={onToggleCollapsed}
        >
          <ChevronRight size={18} />
        </button>
        <SlidersHorizontal className="text-black/40" size={20} />
      </aside>
    );
  }

  return (
    <aside
      className="print-exclude relative flex h-full min-h-0 flex-col border-r border-black/10 bg-white"
      id="left-dashboard-controls"
      style={{ width }}
    >
      <button
        aria-label="Resize controls panel"
        className="absolute -right-2 top-0 z-20 flex h-full w-4 cursor-col-resize items-center justify-center"
        type="button"
        onPointerDown={onResizeStart}
      >
        <span className="h-16 w-1 rounded-full bg-black/20" />
      </button>

      <header className="flex items-center justify-between gap-2 border-b border-black/8 px-4 py-4">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-black/45">
            Dashboard Controls
          </p>
          <h2 className="font-garage text-lg font-black">Settings &amp; export</h2>
        </div>
        <button
          aria-label="Collapse panel"
          className="rounded-full border border-black/10 p-1.5 hover:bg-black/[0.04]"
          type="button"
          onClick={onToggleCollapsed}
        >
          <ChevronLeft size={16} />
        </button>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto px-4">
        <div className="print-doc-header hidden">
          <span className="font-bold">LifeChanger Impact Guide</span>
          <span>Generated on: {formatReportDate()}</span>
        </div>

        <Section title="Export &amp; Share">
          <div className="grid gap-2">
            <button
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-black px-4 py-2.5 text-sm font-bold text-white hover:opacity-90"
              type="button"
              onClick={() => exportReportToPdf()}
            >
              <FileDown size={16} />
              Export to PDF
            </button>
            <button
              className="flex w-full items-center justify-center gap-2 rounded-lg border border-black/10 bg-white px-4 py-2 text-sm font-bold hover:bg-black/[0.03]"
              type="button"
              onClick={onShare}
            >
              <Link2 size={16} />
              Share link
            </button>
          </div>
        </Section>

        <Section title="Workspace settings">
          <div className="grid gap-3">
            <label className="flex items-center justify-between gap-3 text-sm font-semibold">
              <span>Edit layout mode</span>
              <input
                checked={editMode}
                className="h-4 w-4 accent-black"
                type="checkbox"
                onChange={(event) => onEditModeChange(event.target.checked)}
              />
            </label>
            <label className="grid gap-2 text-sm font-bold text-black/70">
              Report theme
              <select
                className="min-h-9 rounded-lg border border-black/10 px-3 text-sm font-semibold"
                value={dashboardState.theme === "dark" ? "Executive (Dark)" : "Corporate (Light)"}
                onChange={(event) =>
                  onThemeChange(
                    event.target.value.includes("Dark") ? "dark" : "light",
                  )
                }
              >
                <option>Corporate (Light)</option>
                <option>Executive (Dark)</option>
              </select>
            </label>
            <button
              className="flex items-center justify-center gap-2 rounded-lg border border-black/10 px-3 py-2 text-sm font-bold hover:bg-black/[0.03]"
              type="button"
              onClick={onRefreshData}
            >
              <RefreshCcw size={16} />
              Refresh data now
            </button>
            <button
              className="text-left text-xs font-bold text-[#2b5c8f] underline"
              type="button"
              onClick={onOpenAdvancedSettings}
            >
              Advanced chart &amp; story settings
            </button>
          </div>
        </Section>

        <Section title="Explore CSV" defaultOpen={false}>
          <div className="grid gap-3">
            {filterFieldList.map(([field, label]) => {
              if (field === "feedbackTheme") {
                return (
                  <FilterSelect
                    disabled={!themeOptions.length}
                    key={field}
                    label={label}
                    options={themeOptions}
                    value={filters.feedbackTheme}
                    onChange={(value) => onFilterChange("feedbackTheme", value)}
                  />
                );
              }
              if (field === "sentimentFilter") {
                return (
                  <FilterSelect
                    key={field}
                    label={label}
                    options={sentimentOptions.filter((item) => item !== "All")}
                    value={filters.sentimentFilter}
                    onChange={(value) => onFilterChange("sentimentFilter", value)}
                  />
                );
              }
              return (
                <FilterSelect
                  disabled={!fields[field]}
                  key={field}
                  label={label}
                  options={[...new Set(rows.map((r) => String(r[fields[field]] ?? "").trim()).filter(Boolean))].sort()}
                  value={filters[field]}
                  onChange={(value) => onFilterChange(field, value)}
                />
              );
            })}
            <SlicerBar
              compact
              dates={dates}
              fields={fields}
              filters={filters}
              rows={rows}
              onDateChange={onDateChange}
              onFilterChange={onFilterChange}
            />
            <button
              className="w-full rounded-lg border border-black/10 py-2 text-sm font-bold"
              type="button"
              onClick={onResetFilters}
            >
              Reset filters
            </button>
          </div>
        </Section>
      </div>
    </aside>
  );
}
