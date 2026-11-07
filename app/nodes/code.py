from __future__ import annotations

from typing import Any

from app.contracts import ItemList
from app.errors import NodeError
from app.params import Param
from app.registry import node
from app.sandbox import run_code


@node(
    "code",
    "Code",
    group="code",
    description="Transform the batch in an isolated Python process.",
    params=[
        Param("code", "code", "Python", default="return items"),
        Param("timeout", "number", "Time limit", default=3, unit="seconds"),
        Param("max_output_rows", "number", "Maximum output rows", default=500),
    ],
)
def code_node(items: ItemList, ctx: Any) -> ItemList:
    timeout = ctx.param("timeout", int, 3)
    maximum = ctx.param("max_output_rows", int, 500)
    if timeout < 1 or timeout > 30:
        raise NodeError("Parameter 'timeout' must be between 1 and 30 seconds.")
    if maximum < 1 or maximum > 10000:
        raise NodeError("Parameter 'max_output_rows' must be between 1 and 10000.")
    rows = [{"json": row["json"], "meta": row["meta"]} for row in items]
    result = run_code(ctx.param("code", str, "return items"), rows, timeout)
    if len(result) > maximum:
        raise NodeError(f"Code output exceeded max_output_rows ({maximum}).")
    return [{"json": row.get("json", row), "meta": row.get("meta", {})} for row in result]
