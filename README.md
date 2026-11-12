# n3rf

n3rf is a self-hosted, AI-assisted workflow builder: messy input in, structured rows out.
Run it on your own machine with your chosen OpenAI-compatible endpoint and API key.

The public marketing site is a separate static app in [`site/`](./site/). Its install links
lead here to the [self-hosting guide](./docs/self-hosting.md); it does not host a n3rf workspace.

## Run locally

Once set up (below), start everything with one command — Uvicorn serves the built React
workspace and the API from the same origin on port 8000:

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

Open <http://127.0.0.1:8000> for the self-hosted workspace (the OpenAPI docs are at `/docs`).
The public site is built and deployed separately. For local app development, start FastAPI on
port 8000 and run `cd frontend && pnpm dev`; Vite proxies API requests to FastAPI. For site
development, run `cd site && pnpm dev`. The node catalog is generated from the Python registry
at `GET /nodes`. For AI nodes, set `OPENAI_API_KEY` in the environment (or change the node's
`api_key_env`). Keys are never saved with workflows.
Sensitive HTTP headers use an environment reference such as `${ENV:MY_SERVICE_TOKEN}`; literal
authorization/key/token/secret headers are rejected so credentials do not enter saved workflows.
See [SECURITY.md](./SECURITY.md) for vulnerability reporting and deployment security notes.

## License

n3rf is licensed under the [GNU Affero General Public License v3.0](./LICENSE)
(AGPL-3.0-only). See [LICENSE-NOTICE.md](./LICENSE-NOTICE.md) for a
plain-language summary. A separate commercial license may be available for
embedding n3rf in a closed-source or proprietary product.

## Project layout and data

- `app/` is the Python backend package: FastAPI routes live in `app/api/`, request schemas in
  `app/schemas/`, execution services in `app/services/`, and workflow nodes in `app/nodes/`.
- `frontend/` contains the self-hosted React + Vite workspace served by FastAPI.
- `site/` contains the independently built React + Vite marketing site. It emits standalone
  entry pages for the homepage, legal information, and Claygent comparison into `site/dist/`.
- `docs/self-hosting.md` explains installation, provider configuration, persistence, and backups.
- FastAPI, SQLAlchemy 2, and SQLite are the backend stack. SQLAlchemy keeps persistence typed
  and lets the app use another SQLAlchemy-supported database via `N3RF_DATABASE_URL` when its
  database driver is installed. Alembic migrations run automatically when the backend first
  opens the database; add future schema changes as revisions under `migrations/versions/`.
- SQLite data is stored in the project-root `n3rf.sqlite3` by default, independent of the
  directory used to launch Uvicorn. It stores workflows, run history, and non-secret model
  profiles and is excluded from Git. Set `N3RF_DB_PATH` to use another SQLite file; it is
  ignored when `N3RF_DATABASE_URL` is set.
- To apply migrations manually, run `alembic upgrade head` from the project root. Existing
  databases created by earlier n3rf versions are adopted by the initial migration without
  dropping their saved workflows, run history, or model profiles.
- Model profiles save the provider URL, model name, and API-key environment-variable name.
  The secret itself remains in the FastAPI process environment. The connection test checks the
  provider's `/models` endpoint without sending a prompt.

Run offline checks with:

```bash
pytest -q
ruff check app tests
ruff format --check app tests
cd frontend && pnpm run build
cd ../site && pnpm install && pnpm run build
```

The marketing site can be deployed from `site/dist` without deploying the API. The self-hosted
app is built from `frontend/dist` and served with FastAPI. When publishing the marketing site
under a subpath, configure its static host/base path accordingly.

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
