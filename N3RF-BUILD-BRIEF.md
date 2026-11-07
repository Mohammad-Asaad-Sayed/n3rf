# n3rf — build brief for an AI coding agent

**What this file is.** A single, self-contained brief you can hand to Claude Code, Codex,
Cursor, or any agentic builder. It states what to build, in what order, and exactly how it
must look. Read it top to bottom before writing code.

**Companions to attach with this brief** (do not paraphrase them, treat them as source of truth):

| File | Role |
|---|---|
| `EVA01-DESIGN.md` | The visual system: colour, type, shape, states, component recipes, acceptance checklist |
| `eva01-tokens.css` | The same values as CSS custom properties — link or inline it, never retype a hex |
| `eva01-tokens.json` | The same values for build pipelines / JS |
| `ARCHITECTURE.md` | The product and engine decisions this brief implements |
| `n3rf-editor.html` | A themed prototype of the editor, for judging the interaction model. **Not** shippable code — rebuild the real thing, but match its feel |

If a value is missing from the theme, derive it from the nearest token and leave a comment.
Never invent a hue. Never introduce new terminology for the product's own entities.

---

## 1. What you are building

An AI-first workflow builder: **messy input in, structured rows out**, running on the user's
own model and their own API key.

It is ETL with an LLM as one of the operators — not an automation tool with an AI step. Two
consequences run through every decision below:

1. **Rows are the unit, not events.** Every node takes `list[Item]` and returns `list[Item]`.
2. **Fan-out is the performance story.** 500 rows × one LLM call each is the normal case, so
   concurrency, retries, cost accounting and row caps are core features, not polish.

The wedge is narrow on purpose: ~23 nodes that make an AI data pipeline complete, not 400
integrations. Do not add integrations. A single generic HTTP Request node covers them.

---

## 2. Non-negotiables (get these wrong and the product is wrong)

**2.1 Data contract.**

```
Every node receives list[Item] and returns list[Item].
Item = {"json": dict, "meta": dict}
```

`json` is the user's row. `meta` holds lineage (`paired` — which input row produced this
output row), the producing node, and error markers. They stay apart so any output row traces
back to its input without users seeing engine bookkeeping. Never leak a `meta` key into
`json`.

Nodes with more than one inbound connection additionally receive `ctx.inputs[0..n]`. That is
what makes Merge and Compare Datasets possible while every other node keeps one shape.

Do **not** define a Pydantic model per node. Rows are user-shaped and change per workflow.
Use plain dicts with explicit coercion at the edges.

**2.2 Batch execution per node, not per row.** The engine walks nodes in topological order and
hands each node the whole batch. Per-row execution makes Sort and Aggregate impossible and
destroys throughput. Row-level parallelism lives *inside* a node as a semaphore around
`asyncio.gather` (the LLM node defaults to `concurrency=8`).

The engine is async; **nodes may be sync**. Await only if the node's return value is
awaitable. Nobody should write `async def` to add a field.

**2.3 Params are declared, so the UI is generated.**

```python
Param("output_mode", "string", "Output mode", default="per_input",
      options=["per_input", "expand_arrays"],
      show_if={"param": "mode", "in": ["expand_arrays"]})
```

One declaration produces (a) the form the editor renders, (b) run-time coercion and
required-field validation, (c) the docs. `GET /nodes` returns the whole catalog as JSON.

If the frontend hardcodes one form per node, adding node #24 costs a frontend PR and the
product slows down every week. This is the highest-leverage rule in the codebase.

**2.4 The registry is the plugin boundary.** `@node(...)` writes into a module-level
`REGISTRY`; `registry.load_all()` imports the node modules. Keep it that dumb. `entry_points`
plugins are a v2 concern.

**2.5 BYOK, provider-agnostic.** `base_url` + `api_key` + `model`. Anything speaking OpenAI's
`/chat/completions` works: OpenAI, Groq, OpenRouter, Together, Ollama, vLLM, LM Studio. Keys
come from `api_key_env` by default so they never land in workflow JSON. No per-provider
adapter layer in this milestone.

---

## 3. Stack and layout

| Layer | Choice |
|---|---|
| HTTP | FastAPI + uvicorn |
| Engine | plain asyncio, in-process |
| LLM | `httpx.AsyncClient` |
| Validation | `jsonschema` (LLM output and node params) |
| Storage | SQLite now, Postgres later — keep the store to ~6 functions |
| Tests | pytest with a mock provider; whole suite offline in seconds |
| Editor | React + accessible shadcn-style primitives, EVA-01 CSS tokens, Vite production build served by FastAPI |

