#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
. .venv/bin/activate
PORT="${PORT:-8000}"
if ! env | grep -qE '^(OPENAI_API_KEY|GROQ_API_KEY|GEMINI_API_KEY|OPENROUTER_API_KEY|MISTRAL_API_KEY|HUGGINGFACE_API_KEY|CLOUDFLARE_API_TOKEN|ANTHROPIC_API_KEY|XAI_API_KEY)='; then
  echo "Note: no known provider key is set in this environment."
  echo "AI nodes will fail until you export one (e.g. export OPENAI_API_KEY=...) or use a local provider (Ollama)."
fi
echo "Starting n3rf on http://127.0.0.1:${PORT}"
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port "$PORT"
