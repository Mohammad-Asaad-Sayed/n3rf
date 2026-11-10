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
        raise NodeError(
            f"Environment variable '{env_name}' is not set. "
            "Set it in the shell that runs FastAPI, or open the node's "
            "Advanced params and paste a key — it is used once and never saved."
        )
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


# --- Tavily: one node, three modes ---


@node(
    "tavily",
    "Tavily",
    group="search",
    description=(
        "Search the web, extract one URL's content, or map a whole site — pick a mode. "
        "Needs TAVILY_API_KEY. Adds tavily_results (search), tavily_content (extract), "
        "or tavily_map + tavily_map_count (map) to each row."
    ),
    params=[
        Param(
            "mode",
            "select",
            "Mode",
            default="search",
            options=["search", "extract", "map"],
            hint=(
                "search: find fresh pages for each row · extract: read one URL · "
                "map: crawl a site into a URL list"
            ),
        ),
        Param(
            "query",
            "string",
            "Query",
            default="{{company}} funding",
            required=True,
            expression=True,
            show_if={"param": "mode", "in": ["search"]},
            hint="Runs once per row. @ picks a field. Example: {{company}} funding",
        ),
        Param(
            "url",
            "string",
            "URL",
            default="{{website}}",
            required=True,
            expression=True,
            show_if={"param": "mode", "in": ["extract", "map"]},
            hint=(
                "Runs once per row. @ picks a field. Extract usually means a row "
                "field ({{website}}); Map usually wants a fixed root such as "
                "https://example.com"
            ),
        ),
        Param(
            "instructions",
            "string",
            "Instructions",
            default="",
            expression=True,
            show_if={"param": "mode", "in": ["map"]},
            hint=(
                "Natural-language guidance for the crawler, e.g. 'Find all pages "
                "about the Python SDK'. Raises the per-page cost to 2 credits "
                "per 10 pages (vs 1). Leave blank for plain traversal."
            ),
        ),
        Param(
            "topic",
            "select",
            "Topic",
            default="general",
            options=["general", "news", "finance"],
            show_if={"param": "mode", "in": ["search"]},
            hint="general: broad web · news: recent news · finance: financial sources",
        ),
        Param(
            "time_range",
            "select",
            "Time range",
            default="",
            options=["", "day", "week", "month", "year"],
            show_if={"param": "mode", "in": ["search"]},
            hint="Only return results from this period back. Blank = any time.",
        ),
        Param(
            "include_domains",
            "string",
            "Only these domains",
            default="",
            show_if={"param": "mode", "in": ["search"]},
            hint="Hostnames only, comma-separated. Restricts results to these sites.",
        ),
        Param(
            "exclude_domains",
            "string",
            "Exclude domains",
            default="",
            show_if={"param": "mode", "in": ["search"]},
            hint="Hostnames only, comma-separated. Drops these sites from results.",
        ),
        Param(
            "max_results",
            "number",
            "Max results",
            default=5,
            show_if={"param": "mode", "in": ["search"]},
        ),
        Param(
            "search_depth",
            "select",
            "Search depth",
            default="basic",
            options=["basic", "advanced"],
            show_if={"param": "mode", "in": ["search"]},
        ),
        Param(
            "include_answer",
            "boolean",
            "Include AI answer",
            default=False,
            show_if={"param": "mode", "in": ["search"]},
        ),
        Param(
            "extract_depth",
            "select",
            "Extract depth",
            default="basic",
            options=["basic", "advanced"],
            show_if={"param": "mode", "in": ["extract"]},
        ),
        Param(
            "format",
            "select",
            "Format",
            default="markdown",
            options=["markdown", "text"],
            show_if={"param": "mode", "in": ["extract"]},
        ),
        Param(
            "max_depth",
            "number",
            "Crawl depth",
            default=1,
            show_if={"param": "mode", "in": ["map"]},
            hint="How far from the base URL the crawler may follow links (1–5).",
        ),
        Param(
            "max_breadth",
            "number",
            "Links per page",
            default=20,
            show_if={"param": "mode", "in": ["map"]},
            hint="How many links to follow per level (1–500).",
        ),
        Param(
            "limit",
            "number",
            "Total link limit",
            default=25,
            show_if={"param": "mode", "in": ["map"]},
            hint="Stop after this many discovered URLs (1–1000).",
        ),
        Param(
            "select_paths",
            "string",
            "Select paths (regex)",
            default="",
            show_if={"param": "mode", "in": ["map"]},
            hint="Only map URLs whose path matches. Comma-separated, e.g. /docs/.* .",
        ),
        Param(
            "select_domains",
            "string",
            "Select domains (regex)",
            default="",
            show_if={"param": "mode", "in": ["map"]},
            hint=(
                "Only map these domains/subdomains. Comma-separated, e.g. ^docs\\.example\\.com$ ."
            ),
        ),
        Param(
            "exclude_paths",
            "string",
            "Exclude paths (regex)",
            default="",
            show_if={"param": "mode", "in": ["map"]},
            hint="Skip URLs whose path matches. Comma-separated, e.g. /private/.* .",
        ),
        Param(
            "exclude_domains",
            "string",
            "Exclude domains (regex)",
            default="",
            show_if={"param": "mode", "in": ["map"]},
            hint="Never map these domains/subdomains. Comma-separated.",
        ),
        Param(
            "allow_external",
            "boolean",
            "Allow external domains",
            default=False,
            show_if={"param": "mode", "in": ["map"]},
            hint="Include URLs on other domains in the results list.",
        ),
        Param(
            "timeout",
            "number",
            "Timeout (seconds)",
            default=150,
            show_if={"param": "mode", "in": ["map"]},
            hint="Max time for the map operation (10–150).",
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
async def tavily(items: ItemList, ctx: Any) -> ItemList:
    mode = ctx.param("mode", str, "search")
    if mode == "search":
        return await _tavily_search_rows(items, ctx)
    if mode == "extract":
        return await _tavily_extract_rows(items, ctx)
    if mode == "map":
        return await _tavily_map_rows(items, ctx)
    raise NodeError(f"Parameter 'mode' must be one of: search, extract, map — got '{mode}'.")


async def _tavily_search_rows(items: ItemList, ctx: Any) -> ItemList:
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
    topic = ctx.param("topic", str, "general")
    time_range = ctx.param("time_range", str, "")
    include_domains = _split_csv(ctx.param("include_domains", str, ""))
    exclude_domains = _split_csv(ctx.param("exclude_domains", str, ""))

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
            "topic": topic,
        }
        if time_range:
            body["time_range"] = time_range
        if include_domains:
            body["include_domains"] = include_domains
        if exclude_domains:
            body["exclude_domains"] = exclude_domains
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


async def _tavily_extract_rows(items: ItemList, ctx: Any) -> ItemList:
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


def _split_csv(raw: str) -> list[str]:
    """Comma-separated list param → cleaned list (empty parts dropped)."""
    return [part.strip() for part in raw.split(",") if part.strip()]


def _split_regexes(raw: str) -> list[str]:
    """Comma-separated regex list param → cleaned list (empty parts dropped)."""
    return [part.strip() for part in raw.split(",") if part.strip()]


async def _tavily_map_rows(items: ItemList, ctx: Any) -> ItemList:
    if not items:
        return []
    env_key = ctx.param("api_key_env", str, "TAVILY_API_KEY")
    api_key = _resolve_key(env_key, ctx.param("api_key", str, ""))
    url_tmpl = ctx.param("url", str, required=True)
    instructions = ctx.param("instructions", str, "").strip()
    max_depth = int(ctx.param("max_depth", int, 1))
    max_breadth = int(ctx.param("max_breadth", int, 20))
    limit = int(ctx.param("limit", int, 25))
    allow_external = bool(ctx.param("allow_external", bool, False))
    timeout = int(ctx.param("timeout", int, 150))
    if not 1 <= max_depth <= 5:
        raise NodeError("Parameter 'max_depth' must be between 1 and 5.")
    if not 1 <= max_breadth <= 500:
        raise NodeError("Parameter 'max_breadth' must be between 1 and 500.")
    if not 1 <= limit <= 1000:
        raise NodeError("Parameter 'limit' must be between 1 and 1000.")
    if not 10 <= timeout <= 150:
        raise NodeError("Parameter 'timeout' must be between 10 and 150 seconds.")
    select_paths = _split_regexes(ctx.param("select_paths", str, ""))
    select_domains = _split_regexes(ctx.param("select_domains", str, ""))
    exclude_paths = _split_regexes(ctx.param("exclude_paths", str, ""))
    exclude_domains = _split_regexes(ctx.param("exclude_domains", str, ""))

    async def call(index: int, item: Item) -> ItemList:
        url = render(url_tmpl, item["json"]).strip()
        if not url or not url.startswith(("http://", "https://")):
            raise NodeError(f"Row {index + 1}: 'url' must be an HTTP(S) URL.")
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        body: dict[str, Any] = {
            "url": url,
            "max_depth": max_depth,
            "max_breadth": max_breadth,
            "limit": limit,
            "allow_external": allow_external,
            "timeout": timeout,
        }
        if instructions:
            body["instructions"] = render(instructions, item["json"]).strip()
        if select_paths:
            body["select_paths"] = select_paths
        if select_domains:
            body["select_domains"] = select_domains
        if exclude_paths:
            body["exclude_paths"] = exclude_paths
        if exclude_domains:
            body["exclude_domains"] = exclude_domains
        async with httpx.AsyncClient(timeout=float(timeout) + 10.0) as client:
            resp = await client.post("https://api.tavily.com/map", headers=headers, json=body)
            if resp.status_code != 200:
                raise NodeError(f"Tavily map failed: {resp.status_code} {resp.text[:500]}")
            payload = resp.json()
        results = payload.get("results", [])
        out_json = dict(item["json"])
        out_json["tavily_map_url"] = url
        out_json["tavily_map"] = results
        out_json["tavily_map_count"] = len(results)
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
            options=["auto", "lite", "deep-lite", "deep"],
            hint="auto: best default · lite: $4/1k, cost/latency · deep-lite/deep: synthesis",
        ),
        Param(
            "category",
            "select",
            "Category",
            default="",
            options=[
                "",
                "company",
                "people",
                "research paper",
                "news",
                "personal site",
                "pdf",
                "github",
                "tweet",
                "linkedin profile",
                "financial report",
            ],
            hint="Restrict results to a page type. Blank = any page.",
        ),
        Param(
            "contents",
            "select",
            "Content",
            default="highlights",
            options=["highlights", "text", "none"],
            hint=(
                "highlights: query-relevant excerpts (recommended, free) · "
                "text: full page body · none: titles/URLs only"
            ),
        ),
        Param(
            "include_domains",
            "string",
            "Only these domains",
            default="",
            hint="Comma-separated domains or path prefixes, e.g. openai.com, anthropic.com/news",
        ),
        Param(
            "exclude_domains",
            "string",
            "Exclude domains",
            default="",
            hint="Comma-separated, drops these sites from results",
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
    category = ctx.param("category", str, "")
    contents_mode = ctx.param("contents", str, "highlights")
    include_domains = _split_csv(ctx.param("include_domains", str, ""))
    exclude_domains = _split_csv(ctx.param("exclude_domains", str, ""))

    async def call(index: int, item: Item) -> ItemList:
        query = render(query_tmpl, item["json"]).strip()
        if not query:
            raise NodeError(f"Row {index + 1}: query resolved to empty.")
        headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        body: dict[str, Any] = {"query": query, "numResults": num_results, "type": search_type}
        if category:
            body["category"] = category
        if include_domains:
            body["includeDomains"] = include_domains
        if exclude_domains:
            body["excludeDomains"] = exclude_domains
        if contents_mode == "highlights":
            body["contents"] = {"highlights": True}
        elif contents_mode == "text":
            body["contents"] = {"text": True}
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post("https://api.exa.ai/search", headers=headers, json=body)
            if resp.status_code != 200:
                raise NodeError(f"Exa request failed: {resp.status_code} {resp.text[:500]}")
            payload = resp.json()
        results = payload.get("results", [])
        out_json = dict(item["json"])
        out_json["exa_query"] = query
        key = contents_mode if contents_mode in ("highlights", "text") else None
        out_json["exa_results"] = [
            {
                "title": r.get("title"),
                "url": r.get("url"),
                "published_date": r.get("publishedDate"),
                "highlights": r.get("highlights") if key == "highlights" else None,
                "text": r.get("text") if key == "text" else None,
            }
            for r in results
        ]
        return [{"json": out_json, "meta": dict(item["meta"])}]

    return await _fanout(items, ctx, call)


def _serp_rows(payload: dict[str, Any], limit: int, engine: str = "google") -> list[dict[str, Any]]:
    """Normalize SerpApi's per-engine result arrays into one shape.

    Web/news engines nest rows under organic_results / news_results; Google Play
    nests them under organic_results[*].items; Google Jobs uses jobs_results with
    company_name/location/via and apply_options links. Per-row output is always
    title / url / content / position.
    """
    if engine == "google_play":
        sections = payload.get("organic_results") or []
        rows: list[dict[str, Any]] = []
        for section in sections:
            for raw in (section or {}).get("items") or []:
                if not isinstance(raw, dict):
                    continue
                rows.append(
                    {
                        "title": raw.get("title"),
                        "url": raw.get("link"),
                        "content": raw.get("description") or raw.get("category"),
                        "position": len(rows) + 1,
                    }
                )
                if limit and len(rows) >= limit:
                    return rows
        return rows

    if engine == "google_jobs":
        container = payload.get("jobs_results") or []
        rows = []
        for index, raw in enumerate(container):
            if not isinstance(raw, dict):
                continue
            apply_options = raw.get("apply_options") or []
            url = None
            if apply_options and isinstance(apply_options[0], dict):
                url = apply_options[0].get("link")
            url = url or raw.get("share_link")
            company = raw.get("company_name") or ""
            location = raw.get("location") or ""
            via = raw.get("via") or ""
            content = " · ".join(
                part for part in (company, location, f"via {via}") if part and part != "via "
            )
            rows.append(
                {
                    "title": raw.get("title"),
                    "url": url,
                    "content": content or None,
                    "position": index + 1,
                }
            )
            if limit and len(rows) >= limit:
                break
        return rows

    for key in ("organic_results", "news_results", "results"):
        candidate = payload.get(key)
        if isinstance(candidate, list):
            container = candidate
            break
    else:
        container = []
    rows = []
    for raw in container[:limit] if limit else container:
        if not isinstance(raw, dict):
            continue
        url = raw.get("link") or raw.get("url") or raw.get("displayed_link")
        url = url or raw.get("destination")
        snippet = raw.get("snippet") or raw.get("description") or raw.get("text")
        rows.append(
            {
                "title": raw.get("title") or raw.get("name"),
                "url": url,
                "content": snippet,
                "position": raw.get("position") or raw.get("rank"),
            }
        )
    return rows


@node(
    "serpapi_search",
    "SerpApi Search",
    group="search",
    description=(
        "Search the web, news, Google Play or Google Jobs via SerpApi. "
        "Needs SERPAPI_API_KEY. Free plan: 250 searches/month (cached queries free). "
        "Adds serp_results (title, url, content) to each row."
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
        Param(
            "max_results",
            "number",
            "Max results",
            default=5,
            hint=(
                "Up to 10. Rows spend 1 search each — identical queries within "
                "the hour are served from the free cache (see Advanced)."
            ),
        ),
        Param(
            "gl",
            "string",
            "Country",
            default="",
            hint="Two-letter country code for localized results, e.g. us, gb, de. Blank = default.",
        ),
        Param(
            "hl",
            "string",
            "Language",
            default="",
            hint="Language code for results, e.g. en, es, fr. Blank = engine default.",
        ),
        Param(
            "location",
            "string",
            "Location",
            default="",
            show_if={"param": "engine", "in": ["google_jobs"]},
            hint=(
                "Jobs geolocation, e.g. 'Austin, TX'. "
                "Strongly recommended — jobs are location-dependent."
            ),
        ),
        Param(
            "no_cache",
            "boolean",
            "Always fetch fresh",
            default=False,
            hint=(
                "SerpApi caches identical queries for 1 hour — those are free "
                "and do not count against your 250 searches/month. Keep this "
                "off to stay free on repeat runs."
            ),
        ),
        Param(
            "engine",
            "select",
            "Engine",
            default="google",
            options=[
                "google",
                "google_light",
                "google_news",
                "google_play",
                "google_jobs",
                "bing",
                "bing_news",
                "duckduckgo",
                "duckduckgo_light",
                "duckduckgo_news",
                "yahoo",
                "yahoo_news",
            ],
            hint=(
                "All 12 engines emit at most Max results rows each (DuckDuckGo, "
                "Google Play and Jobs return fixed pages, sliced to that cap). "
                "Free plan: 250 searches per month."
            ),
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

    engines_with_count = {
        "google",
        "google_light",
        "google_news",
        "bing",
        "bing_news",
        "yahoo",
        "yahoo_news",
    }

    async def call(index: int, item: Item) -> ItemList:
        query = render(query_tmpl, item["json"]).strip()
        if not query:
            raise NodeError(f"Row {index + 1}: query resolved to empty.")
        params = {
            "engine": engine,
            "q": query,
            "api_key": api_key,
        }
        if ctx.param("gl", str, "").strip():
            params["gl"] = ctx.param("gl", str, "").strip().lower()
        if ctx.param("hl", str, "").strip():
            params["hl"] = ctx.param("hl", str, "").strip().lower()
        if ctx.param("location", str, "").strip() and engine == "google_jobs":
            params["location"] = ctx.param("location", str, "").strip()
        if ctx.param("no_cache", bool, False):
            params["no_cache"] = "true"
        # DuckDuckGo engines do not accept a count parameter.
        if engine in engines_with_count:
            params["num"] = max_results
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get("https://serpapi.com/search.json", params=params)
            if resp.status_code != 200:
                raise NodeError(f"SerpApi request failed: {resp.status_code} {resp.text[:500]}")
            payload = resp.json()
        out_json = dict(item["json"])
        out_json["serp_query"] = query
        out_json["serp_results"] = _serp_rows(payload, max_results, engine)
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
