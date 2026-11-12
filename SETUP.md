# Setup (agent-friendly)

One command on a fresh clone:

```bash
./scripts/setup.sh
```

Then run:

```bash
./scripts/run.sh
```

## Provider keys (ask before running)

n3rf never stores API keys. Before `./scripts/run.sh`, ask the user:

1. **Which provider do they use?** (OpenAI, Google Gemini, Anthropic, xAI, Groq, OpenRouter,
   Mistral, Hugging Face, Cloudflare, or a local model such as Ollama — no key needed.)
2. **Is a key already in the environment?** If not, ask them to either
   - export it in the same shell that starts FastAPI, e.g. `export OPENAI_API_KEY="..."`, or
   - copy `.env.example` to `.env`, paste their key there in an editor, and use
     `./scripts/run.sh` (it auto-loads `.env`; the file is gitignored).

   n3rf reads keys at run time; they are never written to disk, workflow JSON, or profiles.
   **Never accept a key pasted into a chat/session** — ask for approval before creating or
   saving any model profile, and prefer `POST /models/test` with the ephemeral paste-to-test
   key if the user wants to verify the connection.
3. **Do they want a keyless local model?** Point them at the provider presets in the AI
   nodes (`provider: ollama`) instead of a hosted API.

If the agent is driving setup, it should run `/models/test` with the user's ephemeral key
(pasted for that one request, never saved) to confirm the connection before handing over,
and ask for approval before creating or saving any model profile. The workspace home page
and `GET /models/status` both show whether any provider can actually be reached — use
that to confirm setup is real, not assumed.

Open http://127.0.0.1:8000.

## Requirements
- Python >= 3.12
- Node.js + pnpm (`npm i -g pnpm` or `corepack enable`)

## Verify
```bash
./scripts/verify.sh
```

## Troubleshooting
- Port in use: `PORT=8001 ./scripts/run.sh`
- Missing pnpm: install Node.js, then `npm i -g pnpm`
- Database path: set `N3RF_DB_PATH` before running
- Backend only: `uvicorn app.main:app --port 8000`
