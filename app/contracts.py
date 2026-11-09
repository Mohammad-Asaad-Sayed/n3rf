"""Rows keep user data in json and execution metadata in meta."""

import re
from typing import Any, TypedDict

from app.errors import NodeError


def to_snake_case(name: str) -> str:
    """Convert a column name to snake_case: "Company Name" -> "company_name"."""
    cleaned = re.sub(r"[^0-9a-zA-Z_]+", "_", str(name).strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_").lower()
    if cleaned and cleaned[0].isdigit():
        cleaned = f"field_{cleaned}"
    return cleaned


def normalize_headers(headers: list[str]) -> list[str]:
    """Normalize to snake_case, keeping uniqueness with _2/_3 suffixes."""
    seen: set[str] = set()
    result: list[str] = []
    for index, raw in enumerate(headers):
        base = to_snake_case(raw) or f"column_{index + 1}"
        candidate = base
        suffix = 2
        while candidate in seen:
            candidate = f"{base}_{suffix}"
            suffix += 1
        seen.add(candidate)
        result.append(candidate)
    return result


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
