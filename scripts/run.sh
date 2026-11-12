#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
. .venv/bin/activate
# Load .env if present (gitignored, never committed). Parses KEY=value lines only;
# it does not source the file, so it cannot execute code.
if [ -f .env ]; then
  echo "Loading environment from .env"
  while IFS='=' read -r raw_key raw_value; do
    key="${raw_key#export }"
    key="${key// /}"
    value="$raw_value"
    case "$key" in ''|\#*) continue ;; esac
    if [[ ! "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
      echo "  skipping invalid line in .env: $key" >&2
      continue
    fi
    value="${value#\"}"; value="${value%\"}"
    value="${value#\'}"; value="${value%\'}"
    export "$key=$value"
  done < .env
fi
PORT="${PORT:-8000}"
if ! env | grep -qE '^(OPENAI_API_KEY|GROQ_API_KEY|GEMINI_API_KEY|OPENROUTER_API_KEY|MISTRAL_API_KEY|HUGGINGFACE_API_KEY|CLOUDFLARE_API_TOKEN|ANTHROPIC_API_KEY|XAI_API_KEY)=.'; then
  echo "Note: no provider key is set in this environment."
  echo "AI nodes will fail until one is set. Either:"
  echo "  cp .env.example .env   # then paste your key into .env (gitignored)"
  echo "  export OPENAI_API_KEY=sk-..."
  echo "or use a local provider (Ollama) — no key needed."
fi
echo "Starting n3rf on http://127.0.0.1:${PORT}"
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port "$PORT"
