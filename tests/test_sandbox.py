"""T-045: sandbox escapes — socket, file, shell, loop, memory, wrapper."""

import pytest

from app.contracts import new_item
from app.engine import RunContext
from app.errors import NodeError
from app.nodes.code import code_node
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


def test_sandbox_rejects_socket_open():
    with pytest.raises(NodeError):
        run_code("import socket\ns = socket.socket()\nreturn items", [])


def test_sandbox_rejects_file_write():
    with pytest.raises(NodeError):
        run_code("open('/tmp/n3rf-pwned', 'w').write('x')\nreturn items", [])


def test_sandbox_rejects_os_system():
    with pytest.raises(NodeError):
        run_code("import os\nos.system('echo hi')\nreturn items", [])


def test_sandbox_rejects_subprocess_and_ctypes():
    with pytest.raises(NodeError):
        run_code("import subprocess\nreturn items", [])
    with pytest.raises(NodeError):
        run_code("import ctypes\nreturn items", [])


def test_sandbox_enforces_wall_clock():
    with pytest.raises(NodeError, match="time limit"):
        run_code("while True:\n    pass", [], timeout=0.2)


def test_sandbox_memory_bomb_fails_cleanly():
    # 100M ints far exceeds RLIMIT_AS (256MB); must fail fast with NodeError.
    with pytest.raises(NodeError):
        run_code("x = [0] * 100000000\nreturn items", [], timeout=5)


def test_sandbox_allows_exception_builtins():
    with pytest.raises(NodeError, match="ValueError: boom"):
        run_code('raise ValueError("boom")', [])
    with pytest.raises(NodeError, match="KeyError"):
        run_code('raise KeyError("k")', [])


def test_code_node_wrapper_happy_empty_and_caps():
    # happy
    out = code_node(
        [new_item({"v": 1})],
        RunContext({"code": "return [{'json': {'v': 2}},]", "timeout": 3, "max_output_rows": 500}),
    )
    assert out[0]["json"] == {"v": 2}
    # empty input round-trips
    assert (
        code_node([], RunContext({"code": "return items", "timeout": 3, "max_output_rows": 500}))
        == []
    )
    # timeout bounds are validated
    with pytest.raises(NodeError, match="timeout"):
        code_node(
            [new_item({})],
            RunContext({"code": "return items", "timeout": 99, "max_output_rows": 500}),
        )
    # output cap enforced
    with pytest.raises(NodeError, match="max_output_rows"):
        code_node(
            [new_item({})],
            RunContext(
                {"code": "return [{'json': {}}, {'json': {}}]", "timeout": 3, "max_output_rows": 1}
            ),
        )
