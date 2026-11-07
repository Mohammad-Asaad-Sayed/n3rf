# PRD.md — n3rf

**Status:** draft for build · **Version:** 0.1 · **Owner:** product · **Companion docs:**
`ARCHITECTURE.md`, `PLAN.md`, `TASKS.md`, `AGENTS.md`, `EVA01-DESIGN.md`

---

## 1. Summary

n3rf is a workflow builder for AI data pipelines: messy input in, structured rows out, running
on the user's own model and their own API key. You wire a graph of nodes, press run, and watch
row counts move from node to node until the data is the shape you wanted.

The product is ETL where one of the operators happens to be an LLM call. It is not an
automation tool with an AI step.

---

## 2. Problem

The work this replaces is done today in one of three bad ways.

**Spreadsheets plus copy-paste into a chat window.** An analyst has 500 messy rows — company
names, addresses, half-filled category fields — and needs them classified and normalised. They
paste chunks into ChatGPT, get prose back, paste it into a sheet, and lose track of which row
became which. At 500 rows this takes an afternoon and is wrong in ways nobody can see.

**Zapier and n8n.** Both are built for events and integrations: a trigger fires, a record
moves. They are poor at the thing this user needs — treating a *batch of rows* as the unit,
sorting and aggregating it, running one model call per row with a concurrency cap, and showing
where rows disappeared. Users end up inserting a log node to find out what happened.

**A script.** A Python script does the job and then becomes the problem: it is not inspectable
by the person who needs to change the prompt, it has no per-step visibility, and it has no
cost control.

The gap: nobody gives a non-engineer a canvas where a batch of rows flows through AI
operators, with per-step row counts, for their own key and their own model.

---

## 3. Users

**3.1 The operations analyst (primary).** Runs a data-heavy function in a mid-size company —
RevOps, supply chain, recruiting, compliance. Comfortable in spreadsheets and formulas, not in
IDEs. Has an API key because they already use a model in another tool. Their success looks
like: 500 messy rows became a clean table before lunch, and they can explain to their manager
which step dropped what.

**3.2 The growth / RevOps engineer (secondary).** Writes SQL and light Python. Will use the
Code node when the built-in nodes run out. Cares about determinism, retries and cost.

**3.3 The internal-tools developer (secondary).** Building a pipeline for someone else and
wants to hand over something the other person can edit without reading code.

**Explicitly not the user:** someone who wants a chatbot, a CRM integration, or a
no-code website builder.

---

## 4. Jobs to be done

- "I have a spreadsheet that a model could clean up. I want to do that without writing a
  script."
- "I need to know *which step* ate my rows."
- "I want to use my own model and my own key, not yours, and not be charged a markup I can't
  see."
- "I want to change the prompt and re-run without a developer."
- "I want to see the actual output rows at each step before I trust the pipeline."

---

## 5. Positioning

| | n3rf | Zapier / n8n | A script | Chat + spreadsheet |
|---|---|---|---|---|
| Unit of work | rows | events | rows | one blob |
| AI per row with concurrency cap | yes | weak | manual | no |
| Per-step row counts | yes, the core UI | no | print statements | no |
| BYOK, any OpenAI-compatible endpoint | yes | no | yes | no |
| Editable by a non-engineer | yes | yes | no | yes |
| Cost visible per run | yes | no | no | no |

The winnable wedge is **AI-native data pipelines**, not integration count. Copying 400
integrations is a losing race; ~23 nodes that make the AI pipeline complete is not.

---

## 6. Scope for v0.1

**In**

- A canvas editor: palette, nodes, connections, inspector, results panel.
- 23 nodes: 7 input, 11 transform, 4 AI, 1 code.
- One model-call-per-row node with schema validation and a repair loop.
- Per-node results with `rows_in → rows_out`, duration, status and a 5-row sample.
- Save and re-load a workflow; run history.
- BYOK: `base_url`, `api_key_env`, `model`.
- A generic HTTP Request node (M3) instead of integrations.

**Out**

| Cut | Why |
|---|---|
| Source/sink integrations (Sheets, Slack, Notion, Supabase) | 30+ nodes of OAuth and pagination boilerplate, zero differentiation |
| Persistent dedup / lookup / upsert | Needs Redis or a real store — infrastructure before product-market fit |
| Sub-workflows, loops, error branches | Multiply engine complexity; a DAG proves the wedge |
| Scheduling, webhooks, cron triggers | Out of scope until someone asks; `POST /workflows/{id}/run` is the trigger |
| Multi-tenant accounts, teams, permissions | Single-operator tool first |
| Undo/redo, multi-select, copy/paste, minimap, auto-layout, collaboration, mobile | Real, but none of them test whether the interaction model works |
| A hosted model reseller | BYOK is the position; a markup would undercut it |

