import asyncio
import json

import pytest

from app.contracts import new_item
from app.engine import RunContext, migrate_nodes, run_workflow
from app.errors import NodeError
from app.nodes.ai import _fanout, ask_ai
from tests.mock_provider import install_mock_provider


def test_structured_response_repair_and_usage(monkeypatch):
    requests = install_mock_provider(
        monkeypatch,
        [{"extra": "invalid"}, {"category": "software"}],
    )
    schema = {
        "type": "object",
        "properties": {"category": {"type": "string"}},
        "required": ["category"],
        "additionalProperties": False,
    }
    context = RunContext(
        {
            "provider": "custom",
            "base_url": "https://provider.invalid/v1",
            "api_key_env": "",
            "model": "test-model",
            "prompt": "Classify {{ $json.company }}.",
            "schema": schema,
            "concurrency": 1,
            "max_output_rows": 10,
            "on_error": "fail",
            "mode": "per_input",
        }
    )
    result = asyncio.run(ask_ai([new_item({"company": "Acme"})], context))
    assert result[0]["json"] == {"company": "Acme", "category": "software"}
    assert len(requests) == 2
    sent_prompt = json.loads(requests[0].content)["messages"][0]["content"]
    assert "Classify Acme." in sent_prompt
    assert "Input row:\n{'company': 'Acme'}" in sent_prompt
    assert context.metrics == {"llm_calls": 2, "tokens_in": 14, "tokens_out": 6}


def test_five_fintech_rows_reach_ask_ai_prompt(monkeypatch):
    requests = install_mock_provider(
        monkeypatch,
        [{"category": "fintech"} for _ in range(5)],
    )
    rows = [{"industry": "fintech", "sample": index} for index in range(1, 6)]
    nodes = [
        {"id": "source", "type": "manual_json", "params": {"data": rows}},
        {
            "id": "llm",
            "type": "ask_ai",
            "params": {
                "provider": "custom",
                "base_url": "https://provider.invalid/v1",
                "api_key_env": "",
                "model": "test-model",
                "prompt": (
                    "Describe the {{ $json.industry }} industry for sample {{ $json.sample }}."
                ),
                "schema": {
                    "type": "object",
                    "properties": {"category": {"type": "string"}},
                    "required": ["category"],
                    "additionalProperties": False,
                },
                "concurrency": 1,
                "max_output_rows": 5,
                "on_error": "fail",
                "mode": "per_input",
            },
        },
    ]
    result = asyncio.run(run_workflow(nodes, [{"source": "source", "target": "llm"}]))

    assert result["status"] == "success"
    assert len(requests) == 5
    assert result["nodes"][1]["rows_in"] == 5
    assert result["nodes"][1]["rows_out"] == 5
    prompts = [json.loads(request.content)["messages"][0]["content"] for request in requests]
    for index, prompt in enumerate(prompts, start=1):
        assert f"Describe the fintech industry for sample {index}." in prompt
        assert f"'industry': 'fintech', 'sample': {index}" in prompt
    assert result["output"] == [{**row, "category": "fintech"} for row in rows]


def test_legacy_llm_node_migrates_to_ask_ai():
    nodes = [
        {
            "id": "old",
            "type": "groq_llm",
            "params": {"model": "gpt-oss-120b", "prompt": "hi"},
        },
        {"id": "gen", "type": "llm_structured", "params": {"model": "gpt-4o-mini"}},
    ]
    migrated = migrate_nodes(nodes)
    assert migrated[0]["type"] == "ask_ai"
    assert migrated[0]["params"]["provider"] == "groq"
    assert migrated[1]["type"] == "ask_ai"
    assert migrated[1]["params"]["provider"] == "custom"


