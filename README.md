# ImpactLens AI (GDayHack)

**ImpactLens AI** is a full-stack analytics and storytelling platform built for the **LifeChanger** workshop program. It turns thousands of Salesforce-style survey responses into an interactive dashboard, AI-generated insights, editable report layouts, and optional voice narration—so program leaders can see impact quickly and explain it to schools, funders, and internal teams.

Live demo (when deployed): [https://hackadayfun.vercel.app](https://hackadayfun.vercel.app)

---

## Team

| Name | Role |
|------|------|
| **Lukita Iswara** | Backend Engineer and AI dev |
| **Jiaxi (Chris) Lin** | Frontend Developer |
| **Javic Rotanson** | Planner and team lead |

---

## What this project does

LifeChanger collects rich qualitative and quantitative feedback after workshops (school, region, workshop topic, sentiment, attendance, and open-text answers). Raw CSV exports are hard to explore in spreadsheets alone.

**ImpactLens AI** solves that by:

1. **Loading and cleaning** the LifeChanger CSV (validation, typing, analytics aggregates).
2. **Showing a live dashboard** with filters, charts, pivot-style tables, and KPI cards.
3. **Letting users ask questions in natural language** (“Which region has the lowest attendance?”) backed by LangChain + Hugging Face (Gemma).
4. **Building and editing the dashboard with an AI copilot**—add charts, change titles, apply filters, clear widgets, or switch themes via chat.
5. **Generating narratives**—executive summaries, impact stories, and PDF-ready report views.
6. **Optional text-to-speech (F5-TTS)** for narrating insights locally (disabled on Vercel serverless by default).

The product goal is **impact visibility**: move from static exports to a conversational, visual command center for program data.

---

## Main features

### Dashboard & analytics

- Pre-built widgets (bar, line, pie, tables, metrics) driven by backend analytics.
- **Slicers and filters** (region, school, workshop, sentiment, themes).
- **Regional pivot table** and trend views.
- Dataset metadata and CSV download via `/api/dataset` and `/api/dataset/csv`.

### AI copilot (dashboard editor)

Users type commands in the side panel; the backend orchestrates LLM chains to:

- Add or update charts from the data.
- Rename the dashboard, change theme/layout.
- Apply filters or focus specific widgets.
- Return **structured mutations** the React app applies to dashboard state.

Example prompts:

- “Add a bar chart of attendance by region”
- “Add a pie chart of feedback sentiment”
- “Which workshop has the most negative feedback?”
- “Clear all widgets” / turn on edit mode

### Q&A and insights

- **Ask** — analytical questions over the dataset (`POST /api/ask`).
- **Insights** — dashboard-aware insight cards with evidence (`POST /api/insights`).
- **Chat** — multi-turn copilot with optional streaming (`POST /api/chat`, `/api/chat/stream`).
- **Reports & stories** — longer-form outputs for funders and executives (`POST /api/report`, `/api/story`).

### Report canvas

- **Report view** with executive narrative, shareable document model, and **Export to PDF** (print-friendly layout).
- **Story-driven dashboard** mode for presentation-style flows.

### Speech (local / optional)

- **F5-TTS** integration for turning narrative text into WAV audio (`POST /api/tts/speak`).
- Intended for local or GPU-backed environments; **off by default on Vercel** (`F5_TTS_ENABLED=0`).

---

## How it is built (architecture)

```text
Browser (React + Vite)
    │
    │  same origin in production: /api/*
    ▼
┌─────────────────────────────────────┐
│  Vercel (one project)               │
│  • Static: frontend/dist            │
│  • Serverless: api/index.py         │
└─────────────────────────────────────┘
    │
    │  imports
    ▼
backend/  (FastAPI app, agents, data layer)
    ├── main.py              FastAPI app, CORS, routers
    ├── routers/impact.py    REST API for dashboard & LLM
    ├── routers/tts.py       TTS routes (when enabled)
    ├── agents/              LangChain orchestration, charts, stories
    ├── data/                CSV load, analytics, ML predictions
    └── tts/                 F5-TTS (optional, heavy)
```

**Local development** runs two processes: Vite on port **5173** (proxies `/api` → **5000**) and Uvicorn for FastAPI.

**Production (Vercel)** uses a single domain:

- `/` → React SPA (`index.html` fallback for client routes)
- `/api/*` → Python serverless function (`api/index.py` wraps `backend/main.py`)

---

## Repository layout

```text
hackadayfun/
├── frontend/           React UI (Vite, Recharts, Tailwind)
│   └── src/
│       ├── App.jsx                 Main app shell (~3000 lines)
│       ├── components/             Dashboard, report, story, widgets
│       └── lib/                    Orchestrator, filters, TTS playback
├── backend/            FastAPI + LangChain + analytics
│   ├── main.py
│   ├── routers/
│   ├── agents/
│   └── data/           LifeChanger CSV + analytics code
├── api/                Vercel serverless entry
│   ├── index.py        ASGI app export for Vercel
│   └── requirements.txt
├── vercel.json         Build + rewrites + function config
├── pyproject.toml      Python 3.12 pin for Vercel
└── scripts/dev.sh      Start backend + frontend together
```

---

## Tech stack

| Layer | Technologies |
|-------|----------------|
| Frontend | React 19, Vite, Recharts, Tailwind, Lucide icons, PapaParse |
| Backend | FastAPI, Uvicorn, Pydantic |
| AI | LangChain, Hugging Face router (Gemma), custom agent chains |
| Data | pandas-style analytics in Python, scikit-learn (predictions), 10k-row LifeChanger CSV |
| Deploy | Vercel (static frontend + Python serverless API) |
| Optional TTS | F5-TTS, PyTorch (local only recommended) |

---

## Run locally

### Option A — one script

```bash
chmod +x scripts/dev.sh
./scripts/dev.sh
```

### Option B — two terminals

**Backend (FastAPI)**

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set HF_TOKEN, verify DATASET_FILE
uvicorn main:app --host 127.0.0.1 --port 5000 --reload
```

**Frontend (Vite)**

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** for the UI. API docs: **http://localhost:5000/docs**.

The frontend proxies `/api` to the backend in dev (`frontend/vite.config.js`), so you do not need `VITE_API_URL` locally.

---

## Configuration

Copy `backend/.env.example` to `backend/.env`:

| Variable | Purpose |
|----------|---------|
| `HF_TOKEN` | Hugging Face token for Gemma / router (required for LLM features) |
| `HF_MODEL` | Model id (default in `.env.example`) |
| `DATASET_FILE` | Path to LifeChanger CSV (default: `data/LifeChanger_Sample_Data_Populated_10000.csv` under `backend/data/`) |
| `FRONTEND_ORIGIN` | Allowed CORS origin (e.g. `http://localhost:5173` or your Vercel URL) |
| `F5_TTS_ENABLED` | `1` to load TTS locally, `0` to skip (recommended for Vercel) |
| `PORT` | API port (default `5000`) |

Dataset file used in production builds:

`backend/data/LifeChanger_Sample_Data_Populated_10000.csv`

---

## Deploy to Vercel (frontend + API together)

1. Import the GitHub repo on [Vercel](https://vercel.com/new).
2. **Framework Preset:** **Other** (not “Services”).
3. **Root Directory:** `./` (repository root).
4. Vercel reads `vercel.json` for build and routes:
   - Builds `frontend/` → `frontend/dist`
   - Routes `/api/*` → serverless Python (`api/index.py`)
   - Routes other paths → `index.html` (SPA)

**Environment variables** (Production):

| Name | Example |
|------|---------|
| `HF_TOKEN` | your Hugging Face token |
| `F5_TTS_ENABLED` | `0` |
| `FRONTEND_ORIGIN` | `https://hackadayfun.vercel.app` |
| `DATASET_FILE` | `data/LifeChanger_Sample_Data_Populated_10000.csv` (optional if default path works) |

**Smoke test after deploy:**

- `https://YOUR-APP.vercel.app` — dashboard UI  
- `https://YOUR-APP.vercel.app/api/health` — API status  
- `https://YOUR-APP.vercel.app/api/dataset` — dataset metadata  

---

## Key API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Service health, LLM configured, row count |
| GET | `/api/dataset` | Dataset metadata and summary |
| GET | `/api/dashboard` | Dashboard metrics payload |
| GET | `/api/analyze` | Full analytics bundle |
| POST | `/api/llm/orchestrate` | Copilot: dashboard mutations + narrative |
| POST | `/api/insights` | Insight cards for active dashboard context |
| POST | `/api/ask` | Natural-language Q&A over data |
| POST | `/api/chat` | Copilot chat turn |
| GET | `/api/langchain/status` | LangChain / model status |
| POST | `/api/tts/speak` | TTS audio (when enabled) |

Full list is returned from `GET /` on the API root.

---

## Branches

| Branch | Notes |
|--------|--------|
| `main` | Hackathon MVP / production snapshot |
| `cursor/fastapi-f5-tts-integration` | Full UI + FastAPI + LangChain + F5-TTS integration branch |

---

## License & attribution

Built for **GDayHack** using LifeChanger sample program data. See dataset notes in `frontend/dist/DATASET.md` for CSV sourcing details.
