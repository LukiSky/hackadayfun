# ImpactLens AI (GDayHack)

Full-stack impact dashboard: LifeChanger CSV data, LangChain orchestration, interactive charts, copilot chat, TTS, PDF export.

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

Open **http://localhost:5173**. API: **http://localhost:5000**.

## Configuration

`backend/.env`:

- `HF_TOKEN` — Hugging Face router (Gemma)
- `DATASET_FILE=data/LifeChanger_Sample_Data_Populated_10000.csv`
- `F5_TTS_ENABLED=0` — skip TTS model load if you only need the dashboard

## Dashboard copilot examples

- Add a bar chart of attendance by region
- Add a pie chart of feedback sentiment
- Which workshop has the most negative feedback?
- Clear all widgets / edit mode on the left panel

## Branches

- `main` — hackathon MVP snapshot
- `cursor/fastapi-f5-tts-integration` — full UI + FastAPI + LangChain + F5-TTS

The full frontend lives in `frontend/src/App.jsx` (~3000 lines) with `DashboardControlPanel`, `ReportCanvas`, and copilot chat.
