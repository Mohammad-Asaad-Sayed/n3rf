"""Rows keep user data in json and execution metadata in meta."""

from typing import Any, TypedDict

from app.errors import NodeError


class Item(TypedDict):
    json: dict[str, Any]
    meta: dict[str, Any]


ItemList = list[Item]


def new_item(data: dict[str, Any], **meta: Any) -> Item:
    return {"json": dict(data), "meta": dict(meta)}


def coerce_items(value: Any) -> ItemList:
    if not isinstance(value, list):
        raise NodeError("Input data must be a list of rows.")
    rows: ItemList = []
    for index, row in enumerate(value):
        if isinstance(row, dict) and set(row) >= {"json", "meta"}:
            if not isinstance(row["json"], dict) or not isinstance(row["meta"], dict):
                raise ValueError(f"Row {index + 1} must contain object json and meta.")
            rows.append({"json": dict(row["json"]), "meta": dict(row["meta"])})
        elif isinstance(row, dict):
            rows.append(new_item(row))
        else:
            rows.append(new_item({"value": row}))
    return rows


def paired(item: Item, node_id: str, row_index: int = 0, **meta: Any) -> dict[str, Any]:
    result = dict(item["meta"])
    result.update(meta)
    result["paired"] = item["meta"].get("paired", item["meta"].get("row", row_index))
    result["node"] = node_id
    return result