Deliberately absent: Celery, Redis, Kafka, an ORM, a message bus, Docker-in-Docker, a Node
runtime in the product. Add a worker queue when a single run routinely exceeds the HTTP
timeout — not before.

```
/app
  main.py            FastAPI app factory and static frontend integration
  api/               routers for nodes, workflows, runs, and uploads
  schemas/           request schemas
  services/          graph validation and workflow execution
  engine.py          topological run, ctx, per-node metrics
  contracts.py       Item, ItemList, coercion
  params.py          Param, show_if resolution, validation
  registry.py        @node decorator, REGISTRY, load_all()
  expressions.py     {{ $json.x }} — ast, allowlist, no eval
  store.py           workflows, runs (6 functions)
  nodes/
    __init__.py
    input.py         the 7 custom-input nodes
    data.py          the 11 in-memory data nodes
    ai.py            LLM Structured, AI Filter, AI Ranker, Semantic Dedup
    code.py          sandboxed Code node
/frontend
  src/
    components/ui/   accessible shadcn-style primitives
    styles/          EVA-01 editor styling
    App.tsx          React workflow editor
/app/static
  eva01-tokens.css
```

---

## 4. API surface

```
GET  /nodes                 catalog + param schemas -> drives the generated form UI
POST /run                   run an unsaved graph (editor "test")
POST /workflows/{id}/run    run a saved workflow
GET  /runs/{id}             per-node results, timings, row counts, logs
GET/POST/PUT /workflows     CRUD
POST /upload                file -> base64 for the File Upload node
```

The run response **is** the product. Per node: `status`, `ms`, `rows_in`, `rows_out`, `error`,
and a 5-row sample.

```json
{"run_id": "run_8f21", "status": "success", "ms": 108,
 "nodes": [{"id": "extract", "status": "success", "ms": 23,
            "rows_in": 3, "rows_out": 3, "error": null, "sample": [{"company": "Acme"}]}],
 "output": [ ... ],
 "metrics": {"llm_calls": 3, "tokens_in": 812, "tokens_out": 240}}
```

`GET /nodes` item shape — the editor renders from exactly this:

```json
{"id": "llm_structured", "name": "LLM Structured", "group": "ai",
 "description": "One model call per row, validated against your schema.",
 "inputs": 1,
 "params": [
   {"key": "model", "label": "Model", "type": "string", "default": "gpt-4o-mini", "required": true},
   {"key": "mode", "label": "Output mode", "type": "select",
    "options": ["per_input", "expand_arrays"], "default": "per_input"},
   {"key": "max_output_rows", "label": "Max output rows", "type": "number",
    "default": 500, "unit": "rows",
    "show_if": {"param": "mode", "in": ["expand_arrays"]}},
   {"key": "schema", "label": "Output schema", "type": "json", "default": "{}"},
   {"key": "on_error", "label": "On row error", "type": "select",
    "options": ["error_item", "skip", "fail"], "default": "error_item"}
 ]}
```

Supported param `type` values, and the control each one renders:

| type | Control |
|---|---|
| `string` | text input, height 34 |
| `textarea` | 3-row textarea |
| `number` | numeric input, optional `unit` label |
| `boolean` | 28×14 toggle |
| `select` | native select, styled |
| `json` | mono textarea, validated on blur, `invalid json` on error |
| `code` | mono textarea, tab-friendly |
| `rows` | repeatable row editor from `columns: [{key,label,type,options}]` |
| `file` | dashed drop zone, 52px |

---

## 5. The node set: 23 nodes, and nothing else

**Input (7)** — Manual JSON · Text Lines · CSV File · File Upload · Spreadsheet Paste ·
Field Builder · Example Dataset

**Transform (11)** — Filter · Sort · Limit · Set Fields · Remove Fields · Rename Fields ·
Aggregate · Expand Arrays · Merge · Compare Datasets · Deduplicate

**AI (4)** — LLM Structured · AI Filter · AI Ranker · Semantic Dedup

**Code (1)** — Code

Plus one optional extra worth shipping early: a **generic HTTP Request node**, ~80 lines. It
turns "you don't have the integration I need" from a blocker into an inconvenience.

