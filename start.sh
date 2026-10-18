#!/usr/bin/env bash
# One-command start for macOS / Linux: sets up everything on first run, then launches Jarvis.
set -euo pipefail
cd "$(dirname "$0")"

PY=${PYTHON:-python3}
if [ ! -d .venv ]; then
  echo "▶ Creating Python virtual environment…"
  "$PY" -m venv .venv
fi
if [ ! -f .venv/.installed ] || [ backend/requirements.txt -nt .venv/.installed ]; then
  echo "▶ Installing backend packages…"
  .venv/bin/pip install -q -r backend/requirements.txt
  touch .venv/.installed
fi
[ -f .env ] || { cp .env.example .env; echo "▶ Created .env — add your API key there or in Settings."; }

if [ ! -d frontend/node_modules ]; then
  echo "▶ Installing frontend packages…"
  (cd frontend && npm install --no-audit --no-fund)
fi
if [ ! -d frontend/dist ] || [ -n "$(find frontend/src -newer frontend/dist -print -quit)" ]; then
  echo "▶ Building the interface…"
  (cd frontend && npm run build)
fi

echo "▶ Starting Jarvis backend…"
.venv/bin/python -m backend.main &
BACKEND=$!
trap 'kill $BACKEND 2>/dev/null' EXIT
for _ in $(seq 1 40); do curl -sf "http://127.0.0.1:${JARVIS_PORT:-8765}/api/health" >/dev/null && break; sleep 0.5; done

echo "▶ Opening Jarvis…"
(cd frontend && npx electron .)
