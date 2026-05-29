const API_BASE = import.meta.env.VITE_API_URL || "";

export async function orchestrateLLM({
  userPrompt,
  currentDashboardWidgets = [],
  dashboardState = {},
  interactive = true,
}) {
  const response = await fetch(`${API_BASE}/api/llm/orchestrate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      userPrompt,
      currentDashboardWidgets,
      dashboardState,
      interactive,
    }),
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "Orchestration failed");
  }
  return payload;
}
