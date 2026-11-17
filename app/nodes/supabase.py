"""Supabase pack — thin PostgREST sugar, opt-in.

Three nodes covering the common shapes:

- ``supabase_select`` — read rows with a PostgREST ``filter`` string
- ``supabase_upsert`` — insert/merge rows (``Prefer: resolution=merge-duplicates``)
- ``supabase_rpc`` — call a Postgres function and return its result

Philosophy (unchanged): keys come from the environment, never from workflow
JSON. ``url``/``api_key`` params may paste values for a single run, but they
are never stored in saved workflows — the persisted params are just the env
var names and the non-secret bits (table, columns, filter, function).

``url``/``api_key`` are resolved as: explicit param → environment variable
(named by ``url_env`` / ``api_key_env``). An unreachable public URL is an
operator error, reported as ``NodeError``.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from app.contracts import ItemList, new_item
from app.errors import NodeError
from app.expressions import render, render_deep
from app.nodes.http import _check_url_safe
from app.params import Param
from app.registry import node

_MAX_UPSERT_ROWS = 1000
_MAX_SELECT_LIMIT = 10000


def _creds_params(*, url_hint: str = "https://xyz.supabase.co") -> list[Param]:
    return [
        Param(
            "url_env",
            "string",
            "URL environment variable",
            default="SUPABASE_URL",
            hint=f"Env var holding your Project URL, e.g. {url_hint}.",
        ),
        Param(
            "api_key_env",
            "string",
            "API key environment variable",
            default="SUPABASE_API_KEY",
            hint=(
                "Service-role key for server-side jobs (bypasses RLS). "
                "Use the anon key only when RLS allows what you need."
            ),
        ),
        Param(
            "api_key",
            "password",
            "API key (paste — run only)",
            default="",
            hint=(
                "Paste a key for this run only — never stored or logged. "
                "Leave blank to use the env var."
            ),
        ),
        Param(
            "url",
            "string",
            "Project URL",
            default="",
            hint=f"Optional override, e.g. {url_hint}. Leave blank to use the env var above.",
        ),
    ]


def _resolve_creds(ctx: Any) -> tuple[str, str]:
    url_env = ctx.param("url_env", str, "SUPABASE_URL") or "SUPABASE_URL"
    api_key_env = ctx.param("api_key_env", str, "SUPABASE_API_KEY") or "SUPABASE_API_KEY"

    url = (ctx.param("url", str, "") or "").strip().rstrip("/")
    if not url:
        url = (os.environ.get(url_env, "") or "").strip().rstrip("/")
    if not url:
        raise NodeError(f"Environment variable '{url_env}' is not set.")
    _check_url_safe(url)

    api_key = (ctx.param("api_key", str, "") or "").strip() or (
        os.environ.get(api_key_env, "") or ""
    ).strip()
    if not api_key:
        raise NodeError(f"Environment variable '{api_key_env}' is not set.")
    return url, api_key


def _headers(key: str, *, prefer: str | None = None) -> dict[str, str]:
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer
    return headers


async def _request(
    ctx: Any,
    method: str,
    path: str,
    *,
    params: dict[str, str] | None = None,
    json_body: Any = None,
    prefer: str | None = None,
) -> tuple[int, Any]:
    url, api_key = _resolve_creds(ctx)
    endpoint = f"{url}{path}"
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
        response = await client.request(
            method,
            endpoint,
            headers=_headers(api_key, prefer=prefer),
            params=params,
            json=json_body,
        )
    if response.status_code >= 400:
        detail = response.text[:500]
        try:
            payload = response.json()
            detail = str(payload.get("message") or payload.get("error") or payload)[:500]
        except ValueError:
            pass
        raise NodeError(f"Supabase request failed: {response.status_code} {detail}")
    if not response.content or response.status_code == 204:
        return response.status_code, None
    try:
        return response.status_code, response.json()
    except ValueError:
        return response.status_code, {"text": response.text}


@node(
    "supabase_select",
    "Supabase Select",
    group="supabase",
    description=(
        "Read rows from a table with a PostgREST filter string. "
        "Example filter: kb_domain=eq.launches&path=eq.answer. "
        "Leave filter empty to pull the whole table (up to the limit)."
    ),
    params=_creds_params()
    + [
        Param(
            "table",
            "string",
            "Table",
            default="decisions",
            required=True,
            expression=True,
            hint="Table name. Supports @ picks, e.g. decisions",
        ),
        Param(
            "columns",
            "string",
            "Columns",
            default="*",
            hint="PostgREST select string, e.g. id,path,cited_kb",
        ),
        Param(
            "filter",
            "string",
            "Filter",
            default="",
            expression=True,
            hint=(
                "PostgREST filter query without leading '?', "
                "e.g. path=eq.answer&cited_kb=not.is.null"
            ),
        ),
        Param(
            "limit",
            "number",
            "Limit",
            default=50,
            hint=f"Max rows to return (1-{_MAX_SELECT_LIMIT}).",
        ),
        Param(
            "per_row",
            "boolean",
            "Call per row",
            default=False,
            hint="Enable when table/columns/filter use @ picks to vary per incoming row.",
        ),
    ],
)
async def supabase_select(items: ItemList, ctx: Any) -> ItemList:
    table = ctx.param("table", str, required=True)
    columns = ctx.param("columns", str, "*")
    limit = ctx.param("limit", (int, float), 50)
    per_row = ctx.param("per_row", bool, False)
    limit_int = min(max(int(limit), 1), _MAX_SELECT_LIMIT)

    targets: list = items if per_row else [items[0] if items else {"json": {}, "meta": {}}]
    output: ItemList = []
    for index, item in enumerate(targets):
        row_table = str(render(table, item["json"]))
        row_columns = str(render(columns, item["json"]))
        row_filter = str(render(ctx.param("filter", str, "") or "", item["json"]))
        params = {"select": row_columns, "limit": str(limit_int)}
        if row_filter:
            params.update(dict(part.split("=", 1) for part in row_filter.split("&") if "=" in part))
        _, payload = await _request(ctx, "GET", f"/rest/v1/{row_table}", params=params)
        if not isinstance(payload, list):
            raise NodeError("Supabase returned a non-list response — check the table and filter.")
        for row in payload:
            if isinstance(row, dict):
                output.append(
                    new_item(
                        row,
                        paired=item["meta"].get("paired", index),
                        node="supabase_select",
                        supabase_table=row_table,
                    )
                )
    return output


@node(
    "supabase_upsert",
    "Supabase Upsert",
    group="supabase",
    description=(
        "Insert rows, merging on a conflict column. "
        "Rows come from the incoming list — one HTTP call. "
        "Set on_conflict to empty to behave as a plain insert."
    ),
    params=_creds_params()
    + [
        Param(
            "table",
            "string",
            "Table",
            default="decisions",
            required=True,
            expression=True,
            hint="Table name. Supports @ picks, e.g. decisions",
        ),
        Param(
            "on_conflict",
            "string",
            "On conflict",
            default="id",
            hint="Column(s) to merge on, e.g. thread_id. Empty = plain insert.",
        ),
    ],
)
async def supabase_upsert(items: ItemList, ctx: Any) -> ItemList:
    table = ctx.param("table", str, required=True)
    on_conflict = (ctx.param("on_conflict", str, "id") or "").strip()
    rows = [dict(item["json"]) for item in items]
    if not rows:
        return []
    if len(rows) > _MAX_UPSERT_ROWS:
        raise NodeError(f"Supabase Upsert accepts at most {_MAX_UPSERT_ROWS} rows per call.")

    row_table = str(render(table, rows[0]))
    prefer = "return=minimal" if not on_conflict else "resolution=merge-duplicates,return=minimal"
    params = {"on_conflict": on_conflict} if on_conflict else None
    status, _ = await _request(
        ctx, "POST", f"/rest/v1/{row_table}", params=params, json_body=rows, prefer=prefer
    )
    return [
        {
            "json": dict(item["json"]),
            "meta": {**item["meta"], "supabase_status": status, "supabase_table": row_table},
        }
        for item in items
    ]


@node(
    "supabase_rpc",
    "Supabase RPC",
    group="supabase",
    description=(
        "Call a Postgres function exposed via PostgREST. "
        "Payload is JSON; if it contains @ picks it renders per incoming row."
    ),
    params=_creds_params()
    + [
        Param(
            "function",
            "string",
            "Function",
            default="log_decision",
            required=True,
            expression=True,
            hint="RPC name, e.g. log_decision",
        ),
        Param(
            "payload",
            "json",
            "Payload",
            default={},
            hint=(
                "JSON object passed as the function arguments, "
                'e.g. {"p_thread_id": "@{{thread_id}}"}.'
            ),
        ),
    ],
)
async def supabase_rpc(items: ItemList, ctx: Any) -> ItemList:
    function = ctx.param("function", str, required=True)
    payload = ctx.param("payload", dict, {}) or {}
    per_row = bool(items) and "{{" in str(payload)
    targets = items if per_row else [items[0] if items else {"json": {}, "meta": {}}]
    output: ItemList = []
    for index, item in enumerate(targets):
        row_function = str(render(function, item["json"]))
        row_payload = render_deep(payload, item["json"]) if per_row else payload
        _, body = await _request(ctx, "POST", f"/rpc/{row_function}", json_body=row_payload)
        rows = body if isinstance(body, list) else [body]
        for row in rows:
            if isinstance(row, dict):
                output.append(
                    new_item(
                        row,
                        paired=item["meta"].get("paired", index),
                        node="supabase_rpc",
                        supabase_function=row_function,
                    )
                )
            else:
                output.append(
                    new_item(
                        {"value": row},
                        paired=item["meta"].get("paired", index),
                        node="supabase_rpc",
                    )
                )
    return output
