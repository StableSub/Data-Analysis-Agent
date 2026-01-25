#!/usr/bin/env bash
set -euo pipefail

if ROOT_DIR="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel 2>/dev/null)"; then
  :
else
  ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi
BACKEND_DIR="${ROOT_DIR}/backend"
FRONTEND_DIR="${ROOT_DIR}/frontend"

cleanup() {
  kill "${BACKEND_PID:-}" "${FRONTEND_PID:-}" 2>/dev/null || true
}

trap cleanup EXIT INT TERM

(
  cd "${BACKEND_DIR}"
  uvicorn app.main:app --reload --reload-dir "${BACKEND_DIR}/app" --port 8000 --host 127.0.0.1
) &
BACKEND_PID=$!

(
  cd "${FRONTEND_DIR}"
  npm run dev -- --host 127.0.0.1 --port 5173
) &
FRONTEND_PID=$!

wait "${BACKEND_PID}" "${FRONTEND_PID}"
