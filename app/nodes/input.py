from __future__ import annotations

import base64
import csv
import io
import json
from typing import Any

from app.contracts import ItemList, new_item
from app.errors import NodeError
from app.params import Param
from app.registry import node


@node(
    "manual_json",
    "Manual JSON",
    group="input",
    description="Enter a JSON array of rows.",
    params=[Param("data", "json", "Rows", default=[], required=True)],
)
def manual_json(items: ItemList, ctx: Any) -> ItemList:
    data = ctx.param("data", required=True)
    if not isinstance(data, list):
        raise NodeError("Parameter 'data' must be a JSON array.")
    return [new_item(row if isinstance(row, dict) else {"value": row}) for row in data]


@node(
    "text_lines",
    "Text Lines",
    group="input",
    description="Create one row per line.",
    params=[
        Param("text", "textarea", "Text", default=""),
        Param(
            "delimiter",
            "select",
            "Split by",
            default="line",
            options=["line", "comma", "tab"],
        ),
    ],
)
def text_lines(items: ItemList, ctx: Any) -> ItemList:
    text = ctx.param("text", str, "")
    delimiter = {"line": "\n", "comma": ",", "tab": "\t"}[ctx.param("delimiter", str, "line")]
    return [new_item({"value": part.strip()}) for part in text.split(delimiter) if part.strip()]


def _parse_csv(text: str, delimiter: str, has_header: bool) -> ItemList:
    rows = list(csv.reader(io.StringIO(text), delimiter=delimiter))
    if not rows:
        return []
    if has_header:
        headers = [name.strip() or f"column_{index + 1}" for index, name in enumerate(rows.pop(0))]
    else:
        headers = [f"column_{index + 1}" for index in range(max(map(len, rows), default=0))]
    return [new_item(dict(zip(headers, row, strict=False))) for row in rows]


@node(
    "csv_file",
    "CSV File",
    group="input",
    description="Parse CSV text into rows.",
    params=[
        Param("text", "textarea", "CSV content", default=""),
        Param("delimiter", "string", "Delimiter", default=","),
        Param("header", "boolean", "First row is header", default=True),
    ],
)
def csv_file(items: ItemList, ctx: Any) -> ItemList:
    delimiter = ctx.param("delimiter", str, ",")
    if len(delimiter) != 1:
        raise NodeError("Parameter 'delimiter' must be one character.")
    return _parse_csv(ctx.param("text", str, ""), delimiter, ctx.param("header", bool, True))


@node(
    "file_upload",
    "File Upload",
    group="input",
    description="Read a base64 file payload.",
    params=[
        Param("filename", "string", "Filename", default="upload.txt"),
        Param("content", "file", "File", default=""),
        Param(
            "encoding",
            "select",
            "Interpret as",
            default="text",
            options=["text", "csv", "json"],
        ),
    ],
)
def file_upload(items: ItemList, ctx: Any) -> ItemList:
    content = ctx.param("content", str, "")
    try:
        raw = base64.b64decode(content, validate=True)
        text = raw.decode("utf-8")
    except (ValueError, UnicodeDecodeError) as exc:
        raise NodeError("Parameter 'content' must be valid base64 containing UTF-8 text.") from exc
    encoding = ctx.param("encoding", str, "text")
    if encoding == "csv":
        return _parse_csv(text, ",", True)
    if encoding == "json":
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise NodeError("Uploaded file does not contain valid JSON.") from exc
        return [
            new_item(row if isinstance(row, dict) else {"value": row})
            for row in (data if isinstance(data, list) else [data])
        ]
    return [new_item({"filename": ctx.param("filename", str, "upload.txt"), "content": text})]


@node(
    "spreadsheet_paste",
    "Spreadsheet Paste",
    group="input",
    description="Parse tab-separated spreadsheet data.",
    params=[
        Param("text", "textarea", "Paste cells", default=""),
        Param("header", "boolean", "First row is header", default=True),
    ],
)
def spreadsheet_paste(items: ItemList, ctx: Any) -> ItemList:
    return _parse_csv(ctx.param("text", str, ""), "\t", ctx.param("header", bool, True))


@node(
    "field_builder",
    "Field Builder",
    group="input",
    description="Build one row from declared fields.",
    params=[
        Param(
            "fields",
            "rows",
            "Fields",
            default=[],
            columns=[
                {"key": "name", "label": "Name", "type": "string"},
                {
                    "key": "type",
                    "label": "Type",
                    "type": "select",
                    "options": ["string", "number", "boolean"],
                },
                {"key": "value", "label": "Value", "type": "string"},
            ],
        )
    ],
)
def field_builder(items: ItemList, ctx: Any) -> ItemList:
    row: dict[str, Any] = {}
    for field in ctx.param("fields", list, []):
        name = field.get("name")
        if not name:
            raise NodeError("Every field needs a name.")
        value: Any = field.get("value")
        kind = field.get("type", "string")
        try:
            if kind == "number":
                value = float(value) if "." in str(value) else int(value)
            elif kind == "boolean":
                value = str(value).lower() in {"true", "1", "yes"}
        except ValueError as exc:
            raise NodeError(f"Field '{name}' has an invalid {kind} value.") from exc
        row[name] = value
    return [new_item(row)]


@node(
    "example_dataset",
    "Example Dataset",
    group="input",
    description="Load a small sample dataset.",
    params=[
        Param(
            "dataset",
            "select",
            "Dataset",
            default="companies",
            options=["companies", "people", "products"],
        ),
        Param("rows", "number", "Row count", default=3, unit="rows"),
    ],
)
def example_dataset(items: ItemList, ctx: Any) -> ItemList:
    samples = {
        "companies": [
            {"company": "Acme", "industry": "software"},
            {"company": "Northstar", "industry": "retail"},
            {"company": "Bluebird", "industry": "health"},
        ],
        "people": [
            {"name": "Avery", "role": "analyst"},
            {"name": "Morgan", "role": "designer"},
            {"name": "Jordan", "role": "engineer"},
        ],
        "products": [
            {"product": "Notebook", "price": 12},
            {"product": "Lamp", "price": 34},
            {"product": "Mug", "price": 8},
        ],
    }
    count = ctx.param("rows", int, 3)
    if count < 0 or count > 5000:
        raise NodeError("Parameter 'rows' must be between 0 and 5000.")
    rows = samples[ctx.param("dataset", str, "companies")]
    return [new_item(rows[index % len(rows)]) for index in range(count)]