Deliberately out: source/sink integrations (Sheets, Slack, Supabase, Notion — a week of OAuth
and pagination each, zero differentiation), persistent dedup/lookup (needs Redis), listwise
ranking prompts, sub-workflows, loops, error branches, scheduling, webhooks, cron.
`POST /workflows/{id}/run` is the trigger.

---

## 6. The four hard problems

**6.1 The Code node is remote code execution by design.** Child process (`python -I -S`), an
import allowlist, `sys.addaudithook` blocking subprocess/socket/ctypes/file writes,
`RLIMIT_AS`/`RLIMIT_CPU`/`RLIMIT_NPROC`, and a parent-side wall-clock kill. That is adequate
for self-hosted single-tenant use and **not** adequate for multi-tenant SaaS. Before you let
anyone but the operator sign up, put Pyodide behind the same node contract (`list in, list
out, return a list`) so the swap is invisible to users.

**6.2 Expressions must never be `eval`.** `{{ $json.name }}` is user input. Parse with `ast`,
walk an allowlist of node types, forbid imports and dunder attributes, and permit calls only
from a curated table (`len`, `trim`, `lower`, `json_dumps`, `re_match`, `coalesce`, …).
Subscript and attribute access go through a `_Safe` wrapper so `item.__class__` raises. Users
who want arbitrary Python use the Code node, which has its own sandbox.

**6.3 Fan-out cost and rate limits.** A 500-row LLM node is 500 requests. Without controls you
get a 429 storm, a surprise bill, and a run that never ends. Every fan-out node needs
`concurrency`, `max_output_rows`, per-item retries with jittered backoff, and a per-row error
policy (`error_item` / `skip` / `fail`). Accumulate token counts into `ctx.metrics` from day
one — retrofitting cost attribution is painful.

**6.4 Partial execution is not solved here.** A run that fails at node 9 re-runs nodes 1–8.
That is a defensible cut, but keep the door open: materialise every node's output in
`ctx.node_outputs` so a run stays a sequence of pure `(params, items) -> items` transitions.
Resume-from-checkpoint later means persisting that map, not rewriting the engine.

---

## 7. The interface, in EVA-01

### 7.1 Surface map — exactly one of each

| Role | Token |
|---|---|
| App frame / canvas backdrop | `--surface-void` |
| Page and panel chrome | `--surface-base` |
| Node bodies, results containers | `--surface-panel` |
| Inputs, chips, hover rows, secondary buttons | `--surface-raised` |
| Selected row, active nav item, dragged state | `--surface-overlay` |

Elevation is one rung up the ladder plus a 1px border. Shadows only for floating layers.
No sixth background may exist anywhere in the CSS.

### 7.2 Where the accent goes

Neon green `--accent` means **live / selected / primary**, and appears at most three times on
a screen: the Run button, the selected node, the connection LED. Everything else is neutral.
If green is on the primary button it is not on links, headings, badges or body text.
Text on green is `--on-accent`, never white.

### 7.3 Node group colours

The theme has no cyan or pink, so group colour is drawn from the existing palette. Do not
invent hues:

| Group | Token | Applied as |
|---|---|---|
| Input | `--info` | 3px leading bar + 6px dot on the card |
| Transform | `--purple-light` | same |
| AI | `--alert` | same |
| Code | `--warn` | same |

Group colour is the only chrome. No icons to learn. Green never encodes a group.

### 7.4 Type map

| Element | Rung |
|---|---|
| Node titles, panel numerals | `--type-title-s` (Chakra Petch 600, UPPER, +0.02em) |
| Field labels, node key column, telemetry | `--type-micro` (Share Tech Mono 9, UPPER, +0.06em) |
| Buttons, tabs, chips, table headers | `--type-label` (Rajdhani 600, UPPER, +0.045em) |
| Table cells, dense copy, node values | `--type-body-s` |
| Body copy | `--type-body` |
| JSON, code, IDs | `--type-mono` (Share Tech Mono 12/16) |

No ad-hoc font sizes. Uppercase only for labels and titles of ~24 characters or fewer, always
with tracking; never uppercase a sentence, description, tooltip or error message.

### 7.5 Geometry

Radii 1–3px only. Every border exactly 1px (2px only for accent rules and corner brackets).
Control heights from the scale: 24 / 28 / 32 / 36 / 40, one height per context. Canvas grid
dots `#5A4691` at 16px pitch. The editor opens at **85% zoom, never lower**.

