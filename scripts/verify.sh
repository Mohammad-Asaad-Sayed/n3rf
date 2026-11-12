#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
. .venv/bin/activate
echo "==> pytest"
.venv/bin/pytest -q
echo "==> ruff"
.venv/bin/ruff check app tests
.venv/bin/ruff format --check app tests
echo "==> frontend build"
cd frontend && pnpm run build && cd ..
echo "==> site build"
cd site && pnpm run build && cd ..
echo "==> verify OK"
