# TASKS.md — n3rf

The executable list. Tick as you go; do not reorder across phases without reading `PLAN.md` §4.
Estimates are for one experienced developer, full-time, and are for *sequencing*, not for
promising.

IDs are stable — reference them in commits (`T-014: add filter node`) and in PR descriptions.
`FR-xx` points at the requirement in `PRD.md` the task satisfies.

Legend: `[ ]` todo · `[~]` in progress · `[x]` done · `[!]` blocked

---

## M0 — Spine (week 1)

**Contracts and params**

- [x] **T-001** `contracts.py`: `Item`, `ItemList`, `new_item()`, `paired()` helpers. Document
      the `json` / `meta` split in the module docstring. · FR-18 · 3h
- [x] **T-002** `params.py`: `Param` dataclass with `key, label, type, default, options, unit,
      required, show_if, columns, hint`. · FR-01 · 3h
- [x] **T-003** `params.py`: coercion per type (string, textarea, number, boolean, select, json,
      code, rows, file), raising `NodeError` with the field name. · FR-16 · 4h
- [x] **T-004** `params.py`: `resolve_show_if(params)` returning the effective visible set, used
      by both validation and `GET /nodes`. · FR-07 · 2h
- [ ] **T-005** `tests/test_params.py`: coercion matrix, required, json parse failure, number
      out of range, `show_if` on/off. · FR-16 · 3h

**Registry**

- [x] **T-006** `registry.py`: `NodeSpec`, `@node(...)` decorator, module-level `REGISTRY`,
      `load_all()`. · FR-01 · 3h
- [ ] **T-007** `tests/test_registry.py`: duplicate id rejected, `load_all()` idempotent, every
      node has a group and a description. · FR-01 · 1h

**Expressions**

- [x] **T-008** `expressions.py`: `ast` parser, node allowlist, curated function table, `_Safe`
      wrapper, template-vs-interpolation split. · FR-23 · 6h
- [ ] **T-009** `tests/test_expressions.py` (security): imports, dunder access, `__class__`,
      attribute traversal, comprehension, lambda, unknown call — all must raise. · FR-23 · 4h

**Engine**

- [x] **T-010** `engine.py`: topological sort with cycle detection that names the nodes. ·
      FR-10 · 3h
- [x] **T-011** `engine.py`: `RunContext` (`params`, `inputs`, `node_outputs`, `metrics`, `log`).
      · FR-17 · 3h
- [x] **T-012** `engine.py`: batch walk, `_call` awaiting only awaitables, per-node timing,
      error policy (`error_item` / `skip` / `fail`). · FR-12, FR-15 · 5h
- [ ] **T-013** `tests/test_engine.py`: linear, diamond, disconnected node, raising node, empty
      output, `ctx.inputs` ordering A before B. · FR-12 · 5h

**Nodes — input (7)** · FR-18

- [x] **T-014** `manual_json` — parse a JSON array into items; invalid JSON is a readable error. · 2h
- [x] **T-015** `text_lines` — one row per line; split on line / comma / tab. · 2h
- [x] **T-016** `csv_file` — parse CSV text; delimiter; header row on/off. · 3h
- [x] **T-017** `file_upload` — base64 payload → items; encoding option. · 2h
- [x] **T-018** `spreadsheet_paste` — TSV block → items; header on/off. · 2h
- [x] **T-019** `field_builder` — rows param of `{name, type}` → a single item. · 2h
- [x] **T-020** `example_dataset` — three seeded datasets, row count param. · 2h

**Nodes — transform (11)** · FR-19

- [x] **T-021** `filter` — expression per row; `keep_empty` for evaluation failures. · 3h
- [x] **T-022** `sort` — field, asc/desc, numeric vs string comparison. · 3h
- [x] **T-023** `limit` — max + offset. · 1h
- [x] **T-024** `set_fields` — rows param of `{name, value}`, values may be expressions. · 3h
- [x] **T-025** `remove_fields` — comma list. · 1h
- [x] **T-026** `rename_fields` — rows param of `{from, to}`. · 2h
- [x] **T-027** `aggregate` — group by + rows param of `{field, op, as}`; ops count/sum/avg/min/max;
      `paired` becomes a list. · 5h
- [x] **T-028** `expand_arrays` — array field → one row per element; `max_output_rows` enforced;
      `paired` copied to every output row. · 4h
- [x] **T-029** `merge` — `inputs=2`; append and merge-by-key modes. · 4h
- [x] **T-030** `compare_datasets` — `inputs=2`; inner / left_only / right_only on a key. · 4h
- [x] **T-031** `dedupe` — field, keep first/last. · 2h
- [ ] **T-032** `tests/test_nodes.py` — happy path, empty input, one bad param for **every**
      node above. · 6h

