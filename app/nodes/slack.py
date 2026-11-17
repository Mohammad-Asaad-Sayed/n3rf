"""Slack pack — outbound messaging + thread reading, opt-in.

Scope note (same as the rest of n3rf): no connection/OAuth layer. Your bot
token comes from the environment (``SLACK_BOT_TOKEN``), never from saved
workflows; ``token`` pastes are run-only.

Nodes:

- ``slack_send_message`` — post to a channel or thread
- ``slack_add_reaction`` — add a reaction (approval/ack signal)
- ``slack_fetch_thread`` — read a thread's messages as rows

There is deliberately no inbound "listen for mentions" node: n3rf's engine is
push-model (``POST /workflows/{id}/run``). A Slack-native answer loop needs an
external listener or the future webhook/trigger work — see examples/slack.md.
Required scopes: chat:write, reactions:write, channels:history (public
channels), groups:history (private channels).
"""

from __future__ import annotations

import os
from typing import Any

from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

from app.contracts import ItemList, new_item
from app.errors import NodeError
from app.expressions import render
from app.params import Param
from app.registry import node

_DEFAULT_API = "https://slack.com/api"


def _creds_params() -> list[Param]:
    return [
        Param(
            "token_env",
            "string",
            "Bot token environment variable",
            default="SLACK_BOT_TOKEN",
            hint=(
                "Env var holding your bot token (xoxb-…). "
                "Scopes: chat:write, reactions:write, channels:history."
            ),
        ),
        Param(
            "token",
            "password",
            "Bot token (paste — run only)",
            default="",
            hint=(
                "Paste a token for this run only — never stored or logged. "
                "Leave blank to use the env var."
            ),
        ),
        Param(
            "api_url",
            "string",
            "API base URL",
            default=_DEFAULT_API,
            hint="Change only for proxies or enterprise grid.",
        ),
    ]


def _resolve_creds(ctx: Any) -> tuple[str, str]:
    token_env = ctx.param("token_env", str, "SLACK_BOT_TOKEN") or "SLACK_BOT_TOKEN"
    api_url = (ctx.param("api_url", str, _DEFAULT_API) or _DEFAULT_API).strip().rstrip("/") + "/"
    token = (ctx.param("token", str, "") or "").strip() or (
        os.environ.get(token_env, "") or ""
    ).strip()
    if not token:
        raise NodeError(f"Environment variable '{token_env}' is not set.")
    return token, api_url


def _client(ctx: Any) -> AsyncWebClient:
    token, api_url = _resolve_creds(ctx)
    return AsyncWebClient(token=token, base_url=api_url)


def _response_body(response: Any) -> dict[str, Any]:
    """Normalize a slack-sdk response to its JSON dict.

    The real AsyncSlackResponse is NOT a dict — the payload lives on ``.data``.
    Test doubles that return plain dicts are accepted too.
    """
    data = getattr(response, "data", response)
    return dict(data) if isinstance(data, dict) else {}


async def _slack_call(ctx: Any, method: str, payload: dict[str, Any]) -> dict[str, Any]:
    client = _client(ctx)
    caller = getattr(client, method)
    try:
        response = await caller(**payload)
    except SlackApiError as exc:
        body = exc.response.data if isinstance(exc.response.data, dict) else {}
        raise NodeError(f"Slack error: {body.get('error', 'unknown_error')}") from exc
    except Exception as exc:
        raise NodeError(f"Slack request failed: {exc}") from exc
    return _response_body(response)


@node(
    "slack_send_message",
    "Slack Send Message",
    group="slack",
    description=(
        "Post a message to a channel, optionally in a thread. "
        "Channel may be a channel ID (C…) or a name like #tech-problems."
    ),
    params=_creds_params()
    + [
        Param(
            "channel",
            "string",
            "Channel",
            default="#general",
            required=True,
            expression=True,
            hint="Channel ID or #name. Supports @ picks.",
        ),
        Param(
            "text",
            "textarea",
            "Message",
            default="",
            required=True,
            expression=True,
            hint='Supports @ picks, e.g. "Routing to the owner — {{summary}}".',
        ),
        Param(
            "thread_ts",
            "string",
            "Thread ts",
            default="",
            expression=True,
            hint="Parent message ts to reply in thread. Empty = new top-level message.",
        ),
    ],
)
async def slack_send_message(items: ItemList, ctx: Any) -> ItemList:
    channel = ctx.param("channel", str, required=True)
    text = ctx.param("text", str, required=True)
    thread_ts = ctx.param("thread_ts", str, "")
    targets = items if items else [{"json": {}, "meta": {}}]
    output: ItemList = []
    for index, item in enumerate(targets):
        resolved_channel = str(render(channel, item["json"]))
        resolved_text = str(render(text, item["json"]))
        ts = str(render(thread_ts, item["json"])) if thread_ts else ""
        method_kwargs: dict[str, Any] = {"channel": resolved_channel, "text": resolved_text}
        if ts:
            method_kwargs["thread_ts"] = ts
        body = await _slack_call(ctx, "chat_postMessage", method_kwargs)
        output.append(
            new_item(
                {
                    **item["json"],
                    "slack_channel": body.get("channel", resolved_channel),
                    "slack_ts": body.get("ts"),
                },
                paired=item["meta"].get("paired", index),
                node="slack_send_message",
                slack_message=True,
            )
        )
    return output


