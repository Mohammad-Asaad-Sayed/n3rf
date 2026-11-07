from __future__ import annotations

import inspect
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.contracts import Item, ItemList, coerce_items, paired
from app.errors import NodeError
from app.params import validate_params
from app.registry import NodeSpec, load_all


@dataclass
class RunContext:
    params: dict[str, Any]
    inputs: list[ItemList] = field(default_factory=list)
    node_outputs: dict[str, ItemList] = field(default_factory=dict)
    metrics: dict[str, int] = field(
        default_factory=lambda: {"llm_calls": 0, "tokens_in": 0, "tokens_out": 0}
    )
    logs: list[str] = field(default_factory=list)
    node_id: str = ""

    def param(
        self,
        key: str,
        expected: type | tuple[type, ...] | None = None,
        default: Any = None,
        *,
        required: bool = False,
    ) -> Any:
        value = self.params.get(key, default)
        if required and value in (None, ""):
            raise NodeError(f"Parameter '{key}' is required.")
        if value is not None and expected is not None and not isinstance(value, expected):
            names = (
                " or ".join(kind.__name__ for kind in expected)
                if isinstance(expected, tuple)
                else expected.__name__
            )
            raise NodeError(f"Parameter '{key}' must be {names}.")
        return value


def topological_order(
    nodes: list[dict[str, Any]], edges: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    by_id = {str(item.get("id")): item for item in nodes}
    if len(by_id) != len(nodes) or "None" in by_id:
        raise NodeError("Every node must have a unique id.")
    indegree = {node_id: 0 for node_id in by_id}
    downstream: dict[str, list[str]] = {node_id: [] for node_id in by_id}
    for edge in edges:
        source = str(edge.get("source", edge.get("from", "")))
        target = str(edge.get("target", edge.get("to", "")))
        if source not in by_id or target not in by_id:
            raise NodeError("Every connection must reference an existing node.")
        if source == target:
            raise NodeError(f"Node '{source}' cannot connect to itself.")
        if target in downstream[source]:
            raise NodeError(f"Duplicate connection from '{source}' to '{target}'.")
        downstream[source].append(target)
        indegree[target] += 1
    ready = [node_id for node_id in by_id if indegree[node_id] == 0]
    ordered: list[dict[str, Any]] = []
    while ready:
        current = ready.pop(0)
        ordered.append(by_id[current])
        for target in downstream[current]:
            indegree[target] -= 1
            if indegree[target] == 0:
                ready.append(target)
    if len(ordered) != len(nodes):
        cyclic = [node_id for node_id, degree in indegree.items() if degree]
        raise NodeError(f"Workflow contains a cycle involving: {', '.join(cyclic)}.")
    return ordered


async def _call(spec: NodeSpec, items: ItemList, ctx: RunContext) -> ItemList:
    result = spec.run(items, ctx)
    if inspect.isawaitable(result):
        result = await result
    if result is None:
        raise NodeError(f"Node '{spec.name}' returned no rows.")
    return coerce_items(result)


async def run_workflow(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    *,
    input_override: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    registry = load_all()
    ordered = topological_order(nodes, edges)
    specs = {}
    for config in nodes:
        kind = str(config.get("type", config.get("node", "")))
        if kind not in registry:
            raise NodeError(f"Node '{config.get('id', '')}' has unknown type '{kind}'.")
        specs[str(config["id"])] = registry[kind]
    incoming: dict[str, list[dict[str, Any]]] = {str(node["id"]): [] for node in nodes}
    for edge in edges:
        target = str(edge.get("target", edge.get("to", "")))
        source = str(edge.get("source", edge.get("from", "")))
        try:
            target_input = int(edge.get("target_input", edge.get("input", 0)))
        except (TypeError, ValueError) as exc:
            raise NodeError("Connection input ports must be non-negative integers.") from exc
        if target_input < 0 or target_input >= specs[target].inputs:
            raise NodeError(f"Connection to '{target}' uses an invalid input port.")
        if any(
            int(item.get("target_input", item.get("input", 0))) == target_input
            for item in incoming[target]
        ):
            raise NodeError(
                f"Input port {target_input + 1} on '{target}' already has a connection."
            )
        if source == target:
            raise NodeError(f"Node '{source}' cannot connect to itself.")
        incoming[target].append(edge)
    for edges_to_node in incoming.values():
        edges_to_node.sort(key=lambda edge: int(edge.get("target_input", edge.get("input", 0))))
    params_by_id = {}
    for config in ordered:
        instance_id = str(config["id"])
        params = config.get("params", {})
        if not isinstance(params, dict):
            raise NodeError(f"Parameters for node '{instance_id}' must be an object.")
        params_by_id[instance_id] = validate_params(specs[instance_id].params, params)

    context = RunContext({})
    results: list[dict[str, Any]] = []
    started = time.perf_counter()
    last_output: ItemList = []
    failed = False
    for config in ordered:
        instance_id = str(config["id"])
        kind = str(config.get("type", config.get("node", "")))
        if kind not in registry:
            raise NodeError(f"Node '{instance_id}' has unknown type '{kind}'.")
        spec = registry[kind]
        params = params_by_id[instance_id]
        ctx = RunContext(
            params,
            node_id=instance_id,
            node_outputs=context.node_outputs,
            metrics=context.metrics,
        )
        input_lists: list[ItemList] = [[] for _ in range(spec.inputs)]
        for edge in incoming[instance_id]:
            target_input = int(edge.get("target_input", edge.get("input", 0)))
            input_lists[target_input] = context.node_outputs.get(
                str(edge.get("source", edge.get("from", ""))), []
            )
        if not incoming[instance_id] and input_override is not None:
            input_lists[0] = coerce_items(input_override)
        if spec.inputs == 1 and not incoming[instance_id] and input_override is None:
            input_lists = []
        ctx.inputs = input_lists
        items = input_lists[0] if input_lists else []
        rows_in = sum(map(len, input_lists)) if spec.inputs > 1 else len(items)
        node_started = time.perf_counter()
        error = None
        status = "success"
        output: ItemList = []
        try:
            output = await _call(spec, items, ctx)
            output = [
                Item(json=row["json"], meta=paired(row, instance_id, index))
                for index, row in enumerate(output)
            ]
        except Exception as exc:
            ctx.logs.append(f"{instance_id}: {type(exc).__name__}")
            error = str(exc)
            if not isinstance(exc, (NodeError, ValueError, TypeError, KeyError)):
                error = "Node failed unexpectedly. Check its parameters and try again."
            status = "error"
            failed = True
        duration = round((time.perf_counter() - node_started) * 1000, 2)
        context.node_outputs[instance_id] = output
        last_output = output
        results.append(
            {
                "id": instance_id,
                "name": spec.name,
                "status": status,
                "ms": duration,
                "rows_in": rows_in,
                "rows_out": len(output),
                "error": error,
                "logs": ctx.logs,
                "input_samples": [
                    [dict(row["json"]) for row in input_list[:5]] for input_list in input_lists
                ],
                "sample": [dict(row["json"]) for row in output[:5]],
            }
        )
    return {
        "run_id": f"run_{uuid.uuid4().hex[:12]}",
        "status": "error" if failed else "success",
        "ms": round((time.perf_counter() - started) * 1000, 2),
        "nodes": results,
        "output": [dict(row["json"]) for row in last_output],
        "metrics": context.metrics,
    }
