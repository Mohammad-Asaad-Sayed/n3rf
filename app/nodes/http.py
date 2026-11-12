from __future__ import annotations

import ipaddress
import os
import re
import socket
from typing import Any
from urllib.parse import urlparse

import httpx

from app.contracts import ItemList
from app.errors import NodeError
from app.expressions import render
from app.params import Param
from app.registry import node


def _check_url_safe(url: str) -> None:
    """Block requests to private/loopback/link-local hosts (SSRF guard)."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise NodeError("HTTP URL must use http or https.")
    host = parsed.hostname
    if not host:
        raise NodeError("HTTP URL is missing a host.")
    lowered = host.lower()
    if lowered in ("localhost",) or lowered.endswith(".local") or lowered.endswith(".internal"):
        raise NodeError(f"HTTP URL host '{host}' is not allowed.")
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except ValueError:
            continue
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise NodeError(f"HTTP URL resolves to a non-public address ({ip}).")


@node(
    "http_request",
    "HTTP Request",
    group="transform",
    description="Call any web address. Use it to reach services n3rf doesn't bundle.",
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
            default="https://example.com/api/{{company}}",
            required=True,
            expression=True,
            hint=(
                "Runs per row when per-row is on. @ picks a field. "
                "Example: https://example.com/api/{{company}}"
            ),
        ),
        Param(
            "headers",
            "json",
            "Headers",
            default={},
            hint=(
                "JSON object. Sensitive values must be ${ENV:NAME}, "
                'e.g. {"Authorization":"Bearer ${ENV:MY_KEY}"}.'
            ),
        ),
        Param("body", "json", "Body", default={}, hint="JSON sent for POST, PUT, PATCH."),
        Param("per_row", "boolean", "Call once per row", default=True),
        Param(
            "timeout",
            "number",
            "Timeout",
            default=30,
            unit="seconds",
            hint="Seconds to wait for each request.",
        ),
        Param(
            "run_once",
            "boolean",
            "Skip rows already fetched",
            default=False,
            hint="Skip a row if it was already fetched in a previous run of this node.",
        ),
    ],
)
async def http_request(items: ItemList, ctx: Any) -> ItemList:
    if os.environ.get("N3RF_HTTP_NODE_DISABLED", "").lower() in ("1", "true", "yes"):
        raise NodeError("HTTP Request node is disabled by N3RF_HTTP_NODE_DISABLED.")
    method, url = ctx.param("method", str, "GET"), ctx.param("url", str, required=True)
    headers = ctx.param("headers", dict, {})
    body = ctx.param("body", default={})
    timeout = ctx.param("timeout", (int, float), 30)
    run_once = ctx.param("run_once", bool, False)
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
    async with httpx.AsyncClient(timeout=float(timeout), follow_redirects=False) as client:
        for item in targets:
            meta = dict(item["meta"])
            if run_once and meta.get("_http_done"):
                output.append({"json": dict(item["json"]), "meta": meta})
                continue
            try:
                resolved_url = str(render(url, item["json"]))
                _check_url_safe(resolved_url)
                response = await client.request(
                    method,
                    resolved_url,
                    headers=resolved_headers,
                    json=body if method != "GET" else None,
                )
                response.raise_for_status()
                try:
                    value = response.json()
                except ValueError:
                    value = {"text": response.text}
            except (httpx.HTTPError, NodeError) as exc:
                raise NodeError(f"HTTP request failed: {exc}") from exc
            meta["_http_done"] = True
            output.append(
                {
                    "json": {"response": value, "status_code": response.status_code},
                    "meta": meta,
                }
            )
    return output
