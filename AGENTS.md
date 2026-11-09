# AGENTS.md

Working agreement for any AI coding agent (Claude Code, Codex, Cursor, etc.) operating in
this repository. Read this file before your first edit. It is short on purpose: it holds only
the rules that, if broken, produce code that looks fine and is wrong.

**Product:** n3rf — an AI-first workflow builder. Messy input in, structured rows out, on the
user's own model and key.

**Doc map.** `PRD.md` (what and why) · `ARCHITECTURE.md` (how) · `PLAN.md` (in what order) ·
`TASKS.md` (the executable list) · `EVA01-DESIGN.md` + `eva01-tokens.css` (how it looks).

When the docs disagree, the order of authority is: this file → `ARCHITECTURE.md` → `PRD.md` →
`PLAN.md` → `TASKS.md`. If you find a real contradiction, fix the lower doc rather than
working around it.

---

## 1. The seven invariants

Break any of these and the product is wrong, even if every test passes.

1. **Rows are the unit.** Every node receives `list[Item]` and returns `list[Item]`, where
   `Item = {"json": dict, "meta": dict}`. Multi-input nodes additionally get `ctx.inputs[0..n]`.
2. **`meta` never appears in `json`.** Lineage, error markers and engine bookkeeping live in
   `meta`. The day a `_paired` key reaches a user's export is the day you learn how much
   people care about their column names.
3. **Batch per node, not per row.** The engine hands each node the whole batch. Row-level
   parallelism is a semaphore around `asyncio.gather` *inside* a node.
4. **Params are declared, never hand-coded.** A `Param(...)` declaration produces the form, the
   coercion, the validation and the docs. If you write a form in the frontend for one node,
   you have broken the extension model.
5. **No `eval`, ever.** `{{ $json.x }}` is user input and goes through the `ast` walker in
   `expressions.py`. The Code node is the only place user code runs, and it has its own
   sandbox.
6. **No raw values in the UI.** Colours, sizes, radii and spacing come from EVA-01 custom
   properties. A hex code outside `eva01-tokens.css` is a bug. One exception exists and is
   commented in place: the canvas grid dot `#5A4691`.
7. **No silent fakes.** If the backend is unreachable the editor simulates the run and says so
   three ways: amber banner, amber connection LED, `· simulated` in the run meta. A prototype
   that quietly fabricates results is worse than one that shows nothing.

---

## 2. Repository layout

```
app/
  main.py            FastAPI application factory and static frontend integration
  api/
    nodes.py         health and generated node catalog
    runs.py          workflow execution and run history endpoints
    workflows.py     workflow persistence endpoints
    models.py        provider profiles and connection test
    upload.py        bounded file upload endpoint
  schemas/
    workflow.py      request schemas
  services/
    execution.py     graph validation and workflow execution
  database.py       SQLAlchemy engine and declarative base
  models.py         SQLite ORM records
  engine.py          topological execution, RunContext, per-node metrics
  contracts.py       Item, ItemList, coercion at the edges
  params.py          Param, show_if resolution, validation
  registry.py        @node decorator, REGISTRY, load_all()
  expressions.py     {{ }} — ast allowlist, _Safe wrapper
  llm.py             httpx client, concurrency, retries, repair loop
  store.py           workflow, run, and model-profile persistence
  nodes/
    __init__.py      imports every node module so @node registers
    input.py         the 7 input nodes
    data.py          the 11 transform nodes
    ai.py            the 4 AI nodes
    code.py          the sandboxed Code node
  sandbox.py         child process, rlimits, audit hook
  static/
    eva01-tokens.css shared design tokens
frontend/
  src/
    components/ui/   shadcn-style accessible primitives
    styles/          EVA-01 editor styling
    App.tsx          home page, model settings, and workflow editor
  package.json       frontend tooling and dependencies
tests/
  test_engine.py test_nodes.py test_expressions.py test_llm.py test_api.py
examples/
  demo.py            a real 6-node pipeline against a real model
docs/                PRD.md, ARCHITECTURE.md, PLAN.md, TASKS.md, EVA01-DESIGN.md
```

Do not add a directory without updating this map.

---

## 3. Run and verify

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

uvicorn app.main:app --reload --port 8000     # API on :8000, /docs for OpenAPI
# or, in one line from the project root (serves frontend dist + API together):
.venv/bin/uvicorn app.main:app --reload --port 8000
python examples/demo.py                       # end-to-end against a real model
pytest -q                                     # must stay under 10s, fully offline
ruff check app tests && ruff format --check app tests
```

Open http://127.0.0.1:8000. FastAPI serves the production React editor and API from one
origin; the OpenAPI docs are at http://127.0.0.1:8000/docs.

Build the React editor with `cd frontend && pnpm install && pnpm run build`. FastAPI serves the
production build at `/`; during development, run Vite with `pnpm dev` and FastAPI separately.

**Verification before you claim a task is done:** `pytest -q` green, `ruff check` clean, and
the editor loads with no console errors. If you touched anything user-facing, also confirm the
run → results → sample path still works.

---

## 4. The golden path: adding a node

Adding a node must stay a one-file, backend-only change. The generated inspector reads each
node's parameter schema from `GET /nodes`; node-specific frontend forms are not allowed.

1. Create `Node` metadata and params in the right module under `app/nodes/`.
2. Decorate the function with `@node(...)`; write the params as `Param(...)` declarations,
   including `show_if` for anything conditional.
3. Implement the body as `def run(items, ctx) -> list[Item]`. Sync is fine. Only make it
   `async` if it genuinely awaits I/O.
4. Coerce and validate params with the helpers in `params.py` — do not read `ctx.params`
   raw and do not invent your own defaults.
5. Handle the error policy (`error_item` / `skip` / `fail`) for anything that fans out.
6. Add a test in `tests/test_nodes.py`: happy path, empty input, and one bad param.

```python
@node("filter", "Filter", group="transform",
      description="Keep only rows whose condition is true.")
