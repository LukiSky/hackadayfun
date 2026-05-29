export async function regenerateStory({
  detailLevel,
  aggregates,
  activeContext,
  chartConfig,
  userPrompt,
}) {
  const response = await fetch("/api/llm/regenerate-story", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      detailLevel,
      aggregates,
      activeContext,
      chartConfig,
      userPrompt:
        userPrompt ||
        `Re-format the current data using detail level: ${detailLevel}`,
    }),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(
      typeof err.detail === "string" ? err.detail : "Story regeneration failed",
    );
  }

  return response.json();
}
