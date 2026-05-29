// In dev, Vite proxies /api → Flask. Set VITE_API_URL=http://localhost:5000 if not using proxy.
const API_BASE = import.meta.env.VITE_API_URL || "";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "Request failed");
  }
  return payload;
}

export async function fetchLangchainStatus() {
  const result = await request("/api/langchain/status");
  return result;
}

export async function fetchDashboardMetrics() {
  const result = await request("/api/dashboard");
  return result.data;
}

export async function fetchAnalysis() {
  const result = await request("/api/analyze");
  return result.data;
}

export async function orchestrateDashboard(userPrompt, widgets = [], dashboardState = {}) {
  const result = await request("/api/llm/orchestrate", {
    method: "POST",
    body: JSON.stringify({
      userPrompt,
      currentDashboardWidgets: widgets,
      dashboardState,
    }),
  });
  return result;
}

export async function askQuestion(question) {
  const result = await request("/api/ask", {
    method: "POST",
    body: JSON.stringify({ question }),
  });
  return result.data;
}

export async function generateReport(audience) {
  const result = await request("/api/report", {
    method: "POST",
    body: JSON.stringify({ audience }),
  });
  return result.data;
}

export async function generateStory(theme) {
  const result = await request("/api/story", {
    method: "POST",
    body: JSON.stringify({ theme: theme || undefined }),
  });
  return result.data;
}