---

## 7. Functional requirements

Each requirement is testable. `TASKS.md` maps tasks to these IDs.

### Graph and editor

- **FR-01 Catalog** — `GET /nodes` returns every node with `id`, `name`, `group`,
  `description`, `inputs` and a param schema. The editor renders from this response alone.
- **FR-02 Palette** — nodes grouped Input → Transform → AI → Code with group colour; searchable;
  clicking an item adds it at the viewport centre and selects it.
- **FR-03 Connect** — drag from an output port to an input port to create an edge; clicking an
  edge deletes it; a node cannot connect to itself; duplicate edges are rejected.
- **FR-04 Move** — nodes drag freely; the canvas pans on empty-canvas drag; zoom via
  `ctrl/⌘ + wheel` and buttons; the editor opens at 85% zoom, never lower.
- **FR-05 Multi-input** — Merge and Compare Datasets show two input ports labelled `A` and `B`;
  the run receives `ctx.inputs` in that order.
- **FR-06 Generated form** — the inspector renders every param type (string, textarea, number,
  boolean, select, json, code, rows, file) from the catalog, with label, unit, required marker
  and hint. No form is hand-written per node.
- **FR-07 Conditional params** — `show_if` hides and reveals a field by toggling `display`; the
  form is never rebuilt for it.
- **FR-08 Editing never loses focus** — typing in a field does not re-render the form or move
  the caret.
- **FR-09 Keyboard** — `⌘/ctrl + Enter` runs; `Delete`/`Backspace` removes the selected node or
  edge; `Esc` clears selection.

### Execution and results

- **FR-10 Run an unsaved graph** — `POST /run` accepts nodes and edges and executes them in
  topological order.
- **FR-10a Run one node** — the editor can execute one node and its upstream dependencies,
  stopping before downstream nodes; partial runs are not added to full workflow run history.
- **FR-11 Run a saved workflow** — `POST /workflows/{id}/run`.
- **FR-12 Per-node result** — status, `ms`, `rows_in`, `rows_out`, `error`, and a sample of up
  to 5 output rows, for every node in the run.
- **FR-13 Results panel** — a table of every node with `rows_in → rows_out` and duration; a
  drop in row count is visually marked; clicking a row opens the sample beneath it.
- **FR-14 Node cards report the run** — after a run, each card shows its own
  `rows_in → rows_out` and `ms`.
- **FR-15 Failure is visible where it happened** — a failed node gets a danger border, the
  error on the card, and the same error in its results row. There is no separate error view.
- **FR-16 Validation before execution** — required and typed params are validated before a node
  runs; the message names the field.
- **FR-17 Run metrics** — the run response carries `llm_calls` and token counts; the editor
  shows them in the run meta.

### Nodes

- **FR-18 Input nodes (7)** — Manual JSON, Text Lines, CSV File, File Upload, Spreadsheet Paste,
  Field Builder, Example Dataset. Each produces `list[Item]`.
- **FR-19 Transform nodes (11)** — Filter, Sort, Limit, Set Fields, Remove Fields, Rename
  Fields, Aggregate, Expand Arrays, Merge, Compare Datasets, Deduplicate.
- **FR-20 LLM Structured** — one model call per row; output validated against a JSON Schema;
  on validation failure, re-prompt once with the error and validate again; honour
  `concurrency`, `max_output_rows`, `on_error`, and both output modes (`per_input`,
  `expand_arrays`).
- **FR-21 AI Filter / AI Ranker / Semantic Dedup** — keep-by-criterion, score-and-truncate, and
  near-duplicate collapse, each with the same fan-out controls as FR-20.
- **FR-22 Code node** — user Python over the batch, `list` in and `list` out, in an isolated
  child process with a wall-clock kill. Same contract when the isolation is upgraded.
- **FR-23 Expressions** — `{{ $json.field }}` in string params, evaluated by an `ast` allowlist
  walker: no imports, no dunder attributes, no arbitrary calls.
- **FR-24 Generic HTTP Request node** — method, URL, headers, body, one row or per row.

### Persistence and platform

- **FR-25 Workflow CRUD** — `GET/POST/PUT /workflows`; a workflow stores nodes, edges and
  positions.
