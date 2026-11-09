# MVP architecture — AI-first workflow builder

**Scope:** LLM node · data-manipulation nodes · custom input nodes · code node.
**Constraint:** Python backend only.

---

## 1. The bet

n8n's moat is not its node count. It is the execution model plus the editor's
feel. Copying 400 integrations is a losing race; you cannot out-integrate them.
The winnable wedge is **AI-native data pipelines**: messy input in, structured
rows out, with your own model and your own key. That is a genuinely different
product from "Zapier with more triggers", and it needs maybe 20 nodes, not 400.

Two consequences shape every decision below:

1. **Rows are the unit, not events.** The whole product is ETL where one step
   happens to be an LLM call. Treat it as a data engine with an AI operator,
   not an automation engine with an AI step.
2. **Fan-out is the performance story.** 500 rows × one LLM call each is the
   normal case. Concurrency, retries, cost accounting and row caps are core
   features, not polish.

---

## 2. Five decisions that determine whether this works

### 2.1 The data contract

```
Every node receives list[Item] and returns list[Item].
Item = {json: dict, meta: dict}
```

`json` is the user's row. `meta` holds lineage (`paired` — which input row
produced this output row), the producing node, and error markers. Keeping them
apart means you can trace any output row back to its input without users seeing
engine bookkeeping, and without the "why is there a `__node__` field in my data"
complaint.

Nodes with more than one inbound connection also get `ctx.inputs[0..n]`. That
looks like it breaks the uniform contract; it does not. It is what lets **Merge**
and **Compare Datasets** work while every other node stays one-shape. Get this
wrong (one flat list, no ports) and Merge becomes impossible to implement
correctly. Each entry stays aligned with the node's declared input port, even
when a port is unconnected; ordinary one-input nodes receive the connected
upstream rows as their batch. The run response includes a JSON-only, 5-row input
sample per port so users can inspect the handoff in the node inspector.

**Do not use Pydantic models per node.** Rows are user-shaped and change per
workflow. `dict` with explicit coercion at the edges is right here.

### 2.2 Batch execution per node, not per row

The engine runs nodes in topological order; each node processes the whole batch
at once. Per-row execution feels natural and is 100× worse: you cannot express
Sort or Aggregate, you pay per-row overhead, and you cannot bound concurrency
across a batch.

Row-level parallelism belongs *inside* the node, where it can be a semaphore
around an `asyncio.gather`. That is exactly what `nodes/ai.py` does: one
`LLMClient` per node invocation, `concurrency=8` by default.

Corollary: **the engine is async, but nodes may be sync.** `engine._call` awaits
only if the result is awaitable. Write sync nodes for pure data work; nobody
should have to sprinkle `async` through a `set_fields`.

### 2.3 Declarative params → the UI is generated

```python
Param("output_mode", "string", "Output mode", default="per_input",
      options=[...], show_if={"param": "mode", "in": ["expand_arrays"]})
```

One declaration produces (a) the form the editor renders, (b) run-time
coercion and required-field validation, (c) the docs. `GET /nodes` returns the
whole catalog as JSON.
Params that accept incoming-row expressions declare `expression=True`; row
parameter columns can opt in the same way. The editor uses that metadata to offer
an `@` field picker without changing literal-only settings.
LLM nodes receive each incoming row automatically; their prompt can additionally
reference individual fields using the same expression picker.

This is the single highest-leverage decision in the codebase. If the frontend
hardcodes a form per node, adding node #21 costs a frontend PR and the product
gets slower to build every week. If it renders from the spec, adding a node is
one Python file.

### 2.4 The registry is the plugin boundary

`@node(...)` writes into a module-level `REGISTRY`. `registry.load_all()` imports
the node modules. That is the entire extension mechanism.

Keep it dumb for now. A `entry_points`-based plugin system is a real feature, but
it is a v2 feature — and it is much easier to add later than to remove.

### 2.5 BYOK, provider-agnostic LLM

