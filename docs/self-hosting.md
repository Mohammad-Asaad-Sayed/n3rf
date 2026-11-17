# Self-host n3rf

n3rf is a local-first workflow builder. The public website is only the product site; it does not
run workflows or store user data. Install this repository to run the app on a machine you control.

## Requirements

- Python 3.12
- Node.js and pnpm

## Install and start

The fastest path is the one-command setup — it checks tooling, creates the venv, builds the
frontend and runs the test suite:

```bash
git clone https://github.com/Mohammad-Asaad-Sayed/n3rf.git
cd n3rf
./scripts/setup.sh
./scripts/run.sh
```

Or do it manually:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt

cd frontend
pnpm install
pnpm run build
cd ..

.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000>. Keep the service bound to localhost unless you have configured
appropriate network access controls. The app and API are served together by FastAPI; the public
marketing site is not required to run it.

## Configure a model provider

Set the environment variable named by the provider profile's `api_key_env` before starting
Uvicorn. For example:

```bash
export OPENAI_API_KEY="your-provider-key"
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Or copy `.env.example` to `.env`, fill in the keys you use, and start via
`./scripts/run.sh`, which loads `.env` automatically (KEY=value lines only; the file is
gitignored and must never be committed).

Add a provider profile in **Models** using its OpenAI-compatible base URL, model name, and the
environment-variable name. The profile stores its configuration, not the secret value. Model
and search providers may separately charge for their services.

## Workflows, history, and backups

By default, SQLite data is stored in `n3rf.sqlite3` at the repository root. It contains saved
workflows, run history, and non-secret model profiles. Browser local storage contains an
auto-recovery draft and editor pane widths; it is not a backup of the database.

Set `N3RF_DB_PATH` to use a different SQLite file, or `N3RF_DATABASE_URL` for another
SQLAlchemy-supported database with its driver installed. Alembic migrations run automatically
when the backend first opens the database.

Back up the database regularly. The supported way — consistent even while n3rf is running — is:

```bash
python examples/backup.py backups/
```

It uses SQLite's online backup API, so there is no need to stop the app. Set `N3RF_DB_PATH` to
back up a non-default database file. Copying `n3rf.sqlite3` by hand is only guaranteed to be
consistent when n3rf is stopped first. Store backups somewhere separate from the machine
hosting n3rf and protect them as carefully as workflow data.

## Updating

Pull the latest repository changes, install any updated Python dependencies, rebuild the
workspace frontend, and restart the app:

```bash
git pull
.venv/bin/pip install -r requirements-dev.txt
cd frontend
pnpm install
pnpm run build
```

Database migrations are applied automatically on the next backend start.
