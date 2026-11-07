# PLAN.md — n3rf

**Status:** active · **Version:** 0.1 · **Companions:** `PRD.md` (what), `ARCHITECTURE.md` (how),
`TASKS.md` (the list you actually work from)

Six weeks to a v0.1 that a stranger can use on their own key. The order below is chosen so that
every phase ends with something demonstrable, and so that the expensive, uncertain part — the
editor — starts only once the engine it projects already works.

---

## 1. Strategy

**Build the spine before the surface.** The engine, the contracts and the node set are
deterministic work with tests that pass or fail. The editor is the uncertain part. Doing the
engine first means that when the editor starts, `GET /nodes` and `POST /run` are already real,
so the UI is never developed against a mock that later changes shape.

**Prove the wedge with AI last.** The 11 data nodes ship before any model call, because they
are the ones that make the product ETL rather than a prompt wrapper. If the data nodes are not
right, the AI node is decoration.

**One demo per phase.** A phase is done when there is a pipeline you can show, not when the
modules compile. The demo is the acceptance test.

**Cut from the edges, never the middle.** If a phase runs long, drop features from the end of
`TASKS.md`, not the invariants in `AGENTS.md`.

---

## 2. Phases

| Phase | Week | Goal | Exit criterion (the demo) |
|---|---|---|---|
| **M0 Spine** | 1 | Contracts, params, registry, expressions, engine, 11 data nodes | A 6-node pipeline passes pytest offline, including a Filter that drops rows and a numeric Sort |
| **M1 Wedge** | 2 | `llm.py`, LLM Structured with repair, AI Filter/Ranker/Dedup, Code node + sandbox | `examples/demo.py` runs against a real model; an invalid model response is repaired, not crashed on |
| **M2 Surface** | 3–4 | FastAPI, SQLite, run history, the editor | Build a 5-node pipeline in the browser, run it, and find which node ate your rows in under 10 seconds |
| **M3 Edges** | 5 | File upload, generic HTTP node, error policies, cost meter, two dogfood workflows | Two of your own real pipelines run end to end without touching Python |
| **M4 Proof** | 6 | Per-node test, polish, docs, design-checklist pass | Someone who is not you builds and debugs a pipeline unassisted |

Budget M2 at **two weeks, not two days.** The editor is where the product is won or lost, and
it is the phase most likely to be underestimated.

---

## 3. Phase detail

### M0 — Spine (week 1)

Deliver `contracts.py`, `params.py`, `registry.py`, `expressions.py`, `engine.py` and
`nodes/data.py` + `nodes/input.py`. No AI, no HTTP, no UI.

Order within the phase matters: contracts → params → registry → expressions → engine → nodes.
Each layer's tests are written before the next layer exists, so a broken contract surfaces in
minutes, not in week 3.

**Exit:** the test suite runs in under 10s, offline, and covers topological order, a diamond
graph, a node that raises, `ctx.inputs` ordering, and every expression escape attempt.

### M1 — Wedge (week 2)

Deliver `llm.py`, `nodes/ai.py`, `nodes/code.py`, `sandbox.py`, `tests/mock_provider.py`, and
`examples/demo.py`.

The repair loop and the sandbox are the two items that must not be rushed here. The repair loop
is the difference between a toy and a reliable operator; the sandbox is the largest risk in the
product.

**Exit:** a deliberately malformed model response is repaired on the second attempt; a 50-row
node respects `concurrency` and `max_output_rows`; a Code node that tries to open a socket or
write a file fails cleanly with a readable message.

### M2 — Surface (weeks 3–4)

Deliver the modular FastAPI application, SQLAlchemy-backed SQLite store, React frontend build +
EVA-01 tokens, and the API tests.

Sequence: API surface → store → editor shell (three panes, palette) → canvas (nodes, ports,
edges) → generated inspector → results panel → keyboard and zoom.

The editor's own sequencing is deliberate: the results panel is built **before** the inspector
polish, because the results panel is half the product and the inspector is a form generator
that already works from the catalog.

**Exit:** the demo pipeline in the browser shows `rows_in → rows_out` per node, a click-through
to sample rows, and a failed node marked red with its error on the card.

### M3 — Edges (week 5)

