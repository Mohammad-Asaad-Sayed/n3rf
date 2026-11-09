from typing import Any

from app import store
from app.engine import migrate_nodes, run_workflow, topological_order
from app.errors import NodeError
from app.params import validate_params
from app.registry import load_all


def validate_graph(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> None:
    nodes = migrate_nodes(nodes)
    registry = load_all()
    topological_order(nodes, edges)
    for config in nodes:
        unknown = set(config) - {"id", "type", "node", "params", "position"}
        if unknown:
            raise NodeError(
                f"Node '{config.get('id', '')}' has unsupported field(s): "
                f"{', '.join(sorted(unknown))}."
            )
        kind = str(config.get("type", config.get("node", "")))
        if kind not in registry:
            raise NodeError(f"Node '{config.get('id', '')}' has unknown type '{kind}'.")
        params = config.get("params", {})
        if not isinstance(params, dict):
            raise NodeError(f"Parameters for node '{config.get('id', '')}' must be an object.")
        validate_params(registry[kind].params, params)
    input_ports: set[tuple[str, int]] = set()
    configs = {str(config["id"]): config for config in nodes}
    for edge in edges:
        target = str(edge.get("target", edge.get("to", "")))
        try:
            port = int(edge.get("target_input", edge.get("input", 0)))
        except (TypeError, ValueError) as exc:
            raise NodeError("Connection input ports must be non-negative integers.") from exc
        config = configs[target]
        kind = str(config.get("type", config.get("node", "")))
        if port < 0 or port >= registry[kind].inputs:
            raise NodeError(f"Connection to '{target}' uses an invalid input port.")
        if (target, port) in input_ports:
            raise NodeError(f"Input port {port + 1} on '{target}' already has a connection.")
        input_ports.add((target, port))


def upstream_subgraph(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    target_node_id: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    node_ids = {str(node.get("id")) for node in nodes}
    if target_node_id not in node_ids:
        raise NodeError(f"Node '{target_node_id}' does not exist in this workflow.")

    incoming: dict[str, list[str]] = {}
    for edge in edges:
        source = str(edge.get("source", edge.get("from", "")))
        target = str(edge.get("target", edge.get("to", "")))
        incoming.setdefault(target, []).append(source)

    included = {target_node_id}
    pending = [target_node_id]
    while pending:
        current = pending.pop()
        for source in incoming.get(current, []):
            if source not in included:
                included.add(source)
                pending.append(source)

    selected_nodes = [node for node in nodes if str(node.get("id")) in included]
    selected_edges = [
        edge
        for edge in edges
        if str(edge.get("source", edge.get("from", ""))) in included
        and str(edge.get("target", edge.get("to", ""))) in included
    ]
    return selected_nodes, selected_edges


def _apply_test_limit(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    test_rows: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Slice every input chain to ``test_rows`` (Altclay-style cheap trial)."""
    if test_rows <= 0:
        return nodes, edges
    targets = {str(edge.get("target", edge.get("to", ""))) for edge in edges}
    sources = [node for node in nodes if str(node.get("id")) not in targets]
    if not sources:
        return nodes, edges
    new_nodes = [dict(node) for node in nodes]
    new_edges: list[dict[str, Any]] = []
    for source in sources:
        source_id = str(source.get("id"))
        limit_id = f"__test_limit_{source_id}"
        new_nodes.append(
            {
                "id": limit_id,
                "type": "limit",
                "params": {"max": test_rows, "offset": 0},
                "position": source.get("position", {"x": 0, "y": 0}),
            }
        )
        new_edges.append({"source": source_id, "target": limit_id, "target_input": 0})
        for edge in edges:
            if str(edge.get("source", edge.get("from", ""))) == source_id:
                rewired = dict(edge)
                rewired["source"] = limit_id
                new_edges.append(rewired)
    # Keep edges that do not touch a source (e.g. downstream of a source we handled).
    for edge in edges:
        if str(edge.get("source", edge.get("from", ""))) not in {
            str(node.get("id")) for node in sources
        }:
            new_edges.append(dict(edge))
    return new_nodes, new_edges


async def run(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    override: list[dict[str, Any]] | None,
    workflow_id: str | None = None,
    target_node_id: str | None = None,
    test_rows: int | None = None,
) -> dict[str, Any]:
    if target_node_id is not None:
        nodes, edges = upstream_subgraph(nodes, edges, target_node_id)
    if test_rows is not None:
        nodes, edges = _apply_test_limit(nodes, edges, test_rows)
    validate_graph(nodes, edges)
    result = await run_workflow(nodes, edges, input_override=override)
    if target_node_id is None:
        store.save_run(result, workflow_id)
    return result
