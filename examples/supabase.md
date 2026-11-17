# Supabase with n3rf — the Magi decision log

Two moves, both sanctioned:

1. **The HTTP Request node covers anything** — the catch-all stays the default answer.
2. **The opt-in Supabase pack** — three nodes when raw PostgREST is too fiddly for operators:
   `Supabase Select`, `Supabase Upsert`, `Supabase RPC`.

Keys come from the environment — `SUPABASE_URL` and `SUPABASE_API_KEY` (service-role key for
server-side jobs; anon key only when RLS permits). No keys are ever written into workflow JSON.

## Setup

```bash
export SUPABASE_URL="https://xyz.supabase.co"   # your project URL
export SUPABASE_API_KEY="eyJhbGciOi…"           # service_role or anon key
uvicorn app.main:app --port 8000
```

## Table

```sql
create table decisions (
  id bigint generated always as identity primary key,
  thread_id text not null,
  asked_by text,
  path text not null check (path in ('answer', 'ask', 'route')),
  cited_kb text,
  confidence text,
  created_at timestamptz default now(),
  unique (thread_id)
);
```

## Workflow shape — log a decision

```text
Manual JSON  →  Ask AI (triage)  →  Set Fields  →  Supabase Upsert  →  Slack Send Message
 [{"question": "what's our line on…"}]   [{"path": "answer", "cited_kb": "positioning", "thread_id": "1700000.1"}, …]
```

`Supabase Upsert` params: table `decisions`, on conflict `thread_id` (merges the row on re-run
instead of duplicating).

## Read it back

`Supabase Select`: table `decisions`, columns `path,cited_kb,thread_id`,
filter `path=eq.answer&cited_kb=not.is.null`, limit 100.

## Call logic in the database

`Supabase RPC`: function `log_decision` (a Postgres function you own), payload `{}` —
or with @ picks for per-row arguments, e.g. `{"p_thread_id": "@thread_id"}`.

## Troubleshooting

- `Supabase request failed: 401` — the key is wrong or expired; both headers (`apikey`,
  `Authorization`) must pass. The service-role key bypasses RLS; the anon key does not.
- `Supabase request failed: 404` — table name, or function name for RPC.
- `Supabase request failed: 400 ... column ... does not exist` — your `filter` references a
  column that isn't in the table; `filter` is a *PostgREST filter string* (value-first query
  params), not SQL.
- Self-hosted Supabase on a private address is rejected by the SSRF guard (same rule the
  HTTP Request node enforces) — keep the instance on a public URL or use it via the HTTP node.

## Not in the pack

CRUD beyond Select/Upsert (conditional updates, deletes), pagination, and realtime subscriptions
are deliberate omissions — drop to the HTTP Request node for those.
