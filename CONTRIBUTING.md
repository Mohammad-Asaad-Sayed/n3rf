# Contributing to n3rf

Thanks for looking at the issues — this file is deliberately short. It points at the
authoritative docs instead of repeating them.

## Before you start

- Read [SETUP.md](./SETUP.md) for a working local setup (`./scripts/setup.sh` then
  `./scripts/run.sh`). The full offline check suite is `./scripts/verify.sh`.
- Read [AGENTS.md](./AGENTS.md) for the working agreement — the row contract, the `Param(...)`
  extension model, the no-`eval` rule, and the PR checklist. Those rules apply whether a human or
  an AI agent writes the code.
- By participating, you agree to abide by [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md).
- Keep changes focused: one node, one fix, one doc per pull request when possible.

## Ground rules that will block a PR

- `pytest -q` must stay green and fully offline; no test may hit a network.
- `ruff check app tests` and `ruff format --check app tests` must pass.
- A new node lands as one Python file plus its tests — no per-node frontend form.
- Never commit secrets, API keys, `.env`, `n3rf.sqlite3`, or `backups/`.
- `meta` never appears in `json`; no `eval` on user input.

## Scope notes

- The MVP ships **one generic HTTP node** instead of per-service integrations — deliberate.
  Discuss integration nodes in an issue before building one.
- The Code node's isolation and anything touching the data contract or execution model need an
  issue discussion first. See "Ask a human before" in [AGENTS.md](./AGENTS.md).

n3rf is licensed under [AGPL-3.0](./LICENSE). Contributions are accepted under the same license.
