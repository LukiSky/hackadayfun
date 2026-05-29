/** Enterprise DocumentModel — page setup and print exclusions. */

export const PAGE_SETUP = {
  format: "A4",
  orientation: "landscape",
  margins: "0.5in",
};

export const PRINT_EXCLUSIONS = [
  "#left-dashboard-controls",
  "#right-chat-pane",
  "#sidebar-copilot",
  "#filter-panel",
  "#right-settings-drawer",
  "#smart-settings-drawer",
  ".print-exclude",
  ".audio-player",
  ".recharts-tooltip-wrapper",
  "[data-print-hide]",
];

export function formatReportDate(date = new Date()) {
  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

export function buildShareUrl(filters = {}) {
  const url = new URL(window.location.href);
  Object.entries(filters).forEach(([key, value]) => {
    if (value && value !== "All") {
      url.searchParams.set(key, value);
    } else {
      url.searchParams.delete(key);
    }
  });
  return url.toString();
}

/** Opens the browser print dialog for #report-export-root (see printReport.css). */
export function exportReportToPdf() {
  window.print();
}
