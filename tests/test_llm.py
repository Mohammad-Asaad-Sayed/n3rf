import asyncio
import json

from app.contracts import new_item
from app.engine import RunContext, run_workflow
from app.nodes.ai import llm_structured
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
    result = asyncio.run(llm_structured([new_item({"company": "Acme"})], context))
    assert result[0]["json"] == {"company": "Acme", "category": "software"}
    assert len(requests) == 2
    sent_prompt = json.loads(requests[0].content)["messages"][0]["content"]
    assert "Classify Acme." in sent_prompt
    assert "Input row:\n{'company': 'Acme'}" in sent_prompt
    assert context.metrics == {"llm_calls": 2, "tokens_in": 14, "tokens_out": 6}


def test_five_fintech_rows_reach_llm_structured_prompt(monkeypatch):
    requests = install_mock_provider(
        monkeypatch,
        [{"category": "fintech"} for _ in range(5)],
    )
    rows = [{"industry": "fintech", "sample": index} for index in range(1, 6)]
    nodes = [
        {"id": "source", "type": "manual_json", "params": {"data": rows}},
        {
            "id": "llm",
            "type": "llm_structured",
            "params": {
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