**M0 exit** — [ ] the 6-node pipeline test passes; suite offline under 10s; `ruff` clean.

---

## M1 — Wedge (week 2)

**LLM**

- [x] **T-033** `llm.py`: `httpx.AsyncClient`, BYOK (`base_url`, `api_key_env`, `model`), one
      client per node invocation. · FR-28 · 4h
- [x] **T-034** `llm.py`: semaphore concurrency, jittered exponential retries, timeout, token
      accounting into `ctx.metrics`. · FR-17, NFR-01 · 5h
- [x] **T-035** `llm.py`: schema validation with `jsonschema` + single repair attempt carrying
      the validation error back to the model. · FR-20 · 6h
- [x] **T-036** `tests/mock_provider.py`: deterministic responses, injectable malformed output,
      injectable 429, latency simulation. · NFR-04 · 4h
- [ ] **T-037** `tests/test_llm.py`: repair loop repairs; second failure applies the error
      policy; concurrency cap observed; tokens accumulated. · FR-20 · 4h

**AI nodes** · FR-20, FR-21

- [x] **T-038** `llm_structured` — both output modes, `max_output_rows`, `on_error`, schema param. · 5h
- [x] **T-039** `ai_filter` — keep-by-criterion per row. · 3h
- [x] **T-040** `ai_ranker` — per-row score then top-N; score written to `score_field`. · 4h
- [x] **T-041** `semantic_dedup` — embedding call, cosine threshold, keep first. · 5h

**Code node** · FR-22

- [x] **T-042** `sandbox.py`: child process `python -I -S`, JSON over a pipe, parent wall-clock
      kill. · 5h
- [x] **T-043** `sandbox.py`: import allowlist, `sys.addaudithook` blocking subprocess / socket /
      ctypes / file writes, `RLIMIT_AS` / `RLIMIT_CPU` / `RLIMIT_NPROC`. · 6h
- [x] **T-044** `nodes/code.py` — `items` in, `return` a list out; timeout param; readable error
      when the sandbox refuses. · 3h
- [ ] **T-045** `tests/test_sandbox.py`: socket open, file write, `os.system`, infinite loop,
      memory bomb — each must fail cleanly and fast. · 5h

**Demo**

- [ ] **T-046** `examples/demo.py` — 6-node pipeline against a real model, prints per-node row
      counts. · 3h

**M1 exit** — [ ] demo runs on a real key; malformed response repaired; 50-row node respects caps.

---

## M2 — Surface (weeks 3–4)

**API**

- [x] **T-047** `main.py`: app skeleton, `GET /nodes` from the registry. · FR-01 · 3h
- [x] **T-048** `main.py`: `POST /run` — validate, execute, return the run response shape. ·
      FR-10, FR-12 · 4h
- [x] **T-049** `main.py`: `POST /workflows/{id}/run`, `GET /runs/{id}`. · FR-11, FR-26 · 3h
- [x] **T-050** SQLAlchemy persistence for workflow and run history. · FR-25, NFR-10 · 4h
- [x] **T-051** `main.py`: workflow CRUD. · FR-25 · 3h
- [x] **T-052** `tests/test_api.py`: catalog shape, run shape, 422 on a bad param, run history
      round-trip. · FR-12 · 4h

**Editor shell**

- [x] **T-053** React editor with EVA-01 tokens, three-pane layout, header with
      wordmark, Save, Run, LED. · 4h
- [x] **T-054** Palette: groups, group colour, search, click-to-add at viewport centre. ·
      FR-02 · 4h
- [x] Collapsible, resizable node library, inspector, and run-results panes; persist pane sizing.
- [x] Build React frontend assets and serve them through the FastAPI application.

**Canvas**

- [x] **T-055** Node card: title row, up to three label/value rows (required first), footer. ·
      4h
- [x] **T-056** Ports and edge drawing: 8px ports, SVG layer, cubic forward edges, right-angled
      routing for backward edges. · FR-03 · 6h
- [x] **T-057** Drag nodes, pan on empty canvas, `ctrl/⌘ + wheel` zoom, 85% default, Fit. ·
      FR-04 · 5h
- [x] **T-058** Connect by drag; reject self and duplicate; click an edge to delete. · FR-03 · 4h
- [x] **T-059** Multi-input nodes: two ports labelled A and B. · FR-05 · 3h

**Inspector**

