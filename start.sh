#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
STREAMLIT_PORT="${STREAMLIT_PORT:-8501}"

mkdir -p data files logs backups

PYTHON_EXECUTABLE="${PYTHON_BIN:-python}"
if [[ -x .venv/bin/python ]]; then PYTHON_EXECUTABLE=".venv/bin/python"; fi

cleanup() {
  kill "${API_PID:-}" "${UI_PID:-}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

"$PYTHON_EXECUTABLE" -m uvicorn app:app --host "$HOST" --port "$PORT" --reload &
API_PID=$!
"$PYTHON_EXECUTABLE" -m streamlit run streamlit_app.py --server.address 0.0.0.0 --server.port "$STREAMLIT_PORT" --server.headless true &
UI_PID=$!

printf 'Documenty API: http://127.0.0.1:%s/health\n' "$PORT"
printf 'Documenty UI:  http://127.0.0.1:%s\n' "$STREAMLIT_PORT"
if [[ "${CODESPACES:-}" == "true" && -n "${CODESPACE_NAME:-}" && -n "${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:-}" ]]; then
  printf 'Codespaces API: https://%s-%s.%s/health\n' "$CODESPACE_NAME" "$PORT" "$GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN"
  printf 'Codespaces UI:  https://%s-%s.%s\n' "$CODESPACE_NAME" "$STREAMLIT_PORT" "$GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN"
fi
wait -n "$API_PID" "$UI_PID"
