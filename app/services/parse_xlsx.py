"""XLSX (Office Open XML) parsing with the standard library only.

XLSX is a ZIP of XML parts, so ``zipfile`` + ``xml.etree`` + ``csv`` are
enough — no ``openpyxl`` dependency. Legacy binary ``.xls`` (OLE2) is
rejected with a clear message; convert to ``.xlsx`` / CSV first.
"""

from __future__ import annotations

import csv
import io
import xml.etree.ElementTree as ET
import zipfile

from app.contracts import normalize_headers

_NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pkg": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def _local(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


def _cell_value(cell: ET.Element, shared: list[str]) -> str:
    cell_type = cell.get("t")
    if cell_type == "inlineStr":
        text = "".join(node.text or "" for node in cell.iter() if _local(node.tag) == "t")
        return text
    value_el = cell.find("main:v", _NS)
    if value_el is None or value_el.text is None:
        return ""
    raw = value_el.text.strip()
    if cell_type == "s":
        try:
            return shared[int(float(raw))] if raw else ""
        except (ValueError, IndexError):
            return raw
    if cell_type in {"str", "e"}:
        return raw
    # Numbers / booleans: normalize 1.0 -> 1, keep booleans readable.
    if raw in {"1", "0"} and cell_type == "b":
        return "true" if raw == "1" else "false"
    try:
        number = float(raw)
    except ValueError:
        return raw
    return str(int(number)) if number.is_integer() else str(number)


def _column_index(reference: str) -> int:
    letters = "".join(char for char in reference if char.isalpha()).upper() or "A"
    index = 0
    for char in letters:
        index = index * 26 + (ord(char) - ord("A") + 1)
    return index - 1


def parse_xlsx_bytes(data: bytes) -> dict[str, object]:
    """Return {columns, rows, totalRows, csvText} for the first sheet."""
    if not zipfile.is_zipfile(io.BytesIO(data)):
        raise ValueError("Not a valid .xlsx file. Export as .xlsx or CSV and try again.")

    with zipfile.ZipFile(io.BytesIO(data)) as bundle:
        names = set(bundle.namelist())
        shared: list[str] = []
        if "xl/sharedStrings.xml" in names:
            root = ET.fromstring(bundle.read("xl/sharedStrings.xml"))
            for item in root.findall("main:si", _NS):
                shared.append(
                    "".join(node.text or "" for node in item.iter() if _local(node.tag) == "t")
                )

        sheet_names = sorted(
            name for name in names if name.startswith("xl/worksheets/") and name.endswith(".xml")
        )
        if not sheet_names:
            raise ValueError("This .xlsx file has no sheets to read.")

        sheet_root = ET.fromstring(bundle.read(sheet_names[0]))

    grid: list[dict[int, str]] = []
    for row_el in sheet_root.iter():
        if _local(row_el.tag) != "row":
            continue
        row: dict[int, str] = {}
        for cell in row_el:
            if _local(cell.tag) != "c":
                continue
            reference = cell.get("r") or ""
            row[_column_index(reference)] = _cell_value(cell, shared)
        if row:
            grid.append(row)

    if not grid:
        return {"columns": [], "rows": [], "totalRows": 0, "csvText": ""}

    width = max(max(row) + 1 for row in grid)
    header = normalize_headers(
        [
            (grid[0].get(index, "") or f"column_{index + 1}").strip() or f"column_{index + 1}"
            for index in range(width)
        ]
    )
    rows: list[dict[str, str]] = []
    for cells in grid[1:]:
        values = [cells.get(index, "") for index in range(width)]
        if not any(value.strip() for value in values):
            continue
        rows.append(dict(zip(header, values, strict=False)))

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=header)
    writer.writeheader()
    writer.writerows(rows)

    return {
        "columns": header,
        "rows": rows,
        "totalRows": len(rows),
        "csvText": buffer.getvalue(),
    }
