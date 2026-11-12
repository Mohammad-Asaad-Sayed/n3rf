---
name: n3rf-setup
description: Set up and run n3rf from a fresh clone. Use when the user points at the n3rf GitHub repo and asks to install/run it.
---

# n3rf setup

## Steps
1. Clone the repo if not present.
2. **Ask about the model provider before running:** which provider do they use, is a key
   already in the environment, or do they want a keyless local model (Ollama)? If they
   need a hosted provider, ask them to export the key in the shell that starts FastAPI
   (e.g. `export OPENAI_API_KEY=...`) or to create a `.env` from `.env.example` (gitignored,
   auto-loaded by `./scripts/run.sh`). n3rf never stores keys. **Do not accept a key pasted
   into the chat** — it ends up in the session transcript. If they insist, use it only as an
   ephemeral `POST /models/test` value and tell them to rotate it.
3. Run `./scripts/setup.sh`. It creates `.venv`, installs Python deps, installs frontend/site deps, builds both, and runs tests.
4. On success, run `./scripts/run.sh` and open http://127.0.0.1:8000.
5. Verify with `./scripts/verify.sh`. Confirm `GET /models/status` returns
   `{"ready": true, ...}` when a provider key is set, or say clearly that AI nodes will
   fail until one is — do not let the user discover it via a failed run.

## Checks
- Python >= 3.12 required.
- pnpm required (`npm i -g pnpm`).
- If setup fails, read the error and fix the missing tool; do not skip tests.

## Notes
- n3rf never stores API keys; keys live in the FastAPI process environment only.
- A pasted key may be used once for `POST /models/test` and is otherwise discarded —
  never write it to files, profiles, or memory.
- Ask for approval before creating or saving a model profile.
- Do not commit `frontend/dist`, `site/dist`, or `n3rf.sqlite3` (gitignored).
- License is AGPL-3.0; see LICENSE-NOTICE.md.
