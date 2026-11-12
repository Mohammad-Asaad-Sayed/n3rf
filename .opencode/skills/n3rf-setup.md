---
name: n3rf-setup
description: Set up and run n3rf from a fresh clone. Use when the user points at the n3rf GitHub repo and asks to install/run it.
---

# n3rf setup

## Steps
1. Clone the repo if not present.
2. Run `./scripts/setup.sh`. It creates `.venv`, installs Python deps, installs frontend/site deps, builds both, and runs tests.
3. On success, run `./scripts/run.sh` and open http://127.0.0.1:8000.
4. Verify with `./scripts/verify.sh`.

## Checks
- Python >= 3.12 required.
- pnpm required (`npm i -g pnpm`).
- If setup fails, read the error and fix the missing tool; do not skip tests.

## Notes
- Do not commit `frontend/dist`, `site/dist`, or `n3rf.sqlite3` (gitignored).
- License is AGPL-3.0; see LICENSE-NOTICE.md.
