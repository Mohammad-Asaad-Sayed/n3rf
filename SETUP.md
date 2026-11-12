# Setup (agent-friendly)

One command on a fresh clone:

```bash
./scripts/setup.sh
```

Then run:

```bash
./scripts/run.sh
```

Open http://127.0.0.1:8000.

## Requirements
- Python >= 3.12
- Node.js + pnpm (`npm i -g pnpm` or `corepack enable`)

## Verify
```bash
./scripts/verify.sh
```

## Troubleshooting
- Port in use: `PORT=8001 ./scripts/run.sh`
- Missing pnpm: install Node.js, then `npm i -g pnpm`
- Database path: set `N3RF_DB_PATH` before running
- Backend only: `uvicorn app.main:app --port 8000`
