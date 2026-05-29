# ImpactLens AI

AI-powered impact intelligence platform for **Lifechanger**, a youth mentoring nonprofit. ImpactLens analyzes mock program and feedback data, surfaces insights, answers plain-English questions, and runs an **interactive dashboard** where you can generate and edit charts via a LangChain-style copilot.

## Architecture

| Folder | Purpose |
|--------|---------|
| `frontend/` | React + Vite + Tailwind + Recharts UI |
| `backend/` | Flask API, dashboard orchestrator, agent logic |
| `backend/data/` | Lifechanger dataset (`lifechanger_school_partner_input_data_10000.json`, 10k sessions) |
| `backend/agents/` | Orchestrator, chart catalog, Ask, Report, Story, etc. |

## Workflows

1. **Dashboard** — interactive charts (bar / line / pie / KPI), copilot chat, edit mode
2. **Analyse Data** — summaries, sentiment, risks
3. **Ask Questions** — Q&A (LLM or local fallback)
4. **Generate Report** — audience-specific reports (LLM)
5. **Impact Story** — ethical narrative (LLM)

## Quick start (one command)

```bash
chmod +x scripts/dev.sh
./scripts/dev.sh
```

Opens **http://localhost:5173** (UI) and **http://localhost:5000** (API).

### Manual start

**Backend**

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # optional: set HF_TOKEN
python app.py
```

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

## Interactive dashboard copilot

On the **Dashboard** tab, try:

- `Add a bar chart of attendance by program`
- `Add a pie chart of feedback sentiment`
- `Add a line chart of quarterly trends`
- `Which program has the lowest attendance?`
- `Change the last chart to a pie chart`
- `Clear all widgets`

Use **Edit widgets** to change titles, chart types, or remove charts manually.

Orchestration runs through `POST /api/llm/orchestrate` with chains: intent → planner (if LLM) → mutations → narrative.

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/langchain/status` | LLM configured? model name |
| GET | `/api/dataset` | Dataset file info |
| GET | `/api/dashboard` | Dashboard metrics |
| GET | `/api/analyze` | Full program analysis |
| POST | `/api/llm/orchestrate` | `{ "userPrompt", "currentDashboardWidgets", "dashboardState" }` |
| POST | `/api/ask` | `{ "question": "..." }` |
| POST | `/api/report` | `{ "audience": "funders\|schools\|board\|internal" }` |
| POST | `/api/story` | `{ "theme": "optional" }` |

## LLM configuration

- Provider: [Hugging Face Router](https://router.huggingface.co) via OpenAI-compatible API
- Set `HF_TOKEN` in `backend/.env` for full LLM (optional — charts and local Q&A work without it)
- Model: `HF_MODEL` in `.env.example`

## MVP constraints

- Mock / de-identified data only
- No production auth or Salesforce

## License

Hackathon / demo project for GDayHack.
