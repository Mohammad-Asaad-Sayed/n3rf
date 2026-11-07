import pytest

from app.errors import NodeError
from app.sandbox import run_code


def test_sandbox_transforms_rows():
    rows = [{"json": {"value": 2}, "meta": {}}]
    result = run_code(
        "return [{**row, 'json': {**row['json'], "
        "'value': row['json']['value'] + 1}} for row in items]",
        rows,
    )
    assert result[0]["json"]["value"] == 3


def test_sandbox_can_import_allowlisted_modules():
    assert (
        run_code("import math\nreturn [{'json': {'value': math.sqrt(9)}}]", [])[0]["json"]["value"]
        == 3
    )


def test_sandbox_rejects_network_import():
    with pytest.raises(NodeError):
        run_code("import socket\nreturn items", [])


def test_sandbox_enforces_wall_clock():
    with pytest.raises(NodeError, match="time limit"):
        run_code("while True:\n    pass", [], timeout=0.2)
