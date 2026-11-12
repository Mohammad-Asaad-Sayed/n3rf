#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> Checking tools"
command -v python3 >/dev/null 2>&1 || { echo "python3 not found"; exit 1; }
PY_VER="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
echo "Python $PY_VER"
python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,12) else 1)' || { echo "Need Python >= 3.12"; exit 1; }

if ! command -v pnpm >/dev/null 2>&1; then
  echo "pnpm not found. Install: npm i -g pnpm  (or corepack enable)"
  exit 1
fi

echo "==> Python venv"
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements-dev.txt

echo "==> Frontend deps + build"
cd frontend
pnpm install
pnpm run build
cd ..

echo "==> Site deps + build"
cd site
pnpm install
pnpm run build
cd ..

echo "==> Smoke test"
.venv/bin/pytest -q
.venv/bin/ruff check app tests

echo "==> Setup complete."
echo
echo "Next steps:"
echo "  1. Configure a provider key (n3rf never stores keys). Either:"
echo "       cp .env.example .env    # then paste your key into .env"
echo "     or export it in your shell, e.g. export OPENAI_API_KEY=sk-..."
echo "     (or skip and use a local model such as Ollama — no key needed)"
echo "  2. Run: ./scripts/run.sh   (loads .env automatically)"
echo "  3. Open http://127.0.0.1:8000 — Models page pastes a key for a one-shot"
echo "     connection test; workspace home warns if no provider is reachable."
