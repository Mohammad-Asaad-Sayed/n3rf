import asyncio
import json

import httpx
import pytest

from app.contracts import new_item
from app.engine import RunContext
from app.errors import NodeError
from app.nodes.enrichment import jina_reader, serpapi_search, tavily_search
from tests.mock_provider import install_mock_provider


def _install_httpx(monkeypatch, handler):
    original = httpx.AsyncClient

    def mocked_client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return original(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", mocked_client)


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
    out = asyncio.run(tavily_search([new_item({"company": "Acme"})], ctx))
    assert out[0]["json"]["tavily_results"][0]["title"] == "Acme raised"
    assert asyncio.run(tavily_search([], ctx)) == []
    assert len(seen) == 1


def test_tavily_search_bad_param(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    ctx = RunContext(
        {
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
        asyncio.run(tavily_search([new_item({})], ctx))


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
    out = asyncio.run(tavily_search([new_item({"company": "Acme"})], ctx))
    assert out[0]["json"]["tavily_results"][0]["title"] == "Acme raised"
    assert seen[0].headers.get("authorization") == "Bearer paste-tavily-secret"
