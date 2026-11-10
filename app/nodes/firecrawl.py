"""Firecrawl v2 nodes: search, scrape and map in one mode-switched node.

Three modes, one node, matching how Tavily is wired:
  mode=search  → POST https://api.firecrawl.dev/v2/search (default sources: web)
  mode=scrape  → POST https://api.firecrawl.dev/v2/scrape
  mode=map     → POST https://api.firecrawl.dev/v2/map

Auth is Bearer fc-…; key comes from FIRECRAWL_API_KEY (or a pasted key, used
for one run and never saved). Crawl / batch-scrape / agent are deliberately
not implemented.
"""

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


def _resolve_key(env_name: str, override: str) -> str:
    pasted = (override or "").strip()
    if pasted:
        return pasted
    value = os.environ.get(env_name, "") if env_name else ""
    return value


def _split_csv(raw: str) -> list[str]:
    """Comma-separated list param → cleaned list (empty parts dropped)."""
    return [part.strip() for part in raw.split(",") if part.strip()]


async def _fanout(items: ItemList, ctx: Any, callback: Any) -> ItemList:
    concurrency = ctx.param("concurrency", int, 4)
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


@node(
    "firecrawl",
    "Firecrawl",
    group="search",
    description=(
        "Search the web, scrape one URL, or map a whole site — pick a mode. "
        "Map needs FIRECRAWL_API_KEY; search and scrape also work keyless. "
        "Adds firecrawl_results (search), "
        "firecrawl_content (scrape), or firecrawl_map + firecrawl_map_count (map) "
        "to each row. Crawl is deliberately not implemented."
    ),
    params=[
        Param(
            "mode",
            "select",
            "Mode",
            default="search",
            options=["search", "scrape", "map"],
            hint=(
                "search: find pages for each row · scrape: read one URL · map: list a site's URLs"
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
            show_if={"param": "mode", "in": ["scrape", "map"]},
            hint=(
                "Runs once per row. @ picks a field. Scrape/map usually mean a row "
                "field ({{website}}); map also accepts a fixed root such as "
                "https://example.com"
            ),
        ),
        Param(
            "limit",
            "number",
            "Result limit",
            default=10,
            hint=(
                "Max results per row. Search: 1–100. Map: 1–100000 (default 5000 "
                "on the API; this node keeps it at 10 to avoid surprise credit "
                "burn)."
            ),
        ),
        Param(
            "country",
            "string",
            "Country",
            default="US",
            show_if={"param": "mode", "in": ["search"]},
            hint="ISO country code for geo-targeted results, e.g. US, DE, JP.",
        ),
        Param(
            "include_domains",
            "string",
            "Only these domains",
            default="",
            show_if={"param": "mode", "in": ["search"]},
            hint="Hostnames only, comma-separated, e.g. docs.firecrawl.dev, github.com",
        ),
        Param(
            "exclude_domains",
            "string",
            "Exclude domains",
            default="",
            show_if={"param": "mode", "in": ["search"]},
            hint="Hostnames only, comma-separated. Cannot be combined with include.",
        ),
        Param(
            "time_range",
            "select",
            "Time range",
            default="",
            options=["", "h", "d", "w", "m", "y"],
            show_if={"param": "mode", "in": ["search"]},
            hint="Only return results from this period back. Blank = any time.",
        ),
        Param(
            "mobile",
            "boolean",
            "Emulate mobile",
            default=False,
            show_if={"param": "mode", "in": ["scrape"]},
            hint="Scrape as a mobile device — useful for responsive pages.",
        ),
        Param(
            "scrape_markdown",
            "boolean",
            "Scrape results too",
            default=False,
            show_if={"param": "mode", "in": ["search"]},
            hint=(
                "Fetch the full markdown of every result page (scrapeOptions). "
                "Costs more credits — off by default."
            ),
        ),
        Param(
            "format",
            "select",
            "Format",
            default="markdown",
            options=["markdown", "html", "rawHtml"],
            show_if={"param": "mode", "in": ["scrape"]},
            hint="markdown is clean text; html is cleaned; rawHtml is the exact response.",
        ),
        Param(
            "only_main_content",
            "boolean",
            "Main content only",
            default=True,
            show_if={"param": "mode", "in": ["scrape"]},
            hint="Drop navs, headers and footers before reading the page.",
        ),
        Param(
            "search_query",
            "string",
            "Order by relevance to",
            default="",
            expression=True,
            show_if={"param": "mode", "in": ["map"]},
            hint="Optional. Discovery URLs are ordered by relevance to this query.",
        ),
        Param(
            "sitemap",
            "select",
            "Sitemap",
            default="include",
            options=["include", "skip", "only"],
            show_if={"param": "mode", "in": ["map"]},
            hint="include: sitemap + discovery · skip: discovery only · only: sitemap URLs only.",
        ),
        Param(
            "include_subdomains",
            "boolean",
            "Include subdomains",
            default=True,
            show_if={"param": "mode", "in": ["map"]},
            hint="Include blog.example.com when mapping example.com.",
        ),
        Param(
            "ignore_query_parameters",
            "boolean",
            "Ignore query parameters",
            default=True,
            show_if={"param": "mode", "in": ["map"]},
            hint="Drop URLs that carry query strings.",
        ),
        Param(
            "timeout",
            "number",
            "Timeout (ms)",
            default=60000,
            hint="Firecrawl timeout in milliseconds (1000–300000).",
        ),
        Param(
            "api_key_env",
            "string",
            "API key environment variable",
            default="FIRECRAWL_API_KEY",
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
async def firecrawl(items: ItemList, ctx: Any) -> ItemList:
    mode = ctx.param("mode", str, "search")
    if mode == "search":
        return await _firecrawl_search_rows(items, ctx)
    if mode == "scrape":
        return await _firecrawl_scrape_rows(items, ctx)
    if mode == "map":
        return await _firecrawl_map_rows(items, ctx)
    raise NodeError(f"Parameter 'mode' must be one of: search, scrape, map — got '{mode}'.")


def _validate_limit(limit: int, maximum: int) -> None:
    if not 1 <= limit <= maximum:
        raise NodeError(f"Parameter 'limit' must be between 1 and {maximum}.")


def _headers(api_key: str) -> dict[str, str]:
    # Firecrawl supports keyless calls for search and scrape (with tight
    # limits). When no key is configured we send no Authorization header at
    # all — a header with an empty token returns 401.
    base = {"Content-Type": "application/json"}
    if api_key:
        base["Authorization"] = f"Bearer {api_key}"
    return base


async def _firecrawl_search_rows(items: ItemList, ctx: Any) -> ItemList:
    if not items:
        return []
    env_key = ctx.param("api_key_env", str, "FIRECRAWL_API_KEY")
    api_key = _resolve_key(env_key, ctx.param("api_key", str, ""))
    query_tmpl = ctx.param("query", str, required=True)
    limit = int(ctx.param("limit", int, 10))
    _validate_limit(limit, 100)
    country = ctx.param("country", str, "US").strip() or "US"
    include = _split_csv(ctx.param("include_domains", str, ""))
    exclude = _split_csv(ctx.param("exclude_domains", str, ""))
    if include and exclude:
        raise NodeError("'include_domains' and 'exclude_domains' cannot be combined.")
    time_range = ctx.param("time_range", str, "")
    scrape_markdown = bool(ctx.param("scrape_markdown", bool, False))
    timeout = int(ctx.param("timeout", int, 60000))
    if not 1000 <= timeout <= 300000:
        raise NodeError("Parameter 'timeout' must be between 1000 and 300000 ms.")

    async def call(index: int, item: Item) -> ItemList:
        query = render(query_tmpl, item["json"]).strip()
        if not query:
            raise NodeError(f"Row {index + 1}: query resolved to empty.")
        if len(query) > 500:
            raise NodeError(f"Row {index + 1}: query is longer than 500 characters.")
        body: dict[str, Any] = {
            "query": query,
            "limit": limit,
            "country": country,
            "timeout": timeout,
        }
        if include:
            body["includeDomains"] = include
        if exclude:
            body["excludeDomains"] = exclude
        if time_range:
            body["tbs"] = f"qdr:{time_range}"
        if scrape_markdown:
            body["scrapeOptions"] = {"formats": [{"type": "markdown"}]}
        async with httpx.AsyncClient(timeout=float(timeout) / 1000.0 + 10.0) as client:
            resp = await client.post(
                "https://api.firecrawl.dev/v2/search", headers=_headers(api_key), json=body
            )
            if resp.status_code != 200:
                raise NodeError(
                    f"Firecrawl search failed: {resp.status_code} {resp.text[:500]}"
                    + (
                        " — keyless search works with tight limits; "
                        "for higher quotas, set FIRECRAWL_API_KEY or paste one for this run."
                        if not api_key
                        else ""
                    )
                )
            payload = resp.json()
        results = (payload.get("data") or {}).get("web", [])
        out_json = dict(item["json"])
        out_json["firecrawl_query"] = query
        out_json["firecrawl_results"] = [
            {
                "title": r.get("title"),
                "url": r.get("url"),
                "description": r.get("description"),
                **({"markdown": r.get("markdown")} if scrape_markdown else {}),
            }
            for r in results
        ]
        if "creditsUsed" in payload:
            out_json["firecrawl_credits_used"] = payload["creditsUsed"]
        return [{"json": out_json, "meta": dict(item["meta"])}]

    return await _fanout(items, ctx, call)


async def _firecrawl_scrape_rows(items: ItemList, ctx: Any) -> ItemList:
    if not items:
        return []
    env_key = ctx.param("api_key_env", str, "FIRECRAWL_API_KEY")
    api_key = _resolve_key(env_key, ctx.param("api_key", str, ""))
    url_tmpl = ctx.param("url", str, required=True)
    fmt = ctx.param("format", str, "markdown")
    only_main = bool(ctx.param("only_main_content", bool, True))
    timeout = int(ctx.param("timeout", int, 60000))
    if not 1000 <= timeout <= 300000:
        raise NodeError("Parameter 'timeout' must be between 1000 and 300000 ms.")

    async def call(index: int, item: Item) -> ItemList:
        url = render(url_tmpl, item["json"]).strip()
        if not url or not url.startswith(("http://", "https://")):
            raise NodeError(f"Row {index + 1}: 'url' must be an HTTP(S) URL.")
        body = {
            "url": url,
            "formats": [fmt],
            "onlyMainContent": only_main,
            "timeout": timeout,
            "mobile": bool(ctx.param("mobile", bool, False)),
        }
        async with httpx.AsyncClient(timeout=float(timeout) / 1000.0 + 10.0) as client:
            resp = await client.post(
                "https://api.firecrawl.dev/v2/scrape", headers=_headers(api_key), json=body
            )
            if resp.status_code != 200:
                raise NodeError(
                    f"Firecrawl scrape failed: {resp.status_code} {resp.text[:500]}"
                    + (
                        " — keyless scrape works with tight limits; "
                        "for higher quotas, set FIRECRAWL_API_KEY or paste one for this run."
                        if not api_key
                        else ""
                    )
                )
            payload = resp.json()
        data = payload.get("data") or {}
        content = data.get("markdown") or data.get("html") or data.get("rawHtml") or ""
        out_json = dict(item["json"])
        out_json["firecrawl_url"] = url
        out_json["firecrawl_content"] = content
        metadata = data.get("metadata") or {}
        if metadata.get("title"):
            title = metadata["title"]
            out_json["firecrawl_title"] = " ".join(title) if isinstance(title, list) else title
        if "creditsUsed" in payload:
            out_json["firecrawl_credits_used"] = payload["creditsUsed"]
        return [{"json": out_json, "meta": dict(item["meta"])}]

    return await _fanout(items, ctx, call)


async def _firecrawl_map_rows(items: ItemList, ctx: Any) -> ItemList:
    if not items:
        return []
    env_key = ctx.param("api_key_env", str, "FIRECRAWL_API_KEY")
    api_key = _resolve_key(env_key, ctx.param("api_key", str, ""))
    url_tmpl = ctx.param("url", str, required=True)
    limit = int(ctx.param("limit", int, 10))
    _validate_limit(limit, 100000)
    search_query = ctx.param("search_query", str, "").strip()
    sitemap = ctx.param("sitemap", str, "include")
    include_subdomains = bool(ctx.param("include_subdomains", bool, True))
    ignore_query = bool(ctx.param("ignore_query_parameters", bool, True))
    timeout = int(ctx.param("timeout", int, 60000))
    if not 1000 <= timeout <= 300000:
        raise NodeError("Parameter 'timeout' must be between 1000 and 300000 ms.")

    async def call(index: int, item: Item) -> ItemList:
        url = render(url_tmpl, item["json"]).strip()
        if not url or not url.startswith(("http://", "https://")):
            raise NodeError(f"Row {index + 1}: 'url' must be an HTTP(S) URL.")
        body: dict[str, Any] = {
            "url": url,
            "limit": limit,
            "sitemap": sitemap,
            "includeSubdomains": include_subdomains,
            "ignoreQueryParameters": ignore_query,
            "timeout": timeout,
        }
        if search_query:
            body["search"] = render(search_query, item["json"]).strip()
        async with httpx.AsyncClient(timeout=float(timeout) / 1000.0 + 10.0) as client:
            resp = await client.post(
                "https://api.firecrawl.dev/v2/map", headers=_headers(api_key), json=body
            )
            if resp.status_code != 200:
                raise NodeError(
                    f"Firecrawl map failed: {resp.status_code} {resp.text[:500]}"
                    + (
                        " — map requires a key: set FIRECRAWL_API_KEY or paste one for this run."
                        if not api_key
                        else ""
                    )
                )
            payload = resp.json()
        links = payload.get("links", [])
        out_json = dict(item["json"])
        out_json["firecrawl_map_url"] = url
        out_json["firecrawl_map"] = [
            {
                "url": link.get("url"),
                "title": link.get("title"),
                "description": link.get("description"),
            }
            for link in links
        ]
        out_json["firecrawl_map_count"] = len(links)
        if "creditsUsed" in payload:
            out_json["firecrawl_credits_used"] = payload["creditsUsed"]
        return [{"json": out_json, "meta": dict(item["meta"])}]

    return await _fanout(items, ctx, call)