`base_url` + `api_key` + `model`. Anything speaking OpenAI's
`/chat/completions` works: OpenAI, Groq, OpenRouter, Together, Ollama, vLLM, LM
Studio. Keys come from `api_key_env` by default so they never land in the
workflow JSON.

Do not build a per-provider adapter layer in the MVP. It buys nothing until you
hit a provider that is genuinely incompatible, and by then you will know which
one.

---

## 3. The four hard problems

### 3.1 The code node is remote code execution, by design

This is the largest risk in the product and the one most MVPs get wrong.

The scaffold uses a child process (`python -I -S`), an import allowlist, a
`sys.addaudithook` that blocks subprocess/socket/ctypes/file-writes, and
`RLIMIT_AS`/`RLIMIT_CPU`/`RLIMIT_NPROC`, with a parent-side wall-clock kill.

That is **adequate for self-hosted, single-tenant** use — the operator is the
same person running the code. It is **not adequate for a multi-tenant SaaS**.
Python-level sandboxes leak; audit hooks can be bypassed via C extensions; a
determined tenant will get out.

The real answer, in increasing order of cost:

| Option | Isolation | Cost | Verdict |
|---|---|---|---|
| subprocess + rlimits + audit hook | weak | free | MVP / self-hosted only |
| Pyodide (CPython in WASM) | strong, no syscalls | ~2s cold start, no native modules | **best SaaS default** |
| gVisor / Firecracker microVM | strong | ops burden, cold start | when you need full Python |
| Separate unprivileged container per run | strong | slowest | enterprise tier |

Recommendation: ship the subprocess sandbox for the MVP, and put Pyodide behind
the same `code` node interface before you let anyone but you sign up. Keep the
node's *contract* (list in, list out, `return` a list) identical across both so
the swap is invisible to users.

### 3.2 Expressions must never be `eval`

`{{ $json.name }}` is user input. `eval` on user input is game over.

`expressions.py` parses with `ast` and walks an allowlist of node types:
no imports, no dunder attributes, no calls except a curated function table
(`len`, `trim`, `lower`, `json_dumps`, `re_match`, `coalesce`, …). Subscripting
and attribute access go through a `_Safe` wrapper so `item.__class__` raises
rather than escaping.

The trade-off: users cannot write arbitrary Python in a template. That is
correct — that is what the Code node is for, and it has its own sandbox.

### 3.3 Fan-out cost and rate limits

A 500-row LLM node is 500 requests. Without controls you get: a 429 storm, a
$400 surprise, and a run that never finishes.

The LLM node therefore has `concurrency`, `max_output_rows`, per-item retries
with jittered backoff, and per-row error policy (`error_item` / `skip` / `fail`).
Token counts are accumulated into `ctx.metrics` — wire that to a cost meter
before you have users, because retrofitting cost attribution is painful.

### 3.4 Partial execution and resumability

Not solved in the MVP, and you should know that going in. A 5-minute run that
fails at node 9 re-runs nodes 1–8. n8n has the same behaviour and users live
with it, so this is a defensible cut — but it becomes urgent the moment someone
runs a 10k-row pipeline.

The design keeps the door open: every node's output is materialised and stored
in `ctx.node_outputs`, and a run is a sequence of pure `(params, items) -> items`
transitions. Adding "resume from a checkpoint" later means persisting that map,
not rewriting the engine.

---

## 4. Node set: what is in, what is out

Your list had 60+ nodes. The MVP ships 23 — the ones that make the AI pipeline
complete. Everything else is a plugin that can land after the engine is stable.

**In (shipped):** all 11 in-memory data nodes, all 7 custom input nodes, 4 AI
nodes (LLM Structured, AI Filter, AI Ranker, Semantic Dedup), and Code.

**Deliberately out of the MVP:**

