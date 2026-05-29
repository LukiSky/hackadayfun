/** Click-to-load sample prompts for dashboard regeneration demos. */

export const DEMO_REGENERATE_SCENARIOS = [
  {
    id: "executive-full",
    label: "Full executive layout",
    hint: "KPIs + regional charts + narrative briefing",
    prompt: `Regenerate the dashboard for a hackathon demo with this exact layout:

1. PAGE TITLE: Set to "LifeChanger Workshop Impact — Executive Demo".

2. KEEP existing default widgets (outcome line chart, valid-outcome KPI, morning briefing) — do not clear the canvas.

3. ADD_WIDGET: Pie chart titled "Participants by Region" using regional breakdown from the filtered CSV.

4. ADD_WIDGET: Bar chart titled "Average Outcome by Workshop Type" using workshop grouping.

5. UPDATE_WIDGET widget-morning-briefing: Replace content with a 3-sentence executive narrative naming the top region, outcome trend, and one recommended action for facilitators.

6. STORY MODE: Add storytelling blocks with a "Listen to Insight" audio narrative summarising Q3-style performance.

Rules: DEFAULT_TO_APPEND only. Never CLEAR_DASHBOARD unless I ask.`,
  },
  {
    id: "regional-deep-dive",
    label: "Regional deep dive",
    hint: "Filters + regional comparison focus",
    prompt: `Demo regeneration — regional deep dive:

- ADD_WIDGET: Bar chart "Outcome Score by Region" (sorted highest first).
- ADD_WIDGET: KPI card "Top Region" showing the leading region name and average score.
- UPDATE_WIDGET widget-rev-ytd: Change to bar-chart type if it is a line chart.
- UPDATE the executive briefing to compare the strongest vs weakest region with specific numbers from the data.
- Apply story-driven visualizations with one chart annotation explaining the gap.

Preserve all current widgets. Append new ones below.`,
  },
  {
    id: "feedback-themes",
    label: "Feedback & themes",
    hint: "Theme counts + qualitative story",
    prompt: `Regenerate for a feedback-focused demo dashboard:

- ADD_WIDGET: Bar chart "Feedback Responses by Theme" from theme field counts.
- ADD_WIDGET: KPI card "Total Feedback Rows" with count from current filters.
- UPDATE_WIDGET widget-morning-briefing: Write a narrative focused on the dominant feedback theme and a representative participant voice (de-identified).
- Include storytelling block linking to evidence table themes.
- Title suggestion: "Participant Voice & Themes — Demo"

Do not remove existing charts. Use ADD_WIDGET mutations only.`,
  },
  {
    id: "minimal-append",
    label: "Minimal append test",
    hint: "Single chart — quick smoke test",
    prompt: `Quick demo test — append only one widget:

ADD_WIDGET: A simple bar chart titled "Rows by School" using the school field from the filtered dataset. Keep every existing widget unchanged. Reply with the mutation list you applied.`,
  },
];

export function getDemoScenarioById(id) {
  return DEMO_REGENERATE_SCENARIOS.find((item) => item.id === id);
}
