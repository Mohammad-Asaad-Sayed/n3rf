#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
. .venv/bin/activate
PORT="${PORT:-8000}"
echo "Starting n3rf on http://127.0.0.1:${PORT}"
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port "$PORT"
