import asyncio

import pytest

from app.engine import run_workflow, topological_order
from app.errors import NodeError
from app.expressions import ExpressionError, evaluate, render
from app.params import Param, resolve_show_if, validate_params
from app.registry import NodeSpec, load_all


def test_param_coercion_and_conditional_visibility():
    specs = [
        Param("mode", "select", "Mode", default="off", options=["off", "on"]),
        Param(
            "limit",
            "number",
            "Limit",
            default=10,
            show_if={"param": "mode", "in": ["on"]},
        ),
    ]
    assert validate_params(specs, {"mode": "on", "limit": "5"}) == {
        "mode": "on",
        "limit": 5,
    }
    assert resolve_show_if(specs, {"mode": "off"}) == {"mode"}
    with pytest.raises(NodeError, match="mode"):
        validate_params(specs, {"mode": "invalid"})


def test_expression_support_is_declared_in_public_param_metadata():
    catalog = {spec.id: spec.public() for spec in load_all().values()}
    filter_condition = next(
        param for param in catalog["filter"]["params"] if param["key"] == "condition"
    )
    set_fields = next(
        param for param in catalog["set_fields"]["params"] if param["key"] == "fields"
    )
    set_fields_value = next(column for column in set_fields["columns"] if column["key"] == "value")
    sort_field = next(param for param in catalog["sort"]["params"] if param["key"] == "field")
    llm_prompt = next(param for param in catalog["ask_ai"]["params"] if param["key"] == "prompt")
    ai_filter_criterion = next(
        param for param in catalog["ai_filter"]["params"] if param["key"] == "criterion"
    )
    http_url = next(param for param in catalog["http_request"]["params"] if param["key"] == "url")

    assert filter_condition["expression"] is True
    assert set_fields_value["expression"] is True
    assert llm_prompt["expression"] is True
    assert ai_filter_criterion["expression"] is True
    assert http_url["expression"] is True
    assert sort_field["expression"] is False


def test_expression_templates_and_security():
    assert evaluate("$json.score >= 4", {"score": 5})
    assert evaluate("score >= 4", {"score": 5})
    assert render("Company {{ $json.name }}", {"name": "Acme"}) == "Company Acme"
    assert render("Company {{name}}", {"name": "Acme"}) == "Company Acme"
    assert evaluate("company", {"company": "Acme"}) == "Acme"
    assert evaluate("user.name", {"user": {"name": "Ada"}}) == "Ada"
    assert evaluate("len(tags)", {"tags": [1, 2, 3]}) == 3
    # Spaced headers: both exact and snake_case resolve.
    assert evaluate("Company Name", {"Company Name": "Acme"}) == "Acme"
    assert evaluate("company_name", {"Company Name": "Acme"}) == "Acme"
    assert render("Hi {{Company Name}}", {"Company Name": "Acme"}) == "Hi Acme"
    assert evaluate("company_name >= 5", {"Company Name": 10}) is True
    for expression in (
        "__import__('os')",
        "$json.__class__",
        "$json['__class__']",
        "(lambda: 1)()",
        "[x for x in [1]]",
        "json.items()",
    ):
        with pytest.raises(ExpressionError):
            evaluate(expression, {"name": "row"})


def test_graph_cycle_identifies_nodes():
    nodes = [{"id": "a"}, {"id": "b"}]
    with pytest.raises(NodeError, match="a, b|b, a"):
        topological_order(nodes, [{"source": "a", "target": "b"}, {"source": "b", "target": "a"}])


def test_demo_pipeline_executes_batch_and_keeps_meta_separate():
    nodes = [
        {
            "id": "source",
            "type": "manual_json",
            "params": {"data": [{"score": 3}, {"score": 8}, {"score": 5}]},
        },
        {"id": "filter", "type": "filter", "params": {"condition": "$json.score >= 5"}},
        {
            "id": "sort",
            "type": "sort",
            "params": {"field": "score", "numeric": True, "direction": "desc"},
        },
        {"id": "limit", "type": "limit", "params": {"max": 1, "offset": 0}},
    ]
    edges = [
        {"source": a, "target": b}
        for a, b in zip(
            ("source", "filter", "sort"),
            ("filter", "sort", "limit"),
            strict=True,
        )
    ]
    result = asyncio.run(run_workflow(nodes, edges))
    assert result["status"] == "success"
    assert result["output"] == [{"score": 8}]
    assert result["nodes"][1]["rows_in"] == 3
    assert result["nodes"][1]["rows_out"] == 2
    assert "meta" not in result["output"][0]


