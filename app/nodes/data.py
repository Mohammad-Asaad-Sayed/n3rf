from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.contracts import Item, ItemList, new_item
from app.errors import NodeError
from app.expressions import ExpressionError, evaluate, render
from app.params import Param
from app.registry import node


def _is_truthy(val: Any) -> bool:
    if isinstance(val, str) and val.strip().lower() in ("false", "0", "null", "none"):
        return False
    return bool(val)


@node(
    "filter",
    "Filter",
    group="transform",
    description="Keep only rows that match a condition. Drops the rest.",
    params=[
        Param(
            "condition",
            "string",
            "Condition",
            default="active == true",
            required=True,
            expression=True,
            hint='Example: "score >= 5" or "active == true". @ picks a field.',
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
            if _is_truthy(evaluate(condition, item["json"])):
                kept.append(item)
        except ExpressionError:
            if keep_empty:
                kept.append(item)
    return kept


@node(
    "if_else",
    "If / Else",
    group="transform",
    description="If a row matches, set the true fields; otherwise set the false fields.",
    params=[
        Param(
            "condition",
            "string",
            "If",
            default="active == true",
            required=True,
            expression=True,
            hint="Is this true for the row? Example: score >= 5",
        ),
        Param(
            "output",
            "select",
            "Keep",
            default="all_rows",
            options=["all_rows", "true_only", "false_only"],
            hint="Keep both branches, or only one.",
        ),
        Param(
            "true_fields",
            "rows",
            "If true, set",
            default=[{"name": "branch", "value": "true"}],
            columns=[
                {"key": "name", "label": "Field", "type": "string"},
                {"key": "value", "label": "Value", "type": "string", "expression": True},
            ],
            show_if={"param": "output", "in": ["all_rows", "true_only"]},
            hint="Example: branch = high",
        ),
        Param(
            "false_fields",
            "rows",
            "If false, set",
            default=[{"name": "branch", "value": "false"}],
            columns=[
                {"key": "name", "label": "Field", "type": "string"},
                {"key": "value", "label": "Value", "type": "string", "expression": True},
            ],
            show_if={"param": "output", "in": ["all_rows", "false_only"]},
            hint="Example: branch = low",
        ),
        Param(
            "keep_empty",
            "boolean",
            "On error, keep the row",
            default=False,
            hint="Off drops rows with a bad condition; on treats them as false.",
        ),
    ],
)
def if_else(items: ItemList, ctx: Any) -> ItemList:
    condition = ctx.param("condition", str, required=True)
    output_mode = ctx.param("output", str, "all_rows")
    if output_mode not in ("all_rows", "true_only", "false_only"):
        raise NodeError(f"Parameter 'output' has an unsupported value '{output_mode}'.")
    true_fields = ctx.param("true_fields", list, []) or []
    false_fields = ctx.param("false_fields", list, []) or []
    keep_empty = ctx.param("keep_empty", bool, False)
    output: ItemList = []
    for item in items:
        try:
            matched = _is_truthy(evaluate(condition, item["json"]))
        except ExpressionError:
            if not keep_empty:
                continue
            matched = False
        if output_mode == "true_only" and not matched:
            continue
        if output_mode == "false_only" and matched:
            continue
        fields = true_fields if matched else false_fields
        row = dict(item["json"])
        for field in fields:
            name = field.get("name")
            if not name:
                raise NodeError("Every field needs a name.")
            row[name] = render(field.get("value", ""), row)
        output.append({"json": row, "meta": dict(item["meta"])})
    return output


@node(
    "sort",
    "Sort",
    group="transform",
    description="Order rows by a field, smallest first or largest first.",
    params=[
        Param(
            "field",
            "string",
            "Field",
            default="",
            required=True,
            hint="Field to sort by. Example: company or score.",
        ),
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
    description="Keep the first N rows, or skip N then keep M.",
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
    description="Add or overwrite fields on every row. Use @ to copy another field.",
    params=[
        Param(
            "fields",
            "rows",
            "Fields",
            default=[{"name": "label", "value": "{{company}} review"}],
            columns=[
                {"key": "name", "label": "Name", "type": "string"},
                {"key": "value", "label": "Value", "type": "string", "expression": True},
            ],
            hint="@ picks a field. Example value: {{company}} review",
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
    description="Drop fields from every row. Handy before export.",
    params=[
        Param(
            "fields",
            "string",
            "Fields",
            default="",
            required=True,
            hint="Comma-separated field names. Example: score, old_field",
        )
    ],
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
    description="Rename fields, e.g. name → company. Values move with the field.",
    params=[
        Param(
            "fields",
            "rows",
            "Renames",
            default=[{"from": "name", "to": "company"}],
            columns=[
                {"key": "from", "label": "From", "type": "string"},
                {"key": "to", "label": "To", "type": "string"},
            ],
            hint="One row per rename. Example: name → company.",
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
    description="Group rows and summarize each group (count, sum, average).",
    params=[
        Param(
            "group_by",
            "string",
            "Group by field",
            default="",
            hint="Field to group by. Leave blank for one total row. Example: industry.",
        ),
        Param(
            "fields",
            "rows",
            "Aggregations",
            default=[{"field": "score", "op": "avg", "as": "avg_score"}],
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
            hint="Example row: field score, operation avg, output avg_score.",
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
    description="Turn one row with a list into many rows, one per list item.",
    params=[
        Param(
            "field",
            "string",
            "Array field",
            default="",
            required=True,
            hint="List-valued field to expand. Example: tags or scores.",
        ),
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
    description="Combine two inputs: stack them, or join them on a match field.",
    inputs=2,
    params=[
        Param(
            "mode",
            "select",
            "Mode",
            default="append",
            options=["append", "merge_by_key"],
            hint="append = stack both lists. merge_by_key = join on Match field.",
        ),
        Param(
            "key",
            "string",
            "Match field",
            default="",
            show_if={"param": "mode", "in": ["merge_by_key"]},
            hint="Field present in both inputs. Example: company.",
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
    description="Find rows that are in both inputs, or only in one. Needs two inputs.",
    inputs=2,
    params=[
        Param(
            "key",
            "string",
            "Match field",
            default="",
            required=True,
            hint="Field present in both inputs. Example: company.",
        ),
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
    description="Keep one row per field value — drops duplicates.",
    params=[
        Param(
            "field",
            "string",
            "Field",
            default="",
            required=True,
            hint="Rows with the same value here collapse to one. Example: company.",
        ),
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