Deliver `POST /upload`, the generic HTTP node, per-node error policies end to end, the cost
meter in the run meta, and two real workflows of your own.

The dogfood workflows are not optional. They are the only way to find out whether the node set
is actually complete; expect at least one node to be added or re-parameterised as a result.

**Exit:** both workflows run start to finish, and the run meta shows model calls and tokens.

### M4 — Proof (week 6)

Deliver per-node test (run one step against the previous node's output), the design-checklist
pass, README, and the empty/idle states.

Per-node test turns a 30-second debug loop into a 2-second one. It is the highest-leverage
feature not in v0.1's core, and `POST /run` with a truncated graph plus an input override
already supports it — the work is almost entirely in the editor.

**Exit:** a person who has not seen the tool builds a 3-node pipeline and debugs a bad row
count without help. Watch them do it; do not ask them.

---

## 4. Critical path

```
contracts → params → registry → engine ──┬─→ data nodes ─┐
                                         │               ├─→ API ─→ editor shell ─→ canvas ─→ inspector ─→ results
expressions ─────────────────────────────┘               │
llm.py ─→ ai nodes ─→ repair loop ───────────────────────┤
sandbox.py ─→ code node ─────────────────────────────────┘
```

Two things block the most work downstream: the **`Item` contract** and the **`Param` schema**.
Change either after M0 and every node plus the editor moves. That is why `AGENTS.md` §8 makes
both "ask a human first".

The editor's critical path is the canvas (nodes, ports, edges) — everything else in the UI can
be stubbed against it.

---

## 5. Risks

| risk | likelihood | impact | mitigation |
|---|---|---|---|
| Code-node sandbox is weaker than it looks | high | high (it is RCE by design) | ship self-hosted-only, state it in the README, put Pyodide behind the same contract before multi-tenant |
| LLM output drift breaks the pipeline silently | medium | high | schema validation + one repair attempt; `on_error` policy is explicit, never defaulted to "fail" |
| Fan-out cost surprises the user | medium | high | `max_output_rows` + `concurrency` on every fan-out node; tokens visible in run meta |
| The editor takes 3 weeks instead of 2 | high | medium | build the results panel before inspector polish; stub per-node test to M4 |
| Scope creep back toward integrations | high | medium | one generic HTTP node is the answer; anything else is a v0.2 conversation |
| Expression allowlist blocks a real use case | medium | low | curated function table is extensible; the Code node is the escape hatch |
| Provider incompatibility (non-OpenAI shape) | low | medium | BYOK covers the OpenAI-compatible majority; add an adapter only when a real user needs it |
| Long runs hit the HTTP timeout | low in v0.1 | high later | the envelope is written down in `ARCHITECTURE.md` §13; move to a worker at 60s, not before |

---

## 6. Cut lines

If a phase runs long, cut in this order — later items first.

1. Semantic Dedup (nice-to-have; exact Deduplicate covers most cases).
2. Compare Datasets (Merge covers the common path).
3. Example Dataset input node.
4. Per-node test (already M4 — cut to v0.2).
5. File Upload + `POST /upload`.
6. AI Ranker (AI Filter covers "cut it down").

**Never cut:** the results panel, `show_if`, the repair loop, `max_output_rows`, the sandbox,
the simulated-mode honesty. Each of those is the product or the safety of the product.

---

## 7. Cadence

- **Daily:** run `pytest -q` and `ruff check` before you stop. A suite that is red overnight
  costs a morning.
- **Per phase:** write the demo first as a script you want to exist, then make it work.
- **Weekly:** re-read `AGENTS.md` §1 and check the seven invariants against what you built. The
  drift happens in small commits, not big ones.
- **Before shipping v0.1:** walk `EVA01-DESIGN.md` §11 and `PRD.md` §12 line by line, and write
  down any line you could not satisfy instead of skipping it.

---

## 8. Definition of done

A phase is done when all four are true:

1. The exit demo runs from a clean checkout with no manual steps.
2. `pytest -q` is green and offline; `ruff check` is clean.
3. The relevant docs are updated in the same change (`TASKS.md` ticked, `ARCHITECTURE.md` if a
   decision moved, `PRD.md` if a requirement changed).
4. You would show it to someone without adding a caveat.
