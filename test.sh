#!/usr/bin/env bash
# Runs every test: backend (pytest) and frontend (type-check + Vitest).
set -euo pipefail
cd "$(dirname "$0")"
.venv/bin/pip install -q -r backend/requirements-dev.txt
.venv/bin/python -m pytest -q
(cd frontend && npx tsc -b && npx vitest run)
