from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.contracts import Item, ItemList, new_item
from app.errors import NodeError
from app.expressions import ExpressionError, evaluate, render
from app.params import Param
from app.registry import node


@node(
    "filter",
    "Filter",
    group="transform",
    description="Keep rows whose condition is true.",
    params=[
        Param(
            "condition",
            "string",
            "Condition",
            default="{{ $json.active }}",
            required=True,
            expression=True,
        ),
        Param("keep_empty", "boolean", "Keep rows on expression error", default=False),
    ],
)
def filter_node(items: ItemList, ctx: Any) -> ItemList:
    condition = ctx.param("condition", str, required=True)
    keep_empty = ctx.param("keep_empty", bool, False)
    kept = []
    for item in items:
        try:
            if evaluate(condition, item["json"]):
                kept.append(item)
        except ExpressionError:
            if keep_empty:
                kept.append(item)
    return kept


@node(
    "sort",
    "Sort",
    group="transform",
    description="Sort rows by a field.",
    params=[
        Param("field", "string", "Field", default="", required=True),
        Param("direction", "select", "Direction", default="asc", options=["asc", "desc"]),
        Param("numeric", "boolean", "Compare as numbers", default=False),
    ],
)
def sort_node(items: ItemList, ctx: Any) -> ItemList:
    field = ctx.param("field", str, required=True)
    numeric = ctx.param("numeric", bool, False)
    reverse = ctx.param("direction", str, "asc") == "desc"

    def key(item: Item) -> tuple[int, Any]:
        value = item["json"].get(field)
        if numeric and value is not None:
            try:
                return (0, float(value))
            except (ValueError, TypeError) as exc:
                raise NodeError(f"Field '{field}' contains a non-numeric value.") from exc
        return (value is None, str(value).casefold() if value is not None else "")

    return sorted(items, key=key, reverse=reverse)


@node(
    "limit",
    "Limit",
    group="transform",
    description="Keep a range of rows.",
    params=[
        Param("max", "number", "Maximum rows", default=100),
        Param("offset", "number", "Offset", default=0),
    ],
)
def limit(items: ItemList, ctx: Any) -> ItemList:
    maximum, offset = ctx.param("max", int, 100), ctx.param("offset", int, 0)
    if maximum < 0 or offset < 0:
        raise NodeError("Parameters 'max' and 'offset' must be zero or greater.")
    return items[offset : offset + maximum]


@node(
    "set_fields",
    "Set Fields",
    group="transform",
    description="Set fields on every row.",
    params=[
        Param(
            "fields",
            "rows",
            "Fields",
            default=[],
            columns=[
                {"key": "name", "label": "Name", "type": "string"},
                {"key": "value", "label": "Value", "type": "string", "expression": True},
            ],
            hint="Type @ to insert a field from each incoming row.",
        )
    ],
)
def set_fields(items: ItemList, ctx: Any) -> ItemList:
    fields = ctx.param("fields", list, [])
    output = []
    for item in items:
        row = dict(item["json"])
        for field in fields:
            name = field.get("name")
            if not name:
                raise NodeError("Every field needs a name.")
            row[name] = render(field.get("value", ""), row)
        output.append({"json": row, "meta": dict(item["meta"])})
    return output


@node(
    "remove_fields",
    "Remove Fields",
    group="transform",
    description="Remove comma-separated fields.",
    params=[Param("fields", "string", "Fields", default="", required=True)],
)
def remove_fields(items: ItemList, ctx: Any) -> ItemList:
    fields = {field.strip() for field in ctx.param("fields", str, required=True).split(",")}
    return [
        {
            "json": {key: value for key, value in item["json"].items() if key not in fields},
            "meta": dict(item["meta"]),
        }
        for item in items
    ]


@node(
    "rename_fields",
    "Rename Fields",
    group="transform",
    description="Rename row fields.",
    params=[
        Param(
            "fields",
            "rows",
            "Renames",
            default=[],
            columns=[
                {"key": "from", "label": "From", "type": "string"},
                {"key": "to", "label": "To", "type": "string"},
            ],
        )
    ],
)
def rename_fields(items: ItemList, ctx: Any) -> ItemList:
    names = ctx.param("fields", list, [])
    output = []
    for item in items:
        row = dict(item["json"])
        for rename in names:
            source, target = rename.get("from"), rename.get("to")
            if source in row and target:
                row[target] = row.pop(source)
        output.append({"json": row, "meta": dict(item["meta"])})
    return output


