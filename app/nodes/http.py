from __future__ import annotations

import os
import re
from typing import Any

import httpx

from app.contracts import ItemList
from app.errors import NodeError
from app.expressions import render
from app.params import Param
from app.registry import node


@node(
    "http_request",
    "HTTP Request",
    group="transform",
    description="Call a generic HTTP endpoint.",
    params=[
        Param(
            "method",
            "select",
            "Method",
            default="GET",
            options=["GET", "POST", "PUT", "PATCH", "DELETE"],
        ),
        Param(
            "url",
            "string",
            "URL",
            default="",
            required=True,
            expression=True,
            hint="Type @ to insert a field from each incoming row.",
        ),
        Param("headers", "json", "Headers", default={}),
        Param("body", "json", "Body", default={}),
        Param("per_row", "boolean", "Call once per row", default=True),
    ],
)
async def http_request(items: ItemList, ctx: Any) -> ItemList:
    method, url = ctx.param("method", str, "GET"), ctx.param("url", str, required=True)
    headers = ctx.param("headers", dict, {})
    body = ctx.param("body", default={})
    env_pattern = re.compile(r"\$\{ENV:([A-Za-z_][A-Za-z0-9_]*)\}")
    resolved_headers = {}
    for key, value in headers.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise NodeError("HTTP header names and values must be strings.")
        sensitive = any(word in key.lower() for word in ("authorization", "token", "secret", "key"))
        if sensitive and (not isinstance(value, str) or not env_pattern.search(value)):
            raise NodeError(f"Header '{key}' must reference a secret with ${{ENV:NAME}}.")
        if isinstance(value, str):
            resolved_headers[key] = env_pattern.sub(
                lambda match: os.environ.get(match.group(1), ""), value
            )
            missing = [
                match.group(1)
                for match in env_pattern.finditer(value)
                if match.group(1) not in os.environ
            ]
            if missing:
                raise NodeError(f"Environment variable '{missing[0]}' is not set.")
        else:
            resolved_headers[key] = value
    per_row = ctx.param("per_row", bool, True)
    targets = items if per_row else [items[0] if items else {"json": {}, "meta": {}}]
    output = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        for item in targets:
            try:
                response = await client.request(
                    method,
                    str(render(url, item["json"])),
                    headers=resolved_headers,
                    json=body if method != "GET" else None,
                )
                response.raise_for_status()
                try:
                    value = response.json()
                except ValueError:
                    value = {"text": response.text}
            except httpx.HTTPError as exc:
                raise NodeError(f"HTTP request failed: {exc}") from exc
            output.append(
                {
                    "json": {"response": value, "status_code": response.status_code},
                    "meta": dict(item["meta"]),
                }
            )
    return output
