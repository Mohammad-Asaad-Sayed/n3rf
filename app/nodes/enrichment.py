from __future__ import annotations

import asyncio
import os
from typing import Any

import httpx

from app.contracts import Item, ItemList
from app.errors import NodeError
from app.expressions import render
from app.params import Param
from app.registry import node


def _get_key(env_name: str) -> str:
    if not env_name:
        return ""
    value = os.environ.get(env_name, "")
    if not value:
        raise NodeError(f"Environment variable '{env_name}' is not set.")
    return value


def _resolve_key(env_name: str, override: str) -> str:
    # Dual BYOK: a pasted key (per-request, never persisted) wins over the
    # env-var value. Blank paste falls back to the env var.
    pasted = (override or "").strip()
    if pasted:
        return pasted
    return _get_key(env_name)


async def _fanout(items: ItemList, ctx: Any, callback: Any) -> ItemList:
    concurrency = ctx.param("concurrency", int, 8)
    cap = ctx.param("max_output_rows", int, 500)
    policy = ctx.param("on_error", str, "error_item")
    if concurrency < 1 or concurrency > 64:
        raise NodeError("Parameter 'concurrency' must be between 1 and 64.")
    if cap < 1 or cap > 10000:
        raise NodeError("Parameter 'max_output_rows' must be between 1 and 10000.")
    semaphore = asyncio.Semaphore(concurrency)

    async def one(index: int, item: Item) -> ItemList:
        async with semaphore:
            try:
                return await callback(index, item)
            except Exception as exc:
                if policy == "fail":
                    raise NodeError(f"Row {index + 1}: {exc}") from exc
                ctx.logs.append(f"Row {index + 1}: {exc}")
                if policy == "skip":
                    return []
                return [
                    {
                        "json": dict(item["json"]),
                        "meta": {**item["meta"], "error": str(exc)},
                    }
                ]

    results = await asyncio.gather(*(one(index, item) for index, item in enumerate(items)))
    output = [row for group in results for row in group]
    if len(output) > cap:
        raise NodeError(f"Output exceeded max_output_rows ({cap}).")
    return output


# --- Web search (monthly replenishing) ---


