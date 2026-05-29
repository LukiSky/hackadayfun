#!/usr/bin/env bash
# Start ImpactLens backend + frontend for local development.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

BACKEND_DIR="$ROOT/backend"
FRONTEND_DIR="$ROOT/frontend"
VENV="$BACKEND_DIR/.venv"

if [[ ! -f "$BACKEND_DIR/.env" ]]; then
  cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
  echo "Created backend/.env from .env.example — add HF_TOKEN for full LLM."
fi

if [[ ! -d "$VENV" ]]; then
  echo "Creating Python venv…"
  python3 -m venv "$VENV"
fi

# shellcheck source=/dev/null
source "$VENV/bin/activate"
pip install -q -r "$BACKEND_DIR/requirements.txt"

cd "$FRONTEND_DIR"
if [[ ! -d node_modules ]]; then
  echo "Installing frontend dependencies…"
  npm install
fi

echo "Starting Flask API on http://localhost:5000"
cd "$BACKEND_DIR"
python app.py &
BACKEND_PID=$!

cleanup() {
  kill "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

sleep 1
echo "Starting Vite on http://localhost:5173"
cd "$FRONTEND_DIR"
npm run dev
