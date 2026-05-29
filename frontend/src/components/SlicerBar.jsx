import { useMemo } from "react";

function Slicer({ label, value, options, onChange, type = "dropdown" }) {
  if (type === "date-hierarchy") {
    return (
      <label className="flex min-w-[140px] flex-col gap-1">
        <span className="text-[10px] font-bold uppercase tracking-wider text-black/50">
          {label}
        </span>
        <input
          className="min-h-9 rounded-lg border border-black/15 bg-white px-2 text-sm font-semibold"
          type="date"
          value={value || ""}
          onChange={(e) => onChange(e.target.value)}
        />
      </label>
    );
  }

  return (
    <label className="flex min-w-[140px] flex-col gap-1">
      <span className="text-[10px] font-bold uppercase tracking-wider text-black/50">
        {label}
      </span>
      <select
        className="min-h-9 rounded-lg border border-black/15 bg-white px-2 text-sm font-semibold"
        value={value || "All"}
        onChange={(e) => onChange(e.target.value)}
      >
        <option>All</option>
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {opt}
          </option>
        ))}
      </select>
    </label>
  );
}

export default function SlicerBar({
  filters,
  fields,
  rows,
  dates,
  compact = false,
  onFilterChange,
  onDateChange,
}) {
  const regionOptions = useMemo(() => {
    if (!fields.region) return [];
    return [...new Set(rows.map((r) => r[fields.region]).filter(Boolean))].sort();
  }, [fields.region, rows]);

  const programOptions = useMemo(() => {
    if (!fields.programType) return [];
    return [...new Set(rows.map((r) => r[fields.programType]).filter(Boolean))].sort();
  }, [fields.programType, rows]);

  return (
    <div
      className={
        compact
          ? "grid gap-2"
          : "mt-2 flex flex-wrap items-end gap-4 rounded-xl border border-black/10 bg-white p-4 shadow-sm"
      }
      id="slicer-bar"
    >
      <Slicer
        label="Date range (start)"
        type="date-hierarchy"
        value={filters.fromDate || dates.min || ""}
        onChange={(v) => onDateChange("fromDate", v)}
      />
      <Slicer
        label="Date range (end)"
        type="date-hierarchy"
        value={filters.toDate || dates.max || ""}
        onChange={(v) => onDateChange("toDate", v)}
      />
      {fields.region ? (
        <Slicer
          label="Region"
          options={regionOptions}
          value={filters.region || "All"}
          onChange={(v) => onFilterChange("region", v)}
        />
      ) : null}
      {fields.programType ? (
        <Slicer
          label="Program line"
          options={programOptions}
          value={filters.programType || "All"}
          onChange={(v) => onFilterChange("programType", v)}
        />
      ) : null}
    </div>
  );
}