@node(
    "tavily_search",
    "Tavily Search",
    group="search",
    description=(
        "Search the web for each row. Needs TAVILY_API_KEY. "
        "Adds tavily_results (title, url, content) to each row."
    ),
    params=[
        Param(
            "query",
            "string",
            "Query",
            default="{{company}} funding",
            required=True,
            expression=True,
            hint="Runs once per row. @ picks a field. Example: {{company}} funding",
        ),
        Param(
            "api_key_env",
            "string",
            "API key environment variable",
            default="TAVILY_API_KEY",
            hint=(
                "Must already exist in the terminal that runs uvicorn. "
                "Or paste a key below for this run only."
            ),
        ),
        Param(
            "api_key",
            "password",
            "API key (paste — run only)",
            default="",
            hint=(
                "Paste a key for this run only — never saved or logged. "
                "Leave blank to use the env var above."
            ),
        ),
        Param("max_results", "number", "Max results", default=5),
        Param(
            "search_depth",
            "select",
            "Search depth",
            default="basic",
            options=["basic", "advanced"],
        ),
        Param("include_answer", "boolean", "Include AI answer", default=False),
        Param("concurrency", "number", "Concurrency", default=4),
        Param("max_output_rows", "number", "Maximum output rows", default=500),
        Param(
            "on_error",
            "select",
            "On row error",
            default="error_item",
            options=["error_item", "skip", "fail"],
        ),
    ],
)
async def tavily_search(items: ItemList, ctx: Any) -> ItemList:
    if not items:
        return []
    env_key = ctx.param("api_key_env", str, "TAVILY_API_KEY")
    api_key = _resolve_key(env_key, ctx.param("api_key", str, ""))
    query_tmpl = ctx.param("query", str, required=True)
    max_results = int(ctx.param("max_results", int, 5))
    if max_results < 1 or max_results > 10:
        raise NodeError("Parameter 'max_results' must be between 1 and 10.")
    search_depth = ctx.param("search_depth", str, "basic")
    include_answer = bool(ctx.param("include_answer", bool, False))

    async def call(index: int, item: Item) -> ItemList:
        query = render(query_tmpl, item["json"]).strip()
        if not query:
            raise NodeError(f"Row {index + 1}: query resolved to empty.")
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        body = {
            "query": query,
            "max_results": max_results,
            "search_depth": search_depth,
            "include_answer": include_answer,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post("https://api.tavily.com/search", headers=headers, json=body)
            if resp.status_code != 200:
                raise NodeError(f"Tavily request failed: {resp.status_code} {resp.text[:500]}")
            payload = resp.json()
        results = payload.get("results", [])
        out_json = dict(item["json"])
        out_json["tavily_query"] = query
        out_json["tavily_results"] = [
            {
                "title": r.get("title"),
                "url": r.get("url"),
                "content": r.get("content"),
                "score": r.get("score"),
            }
            for r in results
        ]
        if include_answer:
            out_json["tavily_answer"] = payload.get("answer")
        return [{"json": out_json, "meta": dict(item["meta"])}]

    return await _fanout(items, ctx, call)


@node(
    "exa_search",
    "Exa Search",
    group="search",
    description=(
        "Neural-search the web for each row. Needs EXA_API_KEY. "
        "Adds exa_results (title, url) to each row."
    ),
    params=[
        Param(
            "query",
            "string",
            "Query",
            default="{{company}} funding",
            required=True,
            expression=True,
            hint="Runs once per row. @ picks a field. Example: {{company}} funding",
        ),
        Param(
            "api_key_env",
            "string",
            "API key environment variable",
            default="EXA_API_KEY",
            hint=(
                "Must already exist in the terminal that runs uvicorn. "
                "Or paste a key below for this run only."
            ),
        ),
        Param(
            "api_key",
            "password",
            "API key (paste — run only)",
            default="",
            hint=(
                "Paste a key for this run only — never saved or logged. "
                "Leave blank to use the env var above."
            ),
        ),
        Param("num_results", "number", "Num results", default=5),
        Param(
            "type",
            "select",
            "Type",
            default="auto",
            options=["auto", "fast", "neural"],
        ),
        Param("include_text", "boolean", "Include text", default=False),
        Param("concurrency", "number", "Concurrency", default=4),
        Param("max_output_rows", "number", "Maximum output rows", default=500),
        Param(
            "on_error",
            "select",
            "On row error",
            default="error_item",
            options=["error_item", "skip", "fail"],
        ),
    ],
)
async def exa_search(items: ItemList, ctx: Any) -> ItemList:
    if not items:
        return []
    env_key = ctx.param("api_key_env", str, "EXA_API_KEY")
    api_key = _resolve_key(env_key, ctx.param("api_key", str, ""))
    query_tmpl = ctx.param("query", str, required=True)
    num_results = int(ctx.param("num_results", int, 5))
    if num_results < 1 or num_results > 10:
        raise NodeError("Parameter 'num_results' must be between 1 and 10.")
    search_type = ctx.param("type", str, "auto")
    include_text = bool(ctx.param("include_text", bool, False))

    async def call(index: int, item: Item) -> ItemList:
        query = render(query_tmpl, item["json"]).strip()
        if not query:
            raise NodeError(f"Row {index + 1}: query resolved to empty.")
        headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        body = {"query": query, "numResults": num_results, "type": search_type}
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post("https://api.exa.ai/search", headers=headers, json=body)
            if resp.status_code != 200:
                raise NodeError(f"Exa request failed: {resp.status_code} {resp.text[:500]}")
            payload = resp.json()
        results = payload.get("results", [])
        out_json = dict(item["json"])
        out_json["exa_query"] = query
        out_json["exa_results"] = [
            {
                "title": r.get("title"),
                "url": r.get("url"),
                "score": r.get("score"),
                "text": r.get("text") if include_text else None,
            }
            for r in results
        ]
        return [{"json": out_json, "meta": dict(item["meta"])}]

    return await _fanout(items, ctx, call)


@node(
    "serpapi_search",
    "SerpApi Search",
    group="search",
    description=(
        "Search Google or Bing for each row via SerpApi. Needs SERPAPI_API_KEY. "
        "Adds serp_results (title, url, snippet) to each row."
    ),
    params=[
        Param(
            "query",
            "string",
            "Query",
            default="{{company}} funding",
            required=True,
            expression=True,
            hint="Runs once per row. @ picks a field. Example: {{company}} funding",
        ),
        Param(
            "api_key_env",
            "string",
            "API key environment variable",
            default="SERPAPI_API_KEY",
            hint=(
                "Must already exist in the terminal that runs uvicorn. "
                "Or paste a key below for this run only."
            ),
        ),
        Param(
            "api_key",
            "password",
            "API key (paste — run only)",
            default="",
            hint=(
                "Paste a key for this run only — never saved or logged. "
                "Leave blank to use the env var above."
            ),
        ),
        Param("max_results", "number", "Max results", default=5),
        Param(
            "engine",
            "select",
            "Engine",
            default="google",
            options=["google", "bing", "google_news"],
        ),
        Param("concurrency", "number", "Concurrency", default=4),
        Param("max_output_rows", "number", "Maximum output rows", default=500),
        Param(
            "on_error",
            "select",
            "On row error",
            default="error_item",
            options=["error_item", "skip", "fail"],
        ),
    ],
)
async def serpapi_search(items: ItemList, ctx: Any) -> ItemList:
    if not items:
        return []
    env_key = ctx.param("api_key_env", str, "SERPAPI_API_KEY")
    api_key = _resolve_key(env_key, ctx.param("api_key", str, ""))
    query_tmpl = ctx.param("query", str, required=True)
    max_results = int(ctx.param("max_results", int, 5))
    if max_results < 1 or max_results > 10:
        raise NodeError("Parameter 'max_results' must be between 1 and 10.")
    engine = ctx.param("engine", str, "google")

    async def call(index: int, item: Item) -> ItemList:
        query = render(query_tmpl, item["json"]).strip()
        if not query:
            raise NodeError(f"Row {index + 1}: query resolved to empty.")
        params = {
            "engine": engine,
            "q": query,
            "api_key": api_key,
            "num": max_results,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get("https://serpapi.com/search.json", params=params)
            if resp.status_code != 200:
                raise NodeError(f"SerpApi request failed: {resp.status_code} {resp.text[:500]}")
            payload = resp.json()
        out_json = dict(item["json"])
        out_json["serp_query"] = query
        out_json["serp_results"] = [
            {
                "title": r.get("title"),
                "url": r.get("link"),
                "content": r.get("snippet"),
                "position": r.get("position"),
            }
            for r in payload.get("organic_results", [])
        ]
        return [{"json": out_json, "meta": dict(item["meta"])}]

    return await _fanout(items, ctx, call)


# --- Web reader (replenishing) ---


@node(
    "tavily_extract",
    "Tavily Extract",
    group="search",
    description=(
        "Fetch a URL as markdown for each row. Needs TAVILY_API_KEY. "
        "Adds tavily_content to each row."
    ),
    params=[
        Param(
            "url",
            "string",
            "URL",
            default="{{website}}",
            required=True,
            expression=True,
            hint="Runs once per row. @ picks a field. Example: {{website}}",
        ),
        Param(
            "api_key_env",
            "string",
            "API key environment variable",
            default="TAVILY_API_KEY",
            hint=(
                "Must already exist in the terminal that runs uvicorn. "
                "Or paste a key below for this run only."
            ),
        ),
        Param(
            "api_key",
            "password",
            "API key (paste — run only)",
            default="",
            hint=(
                "Paste a key for this run only — never saved or logged. "
                "Leave blank to use the env var above."
            ),
        ),
        Param(
            "extract_depth",
            "select",
            "Extract depth",
            default="basic",
            options=["basic", "advanced"],
        ),
        Param(
            "format",
            "select",
            "Format",
            default="markdown",
            options=["markdown", "text"],
        ),
        Param("concurrency", "number", "Concurrency", default=4),
        Param("max_output_rows", "number", "Maximum output rows", default=500),
        Param(
            "on_error",
            "select",
            "On row error",
            default="error_item",
            options=["error_item", "skip", "fail"],
        ),
    ],
)
async def tavily_extract(items: ItemList, ctx: Any) -> ItemList:
    if not items:
        return []
    env_key = ctx.param("api_key_env", str, "TAVILY_API_KEY")
    api_key = _resolve_key(env_key, ctx.param("api_key", str, ""))
    url_tmpl = ctx.param("url", str, required=True)
    extract_depth = ctx.param("extract_depth", str, "basic")
    fmt = ctx.param("format", str, "markdown")

    async def call(index: int, item: Item) -> ItemList:
        url = render(url_tmpl, item["json"]).strip()
        if not url or not url.startswith(("http://", "https://")):
            raise NodeError(f"Row {index + 1}: 'url' must be an HTTP(S) URL.")
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        body = {"urls": [url], "extract_depth": extract_depth, "format": fmt}
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post("https://api.tavily.com/extract", headers=headers, json=body)
            if resp.status_code != 200:
                raise NodeError(f"Tavily extract failed: {resp.status_code} {resp.text[:500]}")
            payload = resp.json()
        results = payload.get("results", [])
        first = results[0] if results else {}
        content = first.get("raw_content") or first.get("content") or ""
        out_json = dict(item["json"])
        out_json["tavily_url"] = url
        out_json["tavily_content"] = content
        if first.get("images"):
            out_json["tavily_images"] = first.get("images")
        return [{"json": out_json, "meta": dict(item["meta"])}]

    return await _fanout(items, ctx, call)


@node(
    "jina_reader",
    "Jina Reader",
    group="search",
    description=(
        "Fetch a URL as markdown for each row. Start here — works with no key. "
        "Adds jina_content to each row."
    ),
    params=[
        Param(
            "url",
            "string",
            "URL",
            default="{{website}}",
            required=True,
            expression=True,
            hint="Runs once per row. @ picks a field. Example: {{website}}",
        ),
        Param(
            "api_key_env",
            "string",
            "API key environment variable (optional)",
            default="",
            hint="Leave empty for anonymous 20 RPM. Set JINA_API_KEY for 500 RPM.",
        ),
        Param(
            "api_key",
            "password",
            "API key (paste — run only)",
            default="",
            hint=(
                "Paste a key for this run only — never saved or logged. "
                "Leave blank for anonymous use."
            ),
        ),
        Param(
            "format",
            "select",
            "Format",
            default="markdown",
            options=["markdown", "text", "html"],
        ),
        Param("concurrency", "number", "Concurrency", default=4),
        Param("max_output_rows", "number", "Maximum output rows", default=500),
        Param(
            "on_error",
            "select",
            "On row error",
            default="error_item",
            options=["error_item", "skip", "fail"],
        ),
    ],
)
async def jina_reader(items: ItemList, ctx: Any) -> ItemList:
    if not items:
        return []
    url_tmpl = ctx.param("url", str, required=True)
    env_key = ctx.param("api_key_env", str, "")
    fmt = ctx.param("format", str, "markdown")
    api_key = _resolve_key(env_key, ctx.param("api_key", str, ""))

    async def call(index: int, item: Item) -> ItemList:
        url = render(url_tmpl, item["json"]).strip()
        if not url or not url.startswith(("http://", "https://")):
            raise NodeError(f"Row {index + 1}: 'url' must be an HTTP(S) URL.")
        headers = {"Accept": "text/plain" if fmt == "text" else "text/markdown"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(f"https://r.jina.ai/{url}", headers=headers)
            if resp.status_code != 200:
                raise NodeError(f"Jina Reader failed: {resp.status_code} {resp.text[:500]}")
            text = resp.text
        out_json = dict(item["json"])
        out_json["jina_url"] = url
        out_json["jina_content"] = text[:20000]
        return [{"json": out_json, "meta": dict(item["meta"])}]

    return await _fanout(items, ctx, call)