- [x] **T-060** Form generator for all nine param types from the catalog. · FR-06 · 6h
- [x] **T-061** `show_if` by toggling `display`, never rebuilding. · FR-07 · 3h
- [x] **T-062** Keystroke safety: write to state, patch only the card summary. · FR-08 · 3h
- [x] **T-063** Rows editor (add/remove rows, per-column controls). · FR-06 · 4h
- [x] **T-064** Field-level validation before run, with the error under the control. · FR-16 · 3h

**Results**

- [x] **T-065** Results table: node, status chip, ms, `rows_in → rows_out`. · FR-13 · 4h
- [x] **T-066** Expandable per-node sample viewer. · FR-12 · 3h
- [x] **T-067** Node cards show their own counts and ms after a run. · FR-14 · 2h
- [x] **T-068** Failure treatment: danger border, error on the card, error in the row. ·
      FR-15 · 3h
- [x] **T-069** Run meta: run id, total ms, `llm_calls`, tokens. · FR-17 · 2h

**Honesty and keys**

- [x] **T-070** Probe `/nodes` on load; simulated mode when absent, signalled three ways. ·
      FR-29 · 4h
- [x] **T-071** Empty and idle states (no selection, no run). · FR-30 · 2h
- [x] **T-072** Keyboard: `⌘↵` run, `Delete` remove, `Esc` clear. · FR-09 · 2h

**Workspace setup**

- [x] SQLAlchemy persistence and model-profile API.
- [x] Provider connection tests, model settings screen, and apply profile to AI nodes.
- [x] Workflow home page with searchable saved workflows.

**M2 exit** — [x] browser demo: 5-node pipeline, run, `3 → 1` visible, sample opens, a cleared
required field marks the node red.

---

## M3 — Edges (week 5)

- [x] **T-073** `POST /upload` + the File Upload node wired to it. · FR-27 · 3h
- [x] **T-074** Generic HTTP Request node: method, URL, headers, body, per-row or once. · FR-24 · 5h
- [x] **T-075** Error policies end to end in the editor (per-row vs node failure). · FR-15 · 3h
- [x] **T-076** Cost meter surfaced: tokens and calls in the run meta and the results header. ·
      FR-17 · 2h
- [ ] **T-077** Dogfood workflow #1 — a real pipeline of your own; fix whatever it exposes. · 5h
- [ ] **T-078** Dogfood workflow #2 — a different shape (fan-out heavy). · 5h
- [ ] **T-079** Re-parameterise or add a node if the dogfood runs demand it; update `PRD.md` §7
      in the same change. · 4h

**M3 exit** — [ ] both workflows run start to finish; run meta shows calls and tokens.

---

## M4 — Proof (week 6)

- [ ] **T-080** Per-node test: run one step against the previous node's output (`POST /run` with
      a truncated graph and an input override). · 6h
- [ ] **T-081** Design-checklist pass against `EVA01-DESIGN.md` §11; write down any unsatisfied
      line. · 4h
- [ ] **T-082** Accessibility pass: focus visible everywhere, contrast, `prefers-reduced-motion`. ·
      NFR-07 · 3h
- [x] **T-083** README: what it is, how to run, single-operator security posture, BYOK setup. ·
      3h
- [ ] **T-084** Unassisted user test: watch one person build a 3-node pipeline and debug a bad
      row count. Fix the top three frictions. · 4h
- [ ] **T-085** Release check: `pytest -q`, `ruff check`, `PRD.md` §12 walked line by line. · 2h

**M4 exit** — [ ] a stranger completes the task unaided; every unmet checklist line is written
down rather than skipped.

---

## Backlog — explicitly not now

Recorded so nobody re-litigates them mid-phase. Each needs a decision, not a commit.

- Undo/redo, multi-select, copy/paste, minimap, auto-layout · the interaction model is not
  settled enough to protect with history.
- Source/sink integrations (Sheets, Slack, Notion, Supabase) · one HTTP node covers them.
- Persistent dedup / lookup / upsert · needs Redis.
- Sub-workflows, loops, error branches · engine complexity before product-market fit.
- Scheduling, webhooks, cron · `POST /workflows/{id}/run` is the trigger.
- Pyodide code isolation · required before multi-tenant, not before v0.1.
- Resumability / checkpointing · `ctx.node_outputs` is the door; the map is the work.
- Auth, tenancy, quotas · single-operator tool first.
- Listwise ranking prompts · pairwise scoring is cheaper and more debuggable.

---

## Done log

Append one line per completed task with the date and the commit, so the plan and reality stay
comparable.

```
YYYY-MM-DD  T-0xx  one line on what shipped
```
