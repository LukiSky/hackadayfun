#!/usr/bin/env bash
# ImpactLens AI — FastAPI backend + Vite frontend
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
VENV="$BACKEND/.venv"

if [[ ! -f "$BACKEND/.env" ]]; then
  cp "$BACKEND/.env.example" "$BACKEND/.env"
  echo "Created backend/.env — set HF_TOKEN for LLM."
fi

if [[ ! -d "$VENV" ]]; then
  python3 -m venv "$VENV"
fi
# shellcheck source=/dev/null
source "$VENV/bin/activate"
pip install -q -r "$BACKEND/requirements.txt"

cd "$FRONTEND"
[[ -d node_modules ]] || npm install

echo "API:  http://localhost:5000  (uvicorn)"
echo "UI:   http://localhost:5173  (vite)"
echo "Press Ctrl+C to stop both."

cd "$BACKEND"
uvicorn main:app --host 127.0.0.1 --port 5000 --reload &
API_PID=$!
trap 'kill $API_PID 2>/dev/null || true' EXIT INT TERM
sleep 2
cd "$FRONTEND"
npm run dev
