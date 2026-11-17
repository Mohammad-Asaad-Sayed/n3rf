# Slack with n3rf — outbound nodes, plus an opt-in inbound trigger

The opt-in Slack pack: `Slack Send Message`, `Slack Add Reaction`, `Slack Fetch Thread`
(one bot token, env-held — never stored in workflows). In addition, n3rf can optionally mount
`POST /slack/events` (slack-bolt) for inbound mentions — see "Inbound trigger" below.
Scope note, same shape as the rest of n3rf: no connection/OAuth layer.

## Setup

Create a Slack app (bot scopes: `chat:write`, `reactions:write`, `channels:history`,
`groups:history` for private channels), invite the bot to the channel, then:

```bash
export SLACK_BOT_TOKEN="xoxb-…"
uvicorn app.main:app --port 8000
```

## Inbound trigger — `@you` runs a saved workflow (opt-in, slack-bolt)

The pack's nodes are outbound only by design. For the full ask → triage → answer loop, n3rf
optionally mounts `POST /slack/events`, driven by **slack-bolt**. Nothing happens until you
configure it:

```bash
# Required — from your Slack app config:
export SLACK_SIGNING_SECRET="…"          # Basic Information → Signing Secret
export SLACK_BOT_TOKEN="xoxb-…"          # bot token (chat:write, app_mentions:read, channels:history)
export N3RF_SLACK_TRIGGER_WORKFLOW_ID="…"  # id of the saved workflow that answers
# Recommended for local dev — skip Bolt's auth.test network call:
export SLACK_BOT_ID="B…"                 # Basic Information → App ID→ Bot User ID? Use the bot's B… id
export SLACK_BOT_USER_ID="U…"            # the bot's user ID, e.g. U0123…
# Optional — comma-separated channel IDs to answer in, everything else is ignored:
export N3RF_SLACK_TRIGGER_CHANNELS="C0123,C0456"
```

Slack-side setup: Event Subscriptions → Request URL `https://<your-host>/slack/events`,
subscribe to bot event `app_mention`, reinstall the app, invite the bot to the channel.
For local dev: `ngrok http 8000` and paste the HTTPS URL.

Behaviour: on an `@bot` mention, Bolt verifies the signature, acks inside Slack's 3-second
window, and **runs your saved workflow in the background** on one row:

```json
{ "question": "what's our line on pricing?", "channel": "C0123",
  "thread_ts": "1700000000.000100", "user": "U999", "event_ts": "1700000000.000100" }
```

The workflow is expected to post its own answer in the thread via **Slack Send Message**
(e.g. Fetch Thread → Ask AI → Send Message). Notes and caveats:

- **At-least-once**: Slack retries events it doesn't get timely 200s for — idempotent workflows or
  upserts on `thread_id` are the safe pattern.
- **Untrusted input**: the mention text is data from whoever typed it. Your answering workflow
  should treat `question` as untrusted data, not as instructions — sanitize or wrap it before any
  model call (see n3rf's expression-safety model; don't `{{question}}` directly into system prompts).
- **Push model preserved**: this is the only listener in n3rf. Everything else still runs via
  `POST /workflows/{id}/run`. If `/slack/events` is unconfigured, it answers `503` and nothing runs.

## Read a thread, answer it, react to it

```text
Manual JSON  →  Slack Fetch Thread  →  Ask AI (summarize + answer)  →  Slack Send Message  →  Slack Add Reaction
 [{"channel": "C0123", "ts": "1700000000.000100"}]   one row per message    [reply in the same thread]            [👀 on the ask]
```

`Slack Fetch Thread`: channel `C0123`, ts `1700000000.000100` — one row per message,
parent first, fields `text, user, ts, thread_ts, is_parent, reply_count`. Feed straight into
Ask AI / AI Filter for a thread summary before drafting the reply.

`Slack Send Message`: channel `#tech-problems` or a channel ID, text `@question — answer: …`,
thread_ts `1700000000.000100` to reply in-thread.

`Slack Add Reaction`: channel `C0123`, ts of the original ask, emoji `eyes` or
`white_check_mark` — the ack signal while the workflow runs.

## Things the pack deliberately does not do

- **Inbound DM handling** — the only listener is the `app_mention` trigger above. Other event
  types (DMs, reactions) are ignored.
- **DMs out / group messages** — bots can't open DMs via `chat:write` without the user's
  `im:write`; send to channels instead.
- **Pagination** — threads are read up to `limit` (max 1000) in one call.

## Failure modes worth knowing

- `Slack error: channel_not_found` — the bot isn't in the channel, or the channel ID/name is
  wrong (use the ID from the channel's permalink for safety).
- `Slack error: invalid_auth` / `account_inactive` — token revoked, or you grabbed a user token.
- `Slack error: missing_scope` — add the scope and reinstall the app.
- `Slack error: already_reacted` — harmless; the reaction is idempotent on retry.
- Rate limits — the Web API enforces per-method limits; keep per-row fan-out modest when
  sending messages, or gate with an `If / Else` on the row count.