def test_field_builder_rows_flow_into_connected_node_expressions():
    nodes = [
        {
            "id": "fields",
            "type": "field_builder",
            "params": {
                "fields": [
                    {"name": "company", "type": "string", "value": "Acme"},
                    {"name": "score", "type": "number", "value": "7"},
                ]
            },
        },
        {
            "id": "enrich",
            "type": "set_fields",
            "params": {
                "fields": [
                    {"name": "label", "value": "{{ $json.company }} review"},
                    {"name": "next_score", "value": "{{ $json.score + 1 }}"},
                ]
            },
        },
    ]
    result = asyncio.run(run_workflow(nodes, [{"source": "fields", "target": "enrich"}]))

    assert result["status"] == "success"
    assert result["output"] == [
        {"company": "Acme", "score": 7, "label": "Acme review", "next_score": 8}
    ]
    assert result["nodes"][1]["input_samples"] == [[{"company": "Acme", "score": 7}]]


def test_multi_input_ports_are_ordered_explicitly():
    nodes = [
        {
            "id": "source",
            "type": "manual_json",
            "params": {"data": [{"value": 1}, {"value": 2}]},
        },
        {"id": "left", "type": "filter", "params": {"condition": "$json.value == 2"}},
        {"id": "right", "type": "filter", "params": {"condition": "$json.value == 1"}},
        {"id": "join", "type": "merge", "params": {"mode": "append"}},
    ]
    edges = [
        {"source": "source", "target": "left"},
        {"source": "source", "target": "right"},
        {"source": "right", "target": "join", "target_input": 1},
        {"source": "left", "target": "join", "target_input": 0},
    ]
    result = asyncio.run(run_workflow(nodes, edges))
    assert result["output"] == [{"value": 2}, {"value": 1}]
    assert result["nodes"][-1]["rows_in"] == 2
    assert result["nodes"][-1]["input_samples"] == [
        [{"value": 2}],
        [{"value": 1}],
    ]


def test_invalid_params_are_rejected_before_any_node_runs():
    nodes = [
        {"id": "input", "type": "manual_json", "params": {"data": [{"value": 1}]}},
        {"id": "sort", "type": "sort", "params": {}},
    ]
    with pytest.raises(NodeError, match="field"):
        asyncio.run(run_workflow(nodes, [{"source": "input", "target": "sort"}]))


def test_failed_node_returns_redacted_diagnostic_log(monkeypatch):
    def fail_node(_items, _ctx):
        raise RuntimeError("sensitive provider response")

    monkeypatch.setattr(
        "app.engine.load_all",
        lambda: {
            "test_failure": NodeSpec(
                "test_failure",
                "Test failure",
                "test",
                "Raises a test error.",
                fail_node,
                [],
            )
        },
    )
    result = asyncio.run(run_workflow([{"id": "broken", "type": "test_failure", "params": {}}], []))

    assert result["status"] == "error"
    assert result["nodes"][0]["error"] == (
        "Node failed unexpectedly. Check its parameters and try again."
    )
    assert result["nodes"][0]["logs"] == ["broken: RuntimeError"]
    assert "sensitive provider response" not in str(result)


def test_catalog_has_all_required_node_groups():
    catalog = load_all()
    assert len(catalog) == 30  # firecrawl added (Nov 2026)
    assert {spec.group for spec in catalog.values()} == {
        "input",
        "transform",
        "search",
        "ai",
        "code",
    }


def test_csv_headers_normalize_to_snake_case():
    nodes = [
        {
            "id": "source",
            "type": "csv_file",
            "params": {"text": "Company Name,Website URL,Company Name\nAcme,https://acme.com,dup"},
            "delimiter": ",",
        }
    ]
    result = asyncio.run(run_workflow(nodes, []))
    assert result["status"] == "success"
    assert result["output"] == [
        {"company_name": "Acme", "website_url": "https://acme.com", "company_name_2": "dup"}
    ]