@node(
    "slack_add_reaction",
    "Slack Add Reaction",
    group="slack",
    description="Add a reaction to a message — the ack/approval signal, like a 👍 or 👀.",
    params=_creds_params()
    + [
        Param(
            "channel",
            "string",
            "Channel",
            default="#general",
            required=True,
            expression=True,
            hint="Channel ID or #name the message lives in.",
        ),
        Param(
            "ts",
            "string",
            "Message ts",
            default="",
            required=True,
            expression=True,
            hint="ts of the message to react to.",
        ),
        Param(
            "emoji",
            "string",
            "Emoji",
            default="eyes",
            hint="Name without colons, e.g. white_check_mark, eyes, thumbsup.",
        ),
    ],
)
async def slack_add_reaction(items: ItemList, ctx: Any) -> ItemList:
    channel = ctx.param("channel", str, required=True)
    ts = ctx.param("ts", str, required=True)
    emoji = (ctx.param("emoji", str, "eyes") or "eyes").strip().strip(":")
    targets = items if items else [{"json": {}, "meta": {}}]
    output: ItemList = []
    for index, item in enumerate(targets):
        body = await _slack_call(
            ctx,
            "reactions_add",
            {
                "channel": str(render(channel, item["json"])),
                "timestamp": str(render(ts, item["json"])),
                "name": emoji,
            },
        )
        output.append(
            new_item(
                {**item["json"], "slack_reacted": True, "slack_ts": body.get("ts")},
                paired=item["meta"].get("paired", index),
                node="slack_add_reaction",
                slack_reaction=emoji,
            )
        )
    return output


@node(
    "slack_fetch_thread",
    "Slack Fetch Thread",
    group="slack",
    description=(
        "Read a thread as rows: one row per message (parent first). "
        "Fields: text, user, ts, thread_ts, is_parent, replies."
    ),
    params=_creds_params()
    + [
        Param(
            "channel",
            "string",
            "Channel",
            default="#general",
            required=True,
            expression=True,
            hint="Channel ID or #name the thread lives in.",
        ),
        Param(
            "ts",
            "string",
            "Thread ts",
            default="",
            required=True,
            expression=True,
            hint="Parent message ts of the thread.",
        ),
        Param("limit", "number", "Limit", default=50, hint="Max messages to return (1-1000)."),
    ],
)
async def slack_fetch_thread(items: ItemList, ctx: Any) -> ItemList:
    channel = ctx.param("channel", str, required=True)
    ts = ctx.param("ts", str, required=True)
    limit = min(max(int(ctx.param("limit", (int, float), 50) or 50), 1), 1000)
    targets = items if items else [{"json": {}, "meta": {}}]
    output: ItemList = []
    for index, item in enumerate(targets):
        body = await _slack_call(
            ctx,
            "conversations_replies",
            {
                "channel": str(render(channel, item["json"])),
                "ts": str(render(ts, item["json"])),
                "limit": limit,
            },
        )
        messages = body.get("messages", []) or []
        channel_id = body.get("channel") or str(render(channel, item["json"]))
        thread_ts = str(render(ts, item["json"]))
        for msg in messages:
            is_parent = msg.get("ts") == thread_ts
            output.append(
                new_item(
                    {
                        "text": msg.get("text", ""),
                        "user": msg.get("user"),
                        "ts": msg.get("ts"),
                        "thread_ts": msg.get("thread_ts", thread_ts),
                        "channel": channel_id,
                        "is_parent": bool(is_parent),
                        "reply_count": msg.get("reply_count", 0),
                    },
                    paired=item["meta"].get("paired", index),
                    node="slack_fetch_thread",
                )
            )
    return output
