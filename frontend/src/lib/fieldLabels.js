/** Human-readable labels for charts and tooltips (ImpactLens spec). */

export const FIELD_DISPLAY_LABELS = {
  region: "Region",
  workshop: "Workshop Type",
  school: "School",
  programType: "Program Type",
  participantGroup: "Participant Group",
  theme: "Feedback Theme",
  sentiment: "Sentiment Score",
  date: "Date",
  outcome: "Average Outcome Score",
  feedback: "Feedback",
};

export function displayFieldLabel(fieldKey) {
  return FIELD_DISPLAY_LABELS[fieldKey] || fieldKey;
}

export function chartCategoryLabel(label) {
  return String(label ?? "Category");
}