@node(
    "aggregate",
    "Aggregate",
    group="transform",
    description="Group and aggregate rows.",
    params=[
        Param("group_by", "string", "Group by field", default=""),
        Param(
            "fields",
            "rows",
            "Aggregations",
            default=[],
            columns=[
                {"key": "field", "label": "Field", "type": "string"},
                {
                    "key": "op",
                    "label": "Operation",
                    "type": "select",
                    "options": ["count", "sum", "avg", "min", "max"],
                },
                {"key": "as", "label": "Output field", "type": "string"},
            ],
        ),
    ],
)
def aggregate(items: ItemList, ctx: Any) -> ItemList:
    group_by = ctx.param("group_by", str, "")
    specs = ctx.param("fields", list, [])
    groups: dict[Any, list[Item]] = defaultdict(list)
    for item in items:
        groups[item["json"].get(group_by) if group_by else None].append(item)
    output = []
    for key, group in groups.items():
        result = {group_by: key} if group_by else {}
        for spec in specs:
            field, operation = spec.get("field"), spec.get("op")
            name = spec.get("as") or f"{operation}_{field}"
            values = [row["json"].get(field) for row in group if row["json"].get(field) is not None]
            try:
                if operation == "count":
                    result[name] = len(values) if field else len(group)
                elif operation == "sum":
                    result[name] = sum(float(value) for value in values)
                elif operation == "avg":
                    result[name] = (
                        sum(float(value) for value in values) / len(values) if values else None
                    )
                elif operation == "min":
                    result[name] = min(values) if values else None
                elif operation == "max":
                    result[name] = max(values) if values else None
                else:
                    raise NodeError(f"Unsupported aggregate operation '{operation}'.")
            except (TypeError, ValueError) as exc:
                raise NodeError(f"Cannot apply '{operation}' to field '{field}'.") from exc
        meta = {"paired": [row["meta"].get("paired", index) for index, row in enumerate(group)]}
        output.append(new_item(result, **meta))
    return output


@node(
    "expand_arrays",
    "Expand Arrays",
    group="transform",
    description="Create one row per array value.",
    params=[
        Param("field", "string", "Array field", default="", required=True),
        Param("max_output_rows", "number", "Maximum output rows", default=500),
    ],
)
def expand_arrays(items: ItemList, ctx: Any) -> ItemList:
    field = ctx.param("field", str, required=True)
    maximum = ctx.param("max_output_rows", int, 500)
    output = []
    for item in items:
        values = item["json"].get(field, [])
        if not isinstance(values, list):
            raise NodeError(f"Field '{field}' must contain an array.")
        for value in values:
            if len(output) >= maximum:
                raise NodeError(f"Expansion exceeded max_output_rows ({maximum}).")
            output.append(new_item({**item["json"], field: value}, **dict(item["meta"])))
    return output


@node(
    "merge",
    "Merge",
    group="transform",
    description="Append or merge two inputs by key.",
    inputs=2,
    params=[
        Param(
            "mode",
            "select",
            "Mode",
            default="append",
            options=["append", "merge_by_key"],
        ),
        Param(
            "key",
            "string",
            "Match field",
            default="",
            show_if={"param": "mode", "in": ["merge_by_key"]},
        ),
    ],
)
def merge(items: ItemList, ctx: Any) -> ItemList:
    inputs = (ctx.inputs + [[], []])[:2]
    mode, key = ctx.param("mode", str, "append"), ctx.param("key", str, "")
    if mode == "append":
        return inputs[0] + inputs[1]
    if not key:
        raise NodeError("Parameter 'key' is required for merge_by_key.")
    right = {row["json"].get(key): row for row in inputs[1]}
    return [
        new_item({**row["json"], **right[row["json"].get(key)]["json"]}, **dict(row["meta"]))
        if row["json"].get(key) in right
        else row
        for row in inputs[0]
    ]


@node(
    "compare_datasets",
    "Compare Datasets",
    group="transform",
    description="Compare inputs by a key.",
    inputs=2,
    params=[
        Param("key", "string", "Match field", default="", required=True),
        Param(
            "mode",
            "select",
            "Keep",
            default="inner",
            options=["inner", "left_only", "right_only"],
        ),
    ],
)
def compare_datasets(items: ItemList, ctx: Any) -> ItemList:
    left, right = (ctx.inputs + [[], []])[:2]
    key, mode = ctx.param("key", str, required=True), ctx.param("mode", str, "inner")
    left_keys = {row["json"].get(key) for row in left}
    right_keys = {row["json"].get(key) for row in right}
    if mode == "inner":
        return [row for row in left if row["json"].get(key) in right_keys]
    if mode == "left_only":
        return [row for row in left if row["json"].get(key) not in right_keys]
    return [row for row in right if row["json"].get(key) not in left_keys]


@node(
    "dedupe",
    "Deduplicate",
    group="transform",
    description="Keep the first or last row for a field.",
    params=[
        Param("field", "string", "Field", default="", required=True),
        Param("keep", "select", "Keep", default="first", options=["first", "last"]),
    ],
)
def dedupe(items: ItemList, ctx: Any) -> ItemList:
    field, keep = (
        ctx.param("field", str, required=True),
        ctx.param("keep", str, "first"),
    )
    selected = {}
    for item in items:
        value = item["json"].get(field)
        if value is not None and (keep == "last" or value not in selected):
            selected[value] = item
    return list(selected.values())
