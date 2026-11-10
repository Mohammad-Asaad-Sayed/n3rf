import asyncio
import json

import httpx
import pytest

from app.contracts import new_item
from app.engine import RunContext
from app.errors import NodeError
from app.nodes.enrichment import _fanout, jina_reader, serpapi_search, tavily
from tests.mock_provider import install_mock_provider


def _install_httpx(monkeypatch, handler):
    original = httpx.AsyncClient

    def mocked_client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return original(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", mocked_client)


def test_error_item_policy_logs_row_failure():
    context = RunContext({"concurrency": 1})

    async def fail(_index, _item):
        raise NodeError("provider unavailable")

    output = asyncio.run(_fanout([new_item({"company": "Acme"})], context, fail))

    assert output[0]["json"] == {"company": "Acme"}
    assert "error" in output[0]["meta"]
    assert context.logs == ["Row 1: provider unavailable"]


def test_tavily_search_happy_and_empty(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        body = json.loads(request.content)
        assert body["query"] == "Acme funding"
        return httpx.Response(
            200,
            json={
                "results": [
                    {"title": "Acme raised", "url": "https://example.com/a", "content": "…"},
                ],
                "answer": None,
            },
        )

    _install_httpx(monkeypatch, handler)
    ctx = RunContext(
        {
            "mode": "search",
            "api_key_env": "TAVILY_API_KEY",
            "query": "{{ $json.company }} funding",
            "max_results": 2,
            "search_depth": "basic",
            "include_answer": False,
            "concurrency": 1,
            "max_output_rows": 10,
            "on_error": "fail",
        }
    )
    out = asyncio.run(tavily([new_item({"company": "Acme"})], ctx))
    assert out[0]["json"]["tavily_results"][0]["title"] == "Acme raised"
    assert asyncio.run(tavily([], ctx)) == []
    assert len(seen) == 1


def test_tavily_search_bad_param(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    ctx = RunContext(
        {
            "mode": "search",
            "api_key_env": "TAVILY_API_KEY",
            "query": "x",
            "max_results": 99,
            "search_depth": "basic",
            "include_answer": False,
            "concurrency": 1,
            "max_output_rows": 10,
            "on_error": "fail",
        }
    )
    with pytest.raises(NodeError):
        asyncio.run(tavily([new_item({})], ctx))


def test_serpapi_search_happy_and_empty(monkeypatch):
    monkeypatch.setenv("SERPAPI_API_KEY", "test-key")
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        assert request.url.params["q"] == "Acme funding"
        assert request.url.params["engine"] == "google"
        return httpx.Response(
            200,
            json={
                "organic_results": [
                    {"title": "Acme raised", "link": "https://example.com/a", "snippet": "…"},
                ],
            },
        )

    _install_httpx(monkeypatch, handler)
    ctx = RunContext(
        {
            "api_key_env": "SERPAPI_API_KEY",
            "query": "{{ $json.company }} funding",
            "max_results": 2,
            "engine": "google",
            "concurrency": 1,
            "max_output_rows": 10,
            "on_error": "fail",
        }
    )
    out = asyncio.run(serpapi_search([new_item({"company": "Acme"})], ctx))
    assert out[0]["json"]["serp_results"][0]["title"] == "Acme raised"
    assert out[0]["json"]["serp_query"] == "Acme funding"
    assert asyncio.run(serpapi_search([], ctx)) == []
    assert len(seen) == 1


def test_serpapi_search_bad_param(monkeypatch):
    monkeypatch.setenv("SERPAPI_API_KEY", "test-key")
    ctx = RunContext(
        {
            "api_key_env": "SERPAPI_API_KEY",
            "query": "x",
            "max_results": 99,
            "engine": "google",
            "concurrency": 1,
            "max_output_rows": 10,
            "on_error": "fail",
        }
    )
    with pytest.raises(NodeError):
        asyncio.run(serpapi_search([new_item({})], ctx))


def test_jina_reader_anonymous(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url).startswith("https://r.jina.ai/https://example.com")
        assert "Authorization" not in request.headers
        return httpx.Response(200, text="# Title\nbody")

    _install_httpx(monkeypatch, handler)
    ctx = RunContext(
        {
            "url": "{{ $json.website }}",
            "api_key_env": "",
            "format": "markdown",
            "concurrency": 1,
            "max_output_rows": 10,
            "on_error": "fail",
        }
    )
    out = asyncio.run(jina_reader([new_item({"website": "https://example.com"})], ctx))
    assert "# Title" in out[0]["json"]["jina_content"]
    assert asyncio.run(jina_reader([], ctx)) == []


def test_ask_ai_groq_provider(monkeypatch):
    from app.nodes.ai import ask_ai

    requests = install_mock_provider(monkeypatch, [{"category": "software"}])
    ctx = RunContext(
        {
            "provider": "groq",
            "api_key_env": "",
            "model": "test-model",
            "prompt": "Classify {{ $json.company }}.",
            "schema": {},
            "concurrency": 1,
            "max_output_rows": 10,
            "on_error": "fail",
            "mode": "per_input",
        }
    )
    out = asyncio.run(ask_ai([new_item({"company": "Acme"})], ctx))
    assert out[0]["json"]["category"] == "software"
    assert len(requests) == 1


def test_tavily_search_pasted_key_without_env(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            200,
            json={"results": [{"title": "Acme raised", "url": "https://example.com/a"}]},
        )

    _install_httpx(monkeypatch, handler)
    ctx = RunContext(
        {
            "mode": "search",
            "api_key_env": "TAVILY_API_KEY",
            "api_key": "paste-tavily-secret",
            "query": "{{ $json.company }} funding",
            "max_results": 2,
            "search_depth": "basic",
            "include_answer": False,
            "concurrency": 1,
            "max_output_rows": 10,
            "on_error": "fail",
        }
    )
    out = asyncio.run(tavily([new_item({"company": "Acme"})], ctx))
    assert out[0]["json"]["tavily_results"][0]["title"] == "Acme raised"
    assert seen[0].headers.get("authorization") == "Bearer paste-tavily-secret"


def test_firecrawl_search_happy_and_empty(monkeypatch):
    from app.nodes.firecrawl import firecrawl

    monkeypatch.setenv("FIRECRAWL_API_KEY", "fc-test")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v2/search"
        body = json.loads(request.content)
        assert body["query"] == "Acme funding"
        assert body["limit"] == 3
        return httpx.Response(
            200,
            json={
                "success": True,
                "data": {
                    "web": [
                        {
                            "title": "Acme raised",
                            "url": "https://example.com/a",
                            "description": "…",
                        },
                    ]
                },
                "creditsUsed": 1,
            },
        )

    _install_httpx(monkeypatch, handler)
    ctx = RunContext(
        {
            "mode": "search",
            "api_key_env": "FIRECRAWL_API_KEY",
            "query": "{{company}} funding",
            "limit": 3,
            "country": "US",
            "include_domains": "",
            "exclude_domains": "",
            "scrape_markdown": False,
            "timeout": 60000,
            "concurrency": 1,
            "max_output_rows": 10,
            "on_error": "fail",
        }
    )
    out = asyncio.run(firecrawl([new_item({"company": "Acme"})], ctx))
    assert out[0]["json"]["firecrawl_results"][0]["title"] == "Acme raised"
    assert asyncio.run(firecrawl([], ctx)) == []


def test_firecrawl_scrape_happy_path(monkeypatch):
    from app.nodes.firecrawl import firecrawl

    monkeypatch.setenv("FIRECRAWL_API_KEY", "fc-test")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v2/scrape"
        body = json.loads(request.content)
        assert body["url"] == "https://example.com"
        assert body["formats"] == ["markdown"]
        return httpx.Response(
            200,
            json={
                "success": True,
                "data": {
                    "markdown": "# Example",
                    "metadata": {"title": "Example Domain"},
                },
                "creditsUsed": 1,
            },
        )

    _install_httpx(monkeypatch, handler)
    ctx = RunContext(
        {
            "mode": "scrape",
            "api_key_env": "FIRECRAWL_API_KEY",
            "url": "{{website}}",
            "format": "markdown",
            "only_main_content": True,
            "timeout": 60000,
            "concurrency": 1,
            "max_output_rows": 10,
            "on_error": "fail",
        }
    )
    out = asyncio.run(firecrawl([new_item({"website": "https://example.com"})], ctx))
    assert out[0]["json"]["firecrawl_content"] == "# Example"
    assert out[0]["json"]["firecrawl_title"] == "Example Domain"


def test_firecrawl_map_happy_path(monkeypatch):
    from app.nodes.firecrawl import firecrawl

    monkeypatch.setenv("FIRECRAWL_API_KEY", "fc-test")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v2/map"
        return httpx.Response(
            200,
            json={
                "success": True,
                "links": [
                    {"url": "https://example.com/", "title": "Home", "description": "…"},
                    {"url": "https://example.com/about"},
                ],
            },
        )

    _install_httpx(monkeypatch, handler)
    ctx = RunContext(
        {
            "mode": "map",
            "api_key_env": "FIRECRAWL_API_KEY",
            "url": "{{website}}",
            "limit": 10,
            "search_query": "",
            "sitemap": "include",
            "include_subdomains": True,
            "ignore_query_parameters": True,
            "timeout": 60000,
            "concurrency": 1,
            "max_output_rows": 10,
            "on_error": "fail",
        }
    )
    out = asyncio.run(firecrawl([new_item({"website": "https://example.com"})], ctx))
    assert out[0]["json"]["firecrawl_map_count"] == 2
    assert out[0]["json"]["firecrawl_map"][0]["url"] == "https://example.com/"


def test_firecrawl_bad_param(monkeypatch):
    from app.nodes.firecrawl import firecrawl

    monkeypatch.setenv("FIRECRAWL_API_KEY", "fc-test")
    with pytest.raises(NodeError):
        asyncio.run(
            firecrawl(
                [new_item({"website": "https://example.com"})],
                RunContext(
                    {
                        "mode": "search",
                        "api_key_env": "FIRECRAWL_API_KEY",
                        "query": "x",
                        "limit": 101,
                        "timeout": 60000,
                        "concurrency": 1,
                        "max_output_rows": 10,
                        "on_error": "fail",
                    }
                ),
            )
        )


def test_serpapi_news_results_fallback(monkeypatch):
    from app.nodes.enrichment import _serp_rows

    payload = {
        "news_results": [
            {"title": "Big funding", "link": "https://example.com/news/1", "snippet": "…"},
        ]
    }
    rows = _serp_rows(payload, 5)
    assert rows[0]["title"] == "Big funding"
    assert rows[0]["url"] == "https://example.com/news/1"
    assert rows[0]["content"] == "…"


def test_serpapi_play_and_jobs_shapes():
    from app.nodes.enrichment import _serp_rows

    play_payload = {
        "organic_results": [
            {
                "items": [
                    {
                        "title": "Extreme Car Driving Simulator",
                        "link": "https://play.google.com/store/apps/details?id=com.aim.racing",
                        "description": "Racing sim.",
                        "rating": 4.3,
                    }
                ]
            }
        ]
    }
    rows = _serp_rows(play_payload, 5, "google_play")
    assert rows[0]["title"] == "Extreme Car Driving Simulator"
    assert rows[0]["url"].startswith("https://play.google.com")

    jobs_payload = {
        "jobs_results": [
            {
                "title": "Barista",
                "company_name": "Starbucks",
                "location": "Austin, TX",
                "via": "Indeed",
                "apply_options": [{"title": "Indeed", "link": "https://indeed.com/viewjob?jk=1"}],
            }
        ]
    }
    rows = _serp_rows(jobs_payload, 5, "google_jobs")
    assert rows[0]["title"] == "Barista"
    assert rows[0]["url"] == "https://indeed.com/viewjob?jk=1"
    assert "Starbucks" in rows[0]["content"]
