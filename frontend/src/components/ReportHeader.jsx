import SlicerBar from "./SlicerBar.jsx";

/** Center canvas header: title + slicers (export lives in left control panel). */
export default function ReportHeader({
  title,
  filters,
  fields,
  rows,
  dates,
  onFilterChange,
  onDateChange,
  onTitleChange,
}) {
  return (
    <header className="border-b border-black/10 bg-white px-5 py-4 lg:px-6" id="global-controls">
      <input
        aria-label="Report title"
        className="report-title-input w-full font-garage text-2xl font-black leading-tight text-black lg:text-3xl"
        id="app-title"
        type="text"
        value={title}
        onChange={(event) => onTitleChange?.(event.target.value)}
      />
      <SlicerBar
        dates={dates}
        fields={fields}
        filters={filters}
        rows={rows}
        onDateChange={onDateChange}
        onFilterChange={onFilterChange}
      />
    </header>
  );
}