### 7.6 Shell: adjustable workbench panes, no modals

```
┌ header 48 ─────────────────────────────────────────────────────────┐
│ brand │ workflow name            │ LED chip │ Save │ Run (⌘↵)      │
├ optional amber strip 26 (only when simulated) ─────────────────────┤
│ palette 236 │ canvas                          │ inspector 372     │
│             ├─────────────────────────────────┤                   │
│             │ results 212                     │                   │
└─────────────┴─────────────────────────────────┴───────────────────┘
```

- Palette 236px fixed. Search at the top, groups in the order Input → Transform → AI → Code,
  each with a colour dot and `--type-micro` heading. Clicking an item adds it at the centre of
  the viewport and selects it.
- Canvas flexible; results panel 212px under it. Results belong to the **run**, not the
  selected node — the useful comparison is node 3 → 4 → 5.
- Inspector 372px fixed in pixels, not percent. A JSON textarea at 500px is worse, not better.
- One piece of furniture per screen: corner brackets on the outer frame. If in doubt, omit.

### 7.7 Canvas behaviour

- Drag from an output port (8px square, right edge) to an input port (left edge). Ports are
  `--line-strong` when free, `--accent` when connected.
- Multi-input nodes (Merge, Compare Datasets) get two ports labelled `A` and `B`. That label
  is the only thing telling a user which branch is which.
- Clicking an edge deletes it. Hovering shows it dashed in `--accent`.
- Forward edges curve (cubic). Edges that go backwards route on a right angle through the gap
  between rows, so a wire never runs behind a node body.
- Selected node: `--accent` border + `--glow-accent` + 2px corner brackets. One glow per
  screen — never glow a card that is not selected.
- Dragging empty canvas pans; `ctrl/⌘ + wheel` zooms about the pointer; `⌘↵` runs; `Delete`
  removes the selection; `Esc` clears it.
- While a run is in flight, wires animate dashes in `--accent` (800–1200ms linear, dashes
  only). Respect `prefers-reduced-motion`: keep opacity changes, drop transforms and loops.

### 7.8 Node card

Width 240 (200–280 allowed). `--surface-panel`, 1px `--line-strong`, radius 3.
Title row 32px, `--type-title-s`, with a 2px rule beneath in the group colour (accent when
selected). Body: **at most three** label/value rows — required params first — because a card
must stay short enough that two never collide. Footer: `rows_in → rows_out` and `ms` after a
run. On failure: `--danger` border, the error printed on the card, and the same error in the
results table. There is no separate error view; errors belong where the node is.

### 7.9 Results panel

A table, hairline dividers, no zebra striping:

| Column | Treatment |
|---|---|
| Node | `--type-micro` in `--text-secondary` |
| Status | chip: `chip--accent` ok, `chip--danger` error, `chip--warn` running |
| ms | right-aligned, Chakra Petch, `--text-primary` |
| Rows | `rows_in → rows_out`, the drop coloured `--warn` |
| Note | model/concurrency for AI nodes, empty otherwise |

Click a row to open a 5-row sample beneath it: `--surface-void`, mono 12/16, keys `--info`,
strings `--accent`, numbers `--warn`, booleans `--purple-light`. Header of the run carries
`run_id`, total ms, node count and `llm_calls`.

`500 → 12` at the Filter node is the number that earns its place: it locates the problem
without opening anything. Most builders dump raw JSON here and users insert a log node to find
out what happened.

### 7.10 State honesty — three signals, never a quiet fake

| State | Treatment |
|---|---|
| No selection | a one-line hint in the inspector, not an empty box |
| No run yet | "Run the workflow to see per-node results." |
| Node failed | `--danger` border, error on the card, error in results |
| Backend unreachable | simulate the run, and say so **three ways**: amber banner, amber connection LED, `· simulated` in the run meta |

A prototype that quietly fakes results is worse than one that shows nothing.

### 7.11 The generated form

Build controls from `GET /nodes` alone. Two rules that matter more than they look:

1. **Never re-render the form on keystroke** — it steals focus and moves the caret. Write to
   state; re-render only the node card summary.
2. **Resolve `show_if` by toggling `display`**, not by rebuilding the subtree.

Field label sits above the control: mono 9, uppercase, +0.06em, `--text-meta`, margin-bottom
4, unit and required marker on the right of the label in the same style. Inputs:
`--surface-void`, 1px `--line-hairline`, radius 2, height 34, text `--text-primary` at
`--type-body-s`. Focus: border `--accent` + `--focus-ring`. Error: `--danger` border, message
in `--danger` at `--type-micro`.