- **FR-26 Run history** — `GET /runs/{id}` returns the stored per-node results after the fact.
- **FR-27 File upload** — `POST /upload` returns base64 for the File Upload node.
- **FR-28 BYOK** — `base_url` + `api_key_env` + `model` on every AI node; the key is read from
  the environment and never written into workflow JSON.

### Degradation

- **FR-29 Simulated mode** — if the API is unreachable, the editor simulates a run so the UI
  stays explorable, and announces it three ways: amber banner, amber connection LED, and
  `· simulated` in the run meta. Nothing may present simulated output as real.
- **FR-30 Empty and idle states** — no selection shows a one-line hint, not an empty box; no
  run shows "Run the workflow to see per-node results."

---

## 8. Non-functional requirements

- **NFR-01 Fan-out safety** — a 500-row LLM node runs without unbounded memory or socket use;
  `max_output_rows` and `concurrency` are enforced, not advisory.
- **NFR-02 Editor delivery** — React production assets are built once and served by FastAPI from
  the same origin as the API; no separate production frontend server is required.
- **NFR-03 Catalog latency** — `GET /nodes` p95 under 50ms locally.
- **NFR-04 Test speed** — the whole suite runs offline in under 10s.
- **NFR-05 Secrets** — no API key in workflow JSON, logs, run records or error messages.
- **NFR-06 Code isolation** — the Code node cannot write files, open sockets, spawn processes
  or read environment variables outside its allowlist.
- **NFR-07 Accessibility** — visible focus on every interactive element; contrast per
  `EVA01-DESIGN.md` §2.3; `prefers-reduced-motion` respected.
- **NFR-08 Design purity** — no hex value, font size or radius outside the EVA-01 tokens; green
  appears at most three times per screen.
- **NFR-09 Durability** — a completed run is readable after a process restart.
- **NFR-10 Portability** — SQLAlchemy-backed persistence uses `N3RF_DATABASE_URL` to select a
  supported SQL database when its driver is installed.
- **NFR-11 Failure clarity** — every user-facing error names the node and the field, and says
  what to change.
- **NFR-12 No hidden cost** — the run meta always shows model calls and tokens consumed.

---

## 9. UX principles

1. **The results panel is half the product.** Workflow tools are debugging tools with a canvas
   attached. `500 → 12` at the Filter node is the number that earns its place.
2. **Generated, never hand-written.** Forms come from the catalog; the UI is a projection of
   the backend's param declarations.
3. **Three panes, no modals.** Palette, canvas, inspector, results under the canvas. You edit a
   node while still seeing the shape of the pipeline.
4. **State honesty.** Nothing is faked, nothing is blank without explanation, errors live where
   they happen.
5. **Density over comfort.** This is equipment being operated, not a website being browsed.
   Every visual rule is in `EVA01-DESIGN.md`; it is not a suggestion.

---

## 10. Success metrics

**Activation.** A new user builds a 3-node pipeline and runs it in under 10 minutes without
reading docs.

**The debugging loop.** Median time from "my rows are wrong" to "it is node 4" under 30
seconds, measured by whether the user opens the results panel rather than editing a node.

**Trust.** Zero reports of a run whose displayed output differed from the returned rows.

**Cost sanity.** No run exceeds the user's declared `max_output_rows` × model price without the
cap being visible in the UI first.

**Leading indicator to watch:** the fraction of runs where the user clicks into a node sample.
If nobody opens the samples, the results panel is decorative.

---

## 11. Assumptions and open questions

**Assumptions**

- The user has, or can get, an API key. BYOK is a filter, not a barrier, for this audience.
- Single-operator use is enough to prove the wedge; teams come later.
- Runs under ~60s cover most jobs, so in-process asyncio is sufficient.

**Open**

- Does the first-run experience need a seeded example workflow, or is an empty canvas honest
  enough? (Current answer: ship the 5-node demo, keep the empty state.)
- Is per-node test (run one step against the previous output) a v0.1 need or the first v0.2
  feature? Current plan: first thing added after v0.1.
- When does the Code node move to Pyodide? Current answer: before anyone but the operator signs
  up.
- Do we need a file-sink node (CSV/Sheets export) to close the loop, or is copy-from-sample
  enough? Not answered.

---

## 12. Release criteria for v0.1

- Every FR above is either implemented or explicitly deferred in writing here.
- A stranger can build, run and debug a 5-node pipeline on their own key without help.
- `pytest -q` green and offline; `ruff check` clean.
- The design acceptance checklist in `EVA01-DESIGN.md` §11 passes line by line, with any
  unsatisfied line reported rather than skipped.
- No known path where simulated output can be mistaken for a real run.
