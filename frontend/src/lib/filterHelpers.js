/** Theme / sentiment filters for ImpactLens filter panel. */

export const SENTIMENT_FILTER_OPTIONS = [
  "All",
  "Positive",
  "Neutral",
  "Needs attention",
];

export function rowInferredThemes(row, fields, themeKeywords) {
  const text = [
    fields.feedback ? row[fields.feedback] : "",
    fields.theme ? row[fields.theme] : "",
    fields.sentiment ? row[fields.sentiment] : "",
  ]
    .filter(Boolean)
    .join(" ");

  const normalised = String(text)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();

  return themeKeywords
    .filter(([theme, keywords]) =>
      keywords.some((keyword) => normalised.includes(keyword)),
    )
    .map(([theme]) => theme);
}

export function getThemeFilterOptions(rows, fields, themeKeywords) {
  const options = new Set();
  if (fields.theme) {
    rows.forEach((row) => {
      const value = String(row[fields.theme] ?? "").trim();
      if (value) options.add(value);
    });
  }
  rows.forEach((row) => {
    rowInferredThemes(row, fields, themeKeywords).forEach((theme) => options.add(theme));
  });
  return [...options].sort((a, b) => a.localeCompare(b));
}

export function rowMatchesThemeFilter(row, fields, filter, themeKeywords) {
  if (!filter || filter === "All") return true;
  if (fields.theme && String(row[fields.theme] ?? "").trim() === filter) return true;
  return rowInferredThemes(row, fields, themeKeywords).includes(filter);
}

export function rowMatchesSentimentFilter(row, fields, filter, sentimentBucketFn) {
  if (!filter || filter === "All") return true;
  return sentimentBucketFn(row, fields) === filter;
}