def filter_node(items, ctx):
    cond = ctx.param("condition", str, required=True)
    keep_empty = ctx.param("keep_empty", bool, default=False)
    out = []
    for item in items:
        try:
            ok = evaluate(cond, item["json"])
        except ExpressionError:
            if keep_empty:
                out.append(item)
            continue
        if ok:
            out.append(item)
    return out
```

---

## 5. Code conventions

**Python.** 3.12. Type hints on public functions. `dict` rows, no per-node Pydantic models —
rows are user-shaped and change per workflow. Prefer pure functions; a node that touches the
network or the filesystem is the exception and must say so in its docstring. Raise
`NodeError` with a user-readable message; never let a bare exception reach the run response.

**Engine.** The engine is async, nodes may be sync: `_call` awaits only when the result is
awaitable. Never `asyncio.run` inside a node.

**Frontend.** React with accessible shadcn-style primitives. Rendering rules that are not
negotiable:

- Never re-render the inspector form on keystroke — it steals focus and moves the caret. Write
  to state, then update only the node card summary.
- Resolve `show_if` by toggling `display`, never by rebuilding the subtree.
- Structural changes (add/remove node or edge) may re-render the canvas; edits may not.

**CSS.** Custom properties only. Every border 1px (2px only for accent rules and brackets),
radii 1–3px, control heights from the scale, no ad-hoc font sizes. Uppercase only on labels
and titles of ~24 characters or fewer, always with positive tracking.

**Naming.** Keep the product's words: node, row, run, workflow, inspector, palette, results.
Never rename an entity for flavour, and never introduce lore-flavoured copy.

---

## 6. Testing rules

- The suite runs **offline**. The LLM is mocked through `tests/mock_provider.py`; no test may
  hit a network.
- Every node has three tests: happy path, empty input, one invalid param.
- The engine has tests for: topological order, a diamond graph, a node that raises, a node
  that returns nothing, and multi-input `ctx.inputs` ordering (A before B).
- `expressions.py` has a security test file: imports, dunder access, `__class__`, attribute
  traversal and calls outside the allowlist must all raise.
- A failing test is never fixed by loosening an assertion. Fix the code, or change the
  requirement in `PRD.md` first and say so.

---

## 7. Pull-request checklist

Copy this into the PR description and tick it honestly.

- [ ] `pytest -q` green, `ruff check` clean.
- [ ] No new dependency without a note in the PR saying why the standard library could not do it.
- [ ] If a node was added: one Python file changed, zero frontend changes, three tests added.
- [ ] If a param was added: `type`, `label`, `default`, and `show_if` where conditional.
- [ ] No `meta` key can reach `json`; no `eval`, `exec`, or `pickle` on user input.
- [ ] No secret, key or token in code, tests, logs or workflow JSON.
- [ ] If the UI changed: tokens only, accent budget respected (green ≤ 3 per screen), hover /
      focus / active / disabled states present, `prefers-reduced-motion` respected.
- [ ] If a run-response field changed: frontend response types and result rendering updated.
- [ ] The relevant doc (`PRD.md` / `ARCHITECTURE.md` / `TASKS.md`) updated in the same PR.

---

## 8. Ask a human before

- Changing the data contract, the engine's execution model, or the `Param` schema. These are
  load-bearing and every node depends on them.
- Adding a node that talks to a third-party service. The MVP ships one generic HTTP node
  instead of integrations, deliberately.
- Introducing a queue or cache. Each is a real answer to a problem this project does not have yet.
- Adding an ORM or database layer beyond SQLAlchemy and the current single-database setup.
- Anything that changes how the Code node is isolated, or that would run user code in the API
  process.
- Deleting or renaming a public endpoint, or a field in the run response.

---

## 9. Things that have already been decided — do not re-litigate

| Decision | Why |
|---|---|
| Plain dicts, no per-node Pydantic | Rows are user-shaped; models fight that |
| Sync nodes allowed in an async engine | `async` in a `set_fields` is pure noise |
| Generated forms, no per-node UI | Node #24 must cost one Python file |
| Module-level `REGISTRY`, no entry_points | Plugin system is a v2 feature, easy to add later |
| In-process asyncio, no Celery/Redis | Runs under ~60s; a queue is premature |
| Vanilla JS single-file editor | The interaction model is still moving |
| No integrations, one generic HTTP node | Out-integration n8n is a losing race |
| No minimap, multi-select, mobile | None of them test the interaction model |
| Canvas undo/redo (nodes+edges only) | Structural history was the top papercut; param text keeps native input undo so keystroke safety holds |

If you believe one of these is now wrong, write the argument in the PR body — do not quietly
implement around it.
