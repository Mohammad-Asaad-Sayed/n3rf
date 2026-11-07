from __future__ import annotations

import json
import subprocess
import sys
from typing import Any

from app.errors import NodeError

_BOOTSTRAP = r"""
import json, sys, math, statistics, re, datetime, collections
try:
    import resource
    resource.setrlimit(resource.RLIMIT_CPU, (2, 2))
    resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024, 256 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_NPROC, (0, 0))
except (ImportError, AttributeError, ValueError):
    pass
payload = json.loads(sys.stdin.read())
def audit(event, args):
    if event.startswith(("socket.", "subprocess.", "ctypes.")) or event in {
        "open", "os.system", "os.spawn", "os.exec", "os.putenv", "os.unsetenv"
    }:
        raise PermissionError("sandbox blocked " + event)
sys.addaudithook(audit)
allowed = {"abs": abs, "all": all, "any": any, "bool": bool, "dict": dict,
           "enumerate": enumerate, "float": float, "int": int, "len": len,
           "list": list, "max": max, "min": min, "range": range, "round": round,
           "sorted": sorted, "str": str, "sum": sum, "zip": zip, "True": True,
           "False": False, "None": None}
def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
    if name not in {"json", "math", "statistics", "re", "datetime", "collections"}:
        raise ImportError("sandbox blocked import: " + name)
    return __import__(name, globals, locals, fromlist, level)
allowed["__import__"] = safe_import
scope = {"__builtins__": allowed}
function_source = "def transform(items):\n" + "\n".join(
    "    " + line for line in payload["code"].splitlines()
)
exec(function_source, scope)
result = scope["transform"](payload["items"])
if not isinstance(result, list):
    raise TypeError("Code node must return a list.")
sys.stdout.write(json.dumps(result))
"""


def run_code(code: str, items: list[dict[str, Any]], timeout: float = 3.0) -> list[dict[str, Any]]:
    try:
        completed = subprocess.run(
            [sys.executable, "-I", "-S", "-c", _BOOTSTRAP],
            input=json.dumps({"code": code, "items": items}),
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise NodeError(f"Code node exceeded its {timeout:g}s time limit.") from exc
    if completed.returncode:
        message = completed.stderr.strip().splitlines()
        raise NodeError(message[-1] if message else "Code node failed in the sandbox.")
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise NodeError("Code node returned invalid JSON.") from exc
    if not isinstance(result, list) or any(not isinstance(row, dict) for row in result):
        raise NodeError("Code node must return a list of row objects.")
    return result