---

## 8. Build order

Each milestone ends with a demo you can show, not a folder of half-built modules.

**M0 — spine.** `contracts.py`, `params.py`, `registry.py`, `expressions.py`, `engine.py`, the
11 data nodes. No AI, no UI.
*Done when:* a 6-node pipeline passes pytest offline, including a Filter that drops rows and a
Sort that respects numeric vs string ordering.

**M1 — wedge.** `llm.py`, LLM Structured with schema validation **and a repair loop**,
AI Filter, AI Ranker, Semantic Dedup, the mock provider, and the Code node with its sandbox.
*Done when:* `examples/demo.py` runs against a real model, a deliberately invalid model
response is repaired rather than crashing, and a 50-row node respects `concurrency` and
`max_output_rows`.

**M2 — surface.** FastAPI, SQLite, run history, and the editor: palette, connection drawing,
generated forms, results panel. Budget two weeks here, not two days.
*Done when:* you can build a 5-node pipeline in the browser, run it, and find which node ate
your rows in under ten seconds.

**M3 — edges.** File upload, generic HTTP node, error policies, cost meter, and two real
workflows of your own to dogfood.

**M4 — the first thing to add back:** per-node test — run one step against the previous node's
output. It turns a 30-second debug loop into a 2-second one, and `POST /run` with a truncated
graph plus an input override already supports it.

---

## 9. Acceptance checklist

Walk every line before calling a screen or a milestone done, and report any line you could not
satisfy rather than silently skipping it.

**Design**

- [ ] Every background is one of the five surface tokens; no sixth value exists in the CSS.
- [ ] Neon green appears at most three times per screen, and never as body text.
- [ ] No white text on green; `--on-accent` on every accent fill.
- [ ] All radii are 1–3px (999px only for avatars and circular icon buttons).
- [ ] All borders exactly 1px (2px only for accent rules and corner brackets).
- [ ] Every text style maps to a rung of the type scale; no ad-hoc font sizes.
- [ ] Uppercase only on labels and titles, always with tracking.
- [ ] Every interactive element has visible hover, focus, active and disabled states.
- [ ] At most one glow and one piece of furniture (stripes / brackets / scanlines) per screen.
- [ ] Contrast: body ≥ 4.5:1, meta ≥ 4.5:1, large display ≥ 3:1 against its own background.
- [ ] No product wording changed, added, or re-flavoured. No lore-flavoured copy.
- [ ] No gradients on surfaces or buttons; no drop shadows on flat cards; no pill chips.

**Product**

- [ ] Every node obeys `list[Item] -> list[Item]`; `meta` never appears in `json`.
- [ ] Multi-input nodes receive `ctx.inputs[0..n]` and Merge/Compare work on both ports.
- [ ] Adding node #24 requires one Python file and no frontend change.
- [ ] The inspector form is generated entirely from `GET /nodes`.
- [ ] `show_if` hides and reveals without rebuilding the form; typing never loses focus.
- [ ] Every run response carries `rows_in`, `rows_out`, `ms` and a 5-row sample per node.
- [ ] A failing node marks its card and its results row, and the run still reports the rest.
- [ ] Simulated mode is announced three ways; nothing is silently faked.
- [ ] LLM nodes bound concurrency and `max_output_rows`; retries are jittered.
- [ ] `ctx.metrics` accumulates token counts on every LLM call.
- [ ] Code node runs in a child process with rlimits and an audit hook; no `eval` anywhere on
      user input.

---

## 10. Priming prompt

Paste this above the brief when you start a session:

> You are building **n3rf**, an AI-first workflow builder, in the EVA-01 theme. Read
> `EVA01-DESIGN.md`, `eva01-tokens.css`, `ARCHITECTURE.md` and this brief first; treat them as
> the single source of truth for colour, type, spacing, radius, states, effects, data contract
> and scope. Use the CSS custom properties — never hard-code a hex value or a font size.
> Compose components only from the primitives in the design system's section 6, and give every
> interactive element the four states from section 7. The theme is visual only: keep the
> product's existing terminology and copy exactly as given. Follow the build order in section
> 8, and before finishing walk the section 9 checklist and report any line you could not
> satisfy. Do not add nodes, integrations or screens that section 5 excludes.
