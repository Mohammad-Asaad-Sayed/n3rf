# n3rf

n3rf is a local-first, AI-assisted workflow builder: messy input in, structured rows out.
Workflows run against your own OpenAI-compatible endpoint and API key.

## Run locally

Once set up (below), start everything with one command — Uvicorn serves the built React
frontend and the API from the same origin on port 8000:

```bash
cd ~/Downloads/n3rf && .venv/bin/uvicorn app.main:app --reload --port 8000
```

Open the served app at http://127.0.0.1:8000 (OpenAPI at `/docs`). Full setup:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
cd frontend
pnpm install
pnpm run build
cd ..
uvicorn app.main:app --reload --port 8000
```

Open <http://127.0.0.1:8000>. FastAPI serves the production React editor and API from one origin.
The workspace links to a product landing page at `/#/landing`; sample report figures are clearly
marked as prepared example data. The hero lazily loads Three.js for its point-cloud signal field,
with a static EVA-01 fallback when WebGL is unavailable, on small screens, or with reduced motion.
Dropping a CSV there opens it as a CSV File node in the editor.
For frontend development, start FastAPI on port 8000 and run `cd frontend && pnpm dev`; Vite
proxies API requests to FastAPI. The catalog is generated from the Python node registry at
`GET /nodes`. For AI nodes, set `OPENAI_API_KEY` in the environment (or change the node's
`api_key_env`). Keys are never saved with workflows.
Sensitive HTTP headers use an environment reference such as `${ENV:MY_SERVICE_TOKEN}`; literal
authorization/key/token/secret headers are rejected so credentials do not enter saved workflows.
See [SECURITY.md](./SECURITY.md) for vulnerability reporting and deployment security notes.

## Project layout and data

- `app/` is the Python backend package: FastAPI routes live in `app/api/`, request schemas in
  `app/schemas/`, execution services in `app/services/`, and workflow nodes in `app/nodes/`.
- `frontend/` contains the React + Vite editor.
- FastAPI, SQLAlchemy 2, and SQLite are the backend stack. SQLAlchemy keeps persistence typed
  and lets the app use another SQLAlchemy-supported database via `N3RF_DATABASE_URL` when its
  database driver is installed.
- SQLite data is stored in the project-root `n3rf.sqlite3` by default, independent of the
  directory used to launch Uvicorn. It stores workflows, run history, and non-secret model
  profiles and is excluded from Git. Set `N3RF_DB_PATH` to use another SQLite file; it is
  ignored when `N3RF_DATABASE_URL` is set.
- Model profiles save the provider URL, model name, and API-key environment-variable name.
  The secret itself remains in the FastAPI process environment. The connection test checks the
  provider's `/models` endpoint without sending a prompt.

Run offline checks with:

```bash
pytest -q
ruff check app tests
ruff format --check app tests
cd frontend && pnpm run build
```

The Code node runs in a resource-limited child process and is intended only for a trusted,
single-operator deployment; this MVP is not a multi-tenant security boundary.

## API

- `GET /nodes` — generated node catalog
- `POST /run` — execute an unsaved graph; optionally pass `target_node_id` to execute that node
  and its upstream dependencies without running downstream nodes
- `GET/POST /workflows`, `PUT/DELETE /workflows/{id}` — workflow persistence
- `POST /workflows/{id}/run` — execute a saved workflow
- `GET /runs/{id}` — persisted run output
- `POST /upload` — base64-encode a file up to 10 MB
- `GET/POST /models` — list and save OpenAI-compatible provider profiles
- `POST /models/test` — check a provider's model-list endpoint and selected model
- `DELETE /models/{id}` — remove a provider profile

Every node exchanges `list[Item]`, where an `Item` separates user `json` from engine `meta`.
The Code node is isolated from the API process, but its Python sandbox is not suitable for
untrusted multi-tenant workloads. Simulated editor output is explicitly labeled when the API is
unavailable.