| Cut | Why |
|---|---|
| Source/sink integrations (Sheets, Supabase, Notion, Slack…) | 30+ nodes of mostly-HTTP boilerplate. Each one is a week of OAuth + pagination + rate-limit handling and zero product differentiation. Ship **one** generic HTTP Request node instead and let users call anything. |
| Persistent Dedup / Lookup / Upsert | Needs Redis or a real store — infrastructure before product-market fit. |
| AI Ranker via a listwise prompt | Pairwise or per-item scoring is simpler, cheaper and more debuggable than "here are 50 rows, rank them". |
| Sub-workflows, loops, error branches | Real features, but they multiply the engine's complexity. A DAG is enough to prove the wedge. |
| Scheduling / webhooks / cron triggers | Out of scope until someone asks. `POST /workflows/{id}/run` is the trigger. |

One addition worth making early: a **generic HTTP Request node**. It is ~80 lines
and it converts "you don't have the integration I need" from a blocker into a
minor inconvenience.

---

## 5. Stack

| Layer | Choice | Why |
|---|---|---|
| HTTP | FastAPI + uvicorn | async, OpenAPI for free, matches the async engine |
| Engine | plain asyncio, in-process | no Celery/Redis until runs exceed ~60s |
| LLM | httpx.AsyncClient | one client, all providers |
| Validation | jsonschema | LLM output + node params |
| Storage | SQLAlchemy + SQLite + Alembic | ORM-backed CRUD and versioned schema migrations; `N3RF_DATABASE_URL` selects a supported database |
| Tests | pytest, mock provider | the whole suite runs offline in 5s |
| Self-hosted editor | React SPA with accessible shadcn-style primitives | FastAPI serves the production app and API from one origin |
| Public site | Separate React/Vite static build in `site/` | Marketing pages deploy independently and link to GitHub self-hosting instructions |

What is deliberately absent: Celery, Redis, Kafka, Docker-in-Docker, a Node
runtime, a queue, a message bus. Each one is a real answer to a problem you do
not have yet at MVP scale. In-process asyncio handles a surprising amount; move
to a worker queue when a single run routinely exceeds the HTTP timeout, not
before.

---

## 6. API surface

```
GET  /nodes                    catalog + param schemas -> the form UI
POST /run                      run an unsaved graph; optional target_node_id runs its upstream subgraph
POST /workflows/{id}/run       run a saved workflow
GET  /runs/{id}                per-node results, timings, row counts, logs
GET/POST/PUT /workflows        CRUD
POST /upload                   file -> base64 for the File Upload node
GET/POST /models               non-secret model provider profiles
POST /models/test              test provider `/models` endpoint
DELETE /models/{id}            delete a provider profile
```

The run response is the product. Per node: status, `ms`, `rows_in`, `rows_out`,
error, redacted diagnostic log entries, a 5-row input sample per input port, and a
5-row output sample. Run-level metrics include
LLM calls and token counts. The editor's Diagnostics view shows failures, timings,
row counts, metrics, and redacted logs. Raw exception text is never included in logs.
Users debug pipelines by looking at row counts dropping between nodes; if you do not
show that, they will not trust the tool.
The editor's per-node Run action sends `target_node_id`; the backend executes only
that node and its ancestors, stopping before downstream nodes. Partial runs are not
added to full workflow run history.

```json
{"run_id": "...", "status": "success", "ms": 108,
 "nodes": [{"id": "extract", "status": "success", "rows_in": 3, "rows_out": 3, "ms": 23}],
 "output": [...], "metrics": {"llm_calls": 3}}
```

---

## 7. Frontend and UI/UX

The production interface is a React + Vite application served by FastAPI. Its
home page lists saved workflows, while model settings provide OpenAI-compatible
provider profiles and connection checks. The decisions worth defending are these.

**The results panel is half the product.** Workflow tools are debugging tools
with a canvas attached. Users do not study their graph, they ask "why did my
data disappear between step 3 and step 4". So per node you show
`rows_in → rows_out` and duration, with a click-through to sample rows. The `3 →
2` is the number that earns its place: scanning a list that goes `500 → 12` at
the Filter node locates the problem without opening anything. Most builders give
you a raw JSON dump here and users end up inserting a log node to find out what
happened.

