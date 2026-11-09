"""T-013: engine shapes — order, diamond, edges, errors, empty."""

import asyncio

import pytest

from app.engine import run_workflow, topological_order
from app.errors import NodeError


def test_linear_order_is_topological():
    nodes = [
        {"id": "c", "type": "limit", "params": {"max": 10}},
        {"id": "a", "type": "manual_json", "params": {"data": [{"v": 1}]}},
        {"id": "b", "type": "filter", "params": {"condition": "v>=1"}},
    ]
    ordered = topological_order(
        nodes, [{"source": "a", "target": "b"}, {"source": "b", "target": "c"}]
    )
    assert [n["id"] for n in ordered] == ["a", "b", "c"]


def test_linear_run():
    nodes = [
        {"id": "a", "type": "manual_json", "params": {"data": [{"v": 1}, {"v": 2}]}},
        {"id": "b", "type": "filter", "params": {"condition": "v>=2"}},
    ]
    result = asyncio.run(run_workflow(nodes, [{"source": "a", "target": "b"}]))
    assert result["status"] == "success"
    assert result["output"] == [{"v": 2}]
    assert result["nodes"][1]["rows_in"] == 2
    assert result["nodes"][1]["rows_out"] == 1


def test_diamond_fan_out_fan_in():
    nodes = [
        {"id": "s", "type": "manual_json", "params": {"data": [{"v": 1}, {"v": 2}]}},
        {"id": "a", "type": "filter", "params": {"condition": "v==1"}},
        {"id": "b", "type": "filter", "params": {"condition": "v==2"}},
        {"id": "m", "type": "merge", "params": {"mode": "append"}},
    ]
    edges = [
        {"source": "s", "target": "a"},
        {"source": "s", "target": "b"},
        {"source": "a", "target": "m", "target_input": 0},
        {"source": "b", "target": "m", "target_input": 1},
    ]
    result = asyncio.run(run_workflow(nodes, edges))
    assert result["status"] == "success"
    assert result["output"] == [{"v": 1}, {"v": 2}]
    # both branches ran before the join
    order = [n["id"] for n in result["nodes"]]
    assert order.index("m") > order.index("a")
    assert order.index("m") > order.index("b")


def test_disconnected_node_still_runs():
    nodes = [
        {"id": "a", "type": "manual_json", "params": {"data": [{"v": 1}]}},
        {"id": "solo", "type": "example_dataset", "params": {"dataset": "companies", "rows": 2}},
    ]
    result = asyncio.run(run_workflow(nodes, []))
    assert result["status"] == "success"
    assert len(result["nodes"]) == 2


def test_node_that_raises_marks_error():
    nodes = [
        {"id": "a", "type": "manual_json", "params": {"data": [{"v": 1}]}},
        {"id": "b", "type": "sort", "params": {}},
    ]
    # invalid param is rejected before any node runs (engine contract)
    with pytest.raises(NodeError, match="field"):
        asyncio.run(run_workflow(nodes, [{"source": "a", "target": "b"}]))


def test_node_that_returns_nothing():
    nodes = [
        {"id": "a", "type": "manual_json", "params": {"data": [{"v": 1}]}},
        {"id": "f", "type": "filter", "params": {"condition": "v==99"}},
        {"id": "l", "type": "limit", "params": {"max": 10}},
    ]
    result = asyncio.run(
        run_workflow(nodes, [{"source": "a", "target": "f"}, {"source": "f", "target": "l"}])
    )
    assert result["status"] == "success"
    assert result["output"] == []
    assert [(n["id"], n["rows_out"]) for n in result["nodes"]] == [
        ("a", 1),
        ("f", 0),
        ("l", 0),
    ]


def test_ctx_inputs_ordered_a_before_b():
    nodes = [
        {"id": "s", "type": "manual_json", "params": {"data": [{"v": 1}, {"v": 2}]}},
        {"id": "left", "type": "filter", "params": {"condition": "v==2"}},
        {"id": "right", "type": "filter", "params": {"condition": "v==1"}},
        {"id": "m", "type": "merge", "params": {"mode": "append"}},
    ]
    edges = [
        {"source": "s", "target": "left"},
        {"source": "s", "target": "right"},
        {"source": "right", "target": "m", "target_input": 1},
        {"source": "left", "target": "m", "target_input": 0},
    ]
    result = asyncio.run(run_workflow(nodes, edges))
    assert result["output"] == [{"v": 2}, {"v": 1}]
    assert result["nodes"][-1]["input_samples"] == [[{"v": 2}], [{"v": 1}]]


def test_cycle_names_nodes():
    nodes = [{"id": "a"}, {"id": "b"}]
    with pytest.raises(NodeError, match="a, b|b, a"):
        topological_order(nodes, [{"source": "a", "target": "b"}, {"source": "b", "target": "a"}])


def test_self_and_duplicate_rejected():
    nodes = [{"id": "a", "type": "manual_json", "params": {"data": []}}]
    with pytest.raises(NodeError, match="itself"):
        asyncio.run(run_workflow(nodes, [{"source": "a", "target": "a"}]))
    nodes2 = [
        {"id": "a", "type": "manual_json", "params": {"data": []}},
        {"id": "b", "type": "limit", "params": {"max": 1}},
    ]
    with pytest.raises(NodeError, match="Duplicate"):
        asyncio.run(
            run_workflow(nodes2, [{"source": "a", "target": "b"}, {"source": "a", "target": "b"}])
        )