def test_pasted_key_works_without_env(monkeypatch):
    requests = install_mock_provider(monkeypatch, [{"category": "software"}])
    monkeypatch.delenv("MISSING_PASTE_TEST_KEY", raising=False)
    context = RunContext(
        {
            "provider": "custom",
            "base_url": "https://provider.invalid/v1",
            "api_key_env": "MISSING_PASTE_TEST_KEY",
            "api_key": "paste-secret-123",
            "model": "test-model",
            "prompt": "Classify {{ $json.company }}.",
            "schema": {},
            "concurrency": 1,
            "max_output_rows": 10,
            "on_error": "fail",
            "mode": "per_input",
        }
    )
    result = asyncio.run(ask_ai([new_item({"company": "Acme"})], context))
    assert result[0]["json"]["category"] == "software"
    assert requests[0].headers.get("authorization") == "Bearer paste-secret-123"


def test_pasted_key_overrides_env_var(monkeypatch):
    monkeypatch.setenv("TEST_OVERRIDE_ENV", "env-secret")
    requests = install_mock_provider(monkeypatch, [{"category": "software"}])
    context = RunContext(
        {
            "provider": "custom",
            "base_url": "https://provider.invalid/v1",
            "api_key_env": "TEST_OVERRIDE_ENV",
            "api_key": "paste-wins",
            "model": "test-model",
            "prompt": "Classify {{ $json.company }}.",
            "schema": {},
            "concurrency": 1,
            "max_output_rows": 10,
            "on_error": "fail",
            "mode": "per_input",
        }
    )
    result = asyncio.run(ask_ai([new_item({"company": "Acme"})], context))
    assert result[0]["json"]["category"] == "software"
    assert requests[0].headers.get("authorization") == "Bearer paste-wins"


_STRICT_SCHEMA = {
    "type": "object",
    "properties": {"category": {"type": "string"}},
    "required": ["category"],
    "additionalProperties": False,
}


def _ask_context(monkeypatch, policy):
    """Always-invalid replies: first try and repair both fail schema."""
    install_mock_provider(monkeypatch, [{"extra": 1}, {"extra": 2}])
    return RunContext(
        {
            "provider": "custom",
            "base_url": "https://provider.invalid/v1",
            "api_key_env": "",
            "model": "test-model",
            "prompt": "Classify {{ $json.company }}.",
            "schema": _STRICT_SCHEMA,
            "concurrency": 1,
            "max_output_rows": 10,
            "on_error": policy,
            "mode": "per_input",
        }
    )


def test_second_schema_failure_applies_error_policy_fail(monkeypatch):
    context = _ask_context(monkeypatch, "fail")
    with pytest.raises(NodeError, match="Row 1"):
        asyncio.run(ask_ai([new_item({"company": "Acme"})], context))


def test_second_schema_failure_applies_error_policy_skip(monkeypatch):
    context = _ask_context(monkeypatch, "skip")
    out = asyncio.run(ask_ai([new_item({"company": "Acme"})], context))
    assert out == []


def test_second_schema_failure_applies_error_policy_error_item(monkeypatch):
    context = _ask_context(monkeypatch, "error_item")
    out = asyncio.run(ask_ai([new_item({"company": "Acme"})], context))
    assert len(out) == 1
    assert out[0]["json"] == {"company": "Acme"}
    assert "error" in out[0]["meta"]


def test_concurrency_cap_observed():
    current = 0
    peak = 0

    async def callback(index, item):
        nonlocal current, peak
        current += 1
        peak = max(peak, current)
        await asyncio.sleep(0.05)
        current -= 1
        return [item]

    ctx = RunContext({"concurrency": 2, "max_output_rows": 10, "on_error": "fail"})
    rows = [new_item({"i": i}) for i in range(6)]

    async def main():
        return await _fanout(rows, ctx, callback)

    out = asyncio.run(main())
    assert len(out) == 6
    assert peak == 2  # parallel ( >1 ) but capped at 2


def test_tokens_accumulate_across_rows(monkeypatch):
    install_mock_provider(monkeypatch, [{"category": "a"}, {"category": "b"}])
    ctx = RunContext(
        {
            "provider": "custom",
            "base_url": "https://provider.invalid/v1",
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
    asyncio.run(ask_ai([new_item({"company": "A"}), new_item({"company": "B"})], ctx))
    assert ctx.metrics["llm_calls"] == 2
    assert ctx.metrics["tokens_in"] == 14
    assert ctx.metrics["tokens_out"] == 6
