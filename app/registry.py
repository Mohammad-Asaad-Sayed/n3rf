from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.params import Param

REGISTRY: dict[str, NodeSpec] = {}


@dataclass(frozen=True)
class NodeSpec:
    id: str
    name: str
    group: str
    description: str
    run: Callable[..., Any]
    params: list[Param]
    inputs: int = 1

    def public(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "group": self.group,
            "description": self.description,
            "inputs": self.inputs,
            "params": [param.public() for param in self.params],
        }


def node(
    node_id: str,
    name: str,
    *,
    group: str,
    description: str,
    params: list[Param] | None = None,
    inputs: int = 1,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorate(func: Callable[..., Any]) -> Callable[..., Any]:
        if node_id in REGISTRY:
            raise ValueError(f"Node id '{node_id}' is already registered.")
        REGISTRY[node_id] = NodeSpec(node_id, name, group, description, func, params or [], inputs)
        return func

    return decorate


def load_all() -> dict[str, NodeSpec]:
    from app.nodes import ai, code, data, http, input  # noqa: F401

    return REGISTRY
