#!/usr/bin/env bash
set -euo pipefail

# Run FastAPI backend for Hugging Face Spaces.
# FastAPI will automatically serve the built React static files.

APP_ROOT="/app"
# Hugging Face Spaces uses port 7860
BACKEND_PORT="7860"

export BACKEND_URL="http://127.0.0.1:${BACKEND_PORT}"

echo "Starting FastAPI backend on :${BACKEND_PORT} ..."
exec python -m uvicorn app:app \
  --app-dir "${APP_ROOT}/backend" \
  --host 0.0.0.0 \
  --port "${BACKEND_PORT}" \
  --log-level info