**The form is generated, never hand-written.** This is the frontend half of §2.3
and the reason collection params now carry nested `fields`. `GET /nodes` gives
type, options, defaults and `show_if`; the inspector renders selects, toggles,
validated JSON textareas and repeatable row editors from that alone. Adding node
#24 stays one Python file with no frontend change. Two rules that matter more
than they look: never re-render the form on keystroke (it steals focus and moves
the caret), and resolve `show_if` by toggling `display`, not rebuilding.

**Three adjustable panes, no modals.** The node library and inspector can be
collapsed, their widths can be resized, and run results can be collapsed or
resized below the canvas. Users can reclaim canvas area without losing the
current workflow state. Results stay under the canvas because they belong to
the *run*, not the selected node, and the useful comparison is `node 3 → 4 → 5`.

**Canvas.** Drag from the output port to an input port; clicking an edge deletes
it. Multi-input nodes (Merge, Compare Datasets) get two ports labelled `A` and
`B` — that visual is the only thing telling a user which branch is which. Group
colour is the only chrome: cyan input, violet transform, pink AI, amber code, as
a 3px bar plus a dot. No icons to learn. `⌘↵` runs, `Delete` removes. The demo
opens at 85% zoom, never lower: five readable nodes beat seven at a scale nobody
can read.

**State honesty.** No selection → a one-line hint, not an empty box. No run →
"run the workflow to see per-node results". Node failed → red border, error on
the card, error box in results; there is no separate error view, because errors
belong where the node is. Backend unreachable → the editor simulates the run so
the UI stays explorable, but says so three ways: amber banner, amber connection
LED, and `· simulated` in the run meta. A prototype that quietly fakes results
is worse than one that shows nothing.

**Provider credentials.** Profiles store only the provider URL, model name and
environment-variable name. The API key stays in the FastAPI process environment.
Connection checks call `/models` without sending a prompt or consuming tokens.

**Deliberately absent:** undo/redo, multi-select, copy/paste, minimap,
auto-layout, versioning, collaboration, mobile. All real, none of them what you
need to learn whether this interaction model works. The first thing to add
back is **per-node test** — run one step against the previous node's output. It
turns a 30-second debug loop into a 2-second one, and `POST /run` with a
truncated graph plus an input override already supports it.

---

## 8. Build order

**Week 1 — the spine.** Contracts, params, registry, expressions, engine, and
the 11 data nodes. No AI, no UI. Target: a 6-node pipeline that passes tests.

**Week 2 — the wedge.** `llm.py` + LLM Structured with real schema validation and
repair, AI Filter/Ranker, the mock provider, and the Code node with its sandbox.
Target: the demo in `examples/demo.py` running against a real model.

**Week 3 — the surface.** FastAPI, SQLAlchemy + SQLite, run history, and the editor. The
editor is the expensive part: node palette, connection drawing, per-node form
rendered from `GET /nodes`, and a results panel driven by the run response.
Budget two weeks here, not two days. The production editor includes the node
palette, canvas, generated inspector, run results, workflow home page, and model
settings.

**Week 4 — the edges.** File upload, the generic HTTP node, error policies,
cost meter, and a real workflow or two of your own to dogfood.

---

## 9. What to watch

- **Row-count visibility.** The most common support question in every workflow
  tool is "why did my data disappear". Show `rows_in`/`rows_out` on every node
  and sample rows at each step. It costs nothing and saves your users hours.
- **Schema validation, not just JSON mode.** `response_format: json_object`
  gives you *valid JSON*, not *your JSON*. The repair loop — validate, re-prompt
  with the error — is what turns an LLM node from a toy into a reliable operator.
- **`max_output_rows` on every fan-out node.** `expand_arrays` on a model that
  decides to return 4,000 elements is a real incident.
- **Idempotency before webhooks.** The moment runs are triggered externally you
  need dedupe on run keys, or a retrying caller doubles your LLM bill.
- **Keep `meta` out of the user's data.** The day you leak `_paired` into a
  Google Sheets sink is the day you find out how much people care about their
  column names.
