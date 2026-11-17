"""Slack trigger — opt-in inbound listener for the n3rf push model.

Slack apps must reach n3rf over HTTP, so this only exists when the operator
configures it. Nothing runs until a signed request hits ``POST /slack/events``.

Behaviour: on ``app_mention`` (the bot @-mentioned in a channel), the configured
saved workflow runs on a single row::

    {"question": "what's our line on pricing?", "channel": "C0123",
     "thread_ts": "1700000000.000100", "user": "U999", "event_ts": "1700000000.000100"}

The workflow is expected to post its own reply into the thread with the Slack
Send Message node (the answer loop of an n3rf-native Magi). Replies are
acknowledged immediately; the workflow runs in the background so Slack's
3-second ack window is never missed (at-least-once delivery applies, as always
with Slack events).

Env:
    SLACK_SIGNING_SECRET             required — from your Slack app
    SLACK_BOT_TOKEN                  required — xoxb-…
    N3RF_SLACK_TRIGGER_WORKFLOW_ID   required — id of the saved answering workflow
    N3RF_SLACK_TRIGGER_CHANNELS      optional — comma-separated channel IDs to allow
"""

from __future__ import annotations

import asyncio
import os
import re
from typing import Any

from app import store
from app.services.execution import run as execute_workflow

MENTION = re.compile(r"<@[A-Za-z0-9]+>")
WS = re.compile(r"\s{2,}")


def trigger_configured() -> bool:
    return all(
        os.environ.get(name)
        for name in ("SLACK_SIGNING_SECRET", "SLACK_BOT_TOKEN", "N3RF_SLACK_TRIGGER_WORKFLOW_ID")
    )


def allowed_channel(channel: str) -> bool:
    raw = os.environ.get("N3RF_SLACK_TRIGGER_CHANNELS", "").strip()
    if not raw:
        return True
    return channel in {part.strip() for part in raw.split(",") if part.strip()}


def mention_row(event: dict[str, Any]) -> dict[str, Any]:
    text = MENTION.sub(" ", str(event.get("text", "")))
    text = WS.sub(" ", text).strip()
    channel = str(event.get("channel", ""))
    thread_ts = str(event.get("thread_ts") or event.get("ts") or "")
    return {
        "question": text,
        "channel": channel,
        "thread_ts": thread_ts,
        "user": str(event.get("user", "")),
        "event_ts": str(event.get("ts", "")),
    }


async def _say(event: dict[str, Any], text: str) -> None:
    thread_ts = str(event.get("thread_ts") or event.get("ts") or "")
    try:
        from slack_sdk.web.async_client import AsyncWebClient

        api = os.environ.get("N3RF_SLACK_API_URL", "https://slack.com/api").rstrip("/") + "/"
        client = AsyncWebClient(token=os.environ.get("SLACK_BOT_TOKEN", ""), base_url=api)
        await client.chat_postMessage(
            channel=str(event.get("channel", "")), text=text, thread_ts=thread_ts or None
        )
    except Exception as exc:  # never let the error path take the loop down
        import sys

        print(f"[n3rf] slack trigger error-report failed: {exc}", file=sys.stderr)


async def _answer(event: dict[str, Any]) -> None:
    if not allowed_channel(str(event.get("channel", ""))):
        return
    workflow_id = os.environ.get("N3RF_SLACK_TRIGGER_WORKFLOW_ID", "")
    try:
        workflow = store.get_workflow(workflow_id)
        if workflow is None:
            await _say(
                event, f"The trigger workflow '{workflow_id}' does not exist in this workspace."
            )
            return
        await execute_workflow(
            workflow["nodes"], workflow["edges"], [mention_row(event)], workflow_id
        )
    except Exception as exc:
        await _say(event, f"The answering workflow failed: {exc}")


def _build_app():
    from slack_bolt.async_app import AsyncApp

    token = os.environ.get("SLACK_BOT_TOKEN", "")
    # Bolt otherwise verifies the token against auth.test on every cold start —
    # fine in production, but it breaks offline runs. Set these two env vars to
    # skip the network call (recommended for local/dev).
    bot_id = os.environ.get("SLACK_BOT_ID")
    bot_user_id = os.environ.get("SLACK_BOT_USER_ID")
    authorize = None
    if bot_id and bot_user_id:
        from slack_bolt.authorization import AuthorizeResult

        async def authorize() -> AuthorizeResult:  # noqa: B023 - fixed values
            return AuthorizeResult(
                enterprise_id=None,
                team_id=None,
                bot_token=token,
                bot_id=bot_id,
                bot_user_id=bot_user_id,
            )

    kwargs = {
        "signing_secret": os.environ.get("SLACK_SIGNING_SECRET", ""),
        "token": token,
    }
    if authorize is not None:
        kwargs["authorize"] = authorize
    app = AsyncApp(**kwargs)

    @app.event("app_mention")
    async def handle_mention(event):  # ack immediately; answer in background
        asyncio.create_task(_answer(event))

    return app


async def handle(request):
    from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler

    return await AsyncSlackRequestHandler(_build_app()).handle(request)


__all__ = [
    "trigger_configured",
    "allowed_channel",
    "mention_row",
    "handle",
]
