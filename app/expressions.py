from __future__ import annotations

import ast
import json
import operator
import re
from typing import Any

from app.contracts import to_snake_case


class ExpressionError(ValueError):
    pass


def _lookup_field_path(row: dict[str, Any], source: str) -> tuple[bool, Any]:
    """Fallback lookup for names Python can't parse (spaces/hyphens).

    Handles "Company Name" and "User Name.First Name" by exact match first,
    then snake_case-normalized match.
    """
    parts = [part.strip() for part in source.split(".")]
    current: Any = row
    for part in parts:
        if not isinstance(current, dict):
            return False, None
        if part in current:
            current = current[part]
            continue
        wanted = to_snake_case(part)
        match_key = next(
            (key for key in current if isinstance(key, str) and to_snake_case(key) == wanted),
            None,
        )
        if match_key is None:
            return False, None
        current = current[match_key]
    return True, _safe(current)


def _safe(value: Any) -> Any:
    if isinstance(value, dict):
        return _SafeDict(value)
    if isinstance(value, (list, tuple)):
        return [_safe(item) for item in value]
    return value


class _SafeDict(dict):
    def __getattr__(self, name: str) -> Any:
        if name.startswith("_") or name not in self:
            raise ExpressionError(f"Unknown field '{name}'.")
        return _safe(self[name])

    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, str) and key.startswith("_"):
            raise ExpressionError("Private attributes are not available in expressions.")
        return _safe(super().__getitem__(key))


_BINARY = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
}
_COMPARE = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.In: lambda left, right: left in right,
    ast.NotIn: lambda left, right: left not in right,
}
_FUNCTIONS = {
    "len": len,
    "trim": lambda value: str(value).strip(),
    "lower": lambda value: str(value).lower(),
    "upper": lambda value: str(value).upper(),
    "json_dumps": lambda value: json.dumps(value, ensure_ascii=False),
    "coalesce": lambda *values: next((value for value in values if value is not None), None),
    "re_match": lambda pattern, text: bool(re.search(str(pattern), str(text))),
    "str": str,
    "int": int,
    "float": float,
}


def _compare_op(op_type: type, left: Any, right: Any) -> bool:
    if op_type in (ast.Eq, ast.NotEq):
        is_eq = False
        if left == right:
            is_eq = True
        else:
            if isinstance(left, str) and isinstance(right, (int, float)):
                try:
                    is_eq = float(left) == float(right)
                except ValueError:
                    pass
            elif isinstance(right, str) and isinstance(left, (int, float)):
                try:
                    is_eq = float(left) == float(right)
                except ValueError:
                    pass
            if isinstance(left, str) and isinstance(right, bool):
                low = left.strip().lower()
                if low in ("true", "1"):
                    is_eq = right is True
                elif low in ("false", "0"):
                    is_eq = right is False
            elif isinstance(right, str) and isinstance(left, bool):
                low = right.strip().lower()
                if low in ("true", "1"):
                    is_eq = left is True
                elif low in ("false", "0"):
                    is_eq = left is False
        return is_eq if op_type is ast.Eq else not is_eq

    op_fn = _COMPARE.get(op_type)
    if not op_fn:
        return False
    try:
        return op_fn(left, right)
    except TypeError:
        if isinstance(left, str) and isinstance(right, (int, float)):
            try:
                return op_fn(float(left), right)
            except ValueError:
                pass
        elif isinstance(right, str) and isinstance(left, (int, float)):
            try:
                return op_fn(left, float(right))
            except ValueError:
                pass
        try:
            return op_fn(str(left), str(right))
        except Exception:
            return False


def _walk(expr: ast.AST, env: dict[str, Any]) -> Any:
    if isinstance(expr, ast.Constant):
        return expr.value
    if isinstance(expr, ast.Name):
        if expr.id.startswith("_"):
            raise ExpressionError(f"Unknown name '{expr.id}'.")
        if expr.id not in env:
            # JSON-style literals users type in conditions: true / false / null.
            # Row fields win when present, so a column named "true" still resolves.
            if expr.id == "true":
                return True
            if expr.id == "false":
                return False
            if expr.id in {"null", "none"}:
                return None
            raise ExpressionError(f"Unknown field '{expr.id}'.")
        return env[expr.id]
    if isinstance(expr, ast.Attribute):
        if expr.attr.startswith("_"):
            raise ExpressionError("Private attributes are not available in expressions.")
        target = _walk(expr.value, env)
        if not isinstance(target, _SafeDict):
            raise ExpressionError("Only row fields can be accessed by name.")
        return getattr(target, expr.attr)
    if isinstance(expr, ast.Subscript):
        return _safe(_walk(expr.value, env)[_walk(expr.slice, env)])
    if isinstance(expr, ast.List):
        return [_walk(item, env) for item in expr.elts]
    if isinstance(expr, ast.Tuple):
        return tuple(_walk(item, env) for item in expr.elts)
    if isinstance(expr, ast.Dict):
        return {_walk(k, env): _walk(v, env) for k, v in zip(expr.keys, expr.values, strict=True)}
    if isinstance(expr, ast.BinOp) and type(expr.op) in _BINARY:
        return _BINARY[type(expr.op)](_walk(expr.left, env), _walk(expr.right, env))
    if isinstance(expr, ast.UnaryOp) and isinstance(expr.op, (ast.Not, ast.USub, ast.UAdd)):
        value = _walk(expr.operand, env)
        return (
            not value
            if isinstance(expr.op, ast.Not)
            else (-value if isinstance(expr.op, ast.USub) else +value)
        )
    if isinstance(expr, ast.BoolOp):
        if isinstance(expr.op, ast.And):
            return all(_walk(item, env) for item in expr.values)
        if isinstance(expr.op, ast.Or):
            return any(_walk(item, env) for item in expr.values)
    if isinstance(expr, ast.Compare):
        left = _walk(expr.left, env)
        for op, comparator in zip(expr.ops, expr.comparators, strict=True):
            right = _walk(comparator, env)
            if not _compare_op(type(op), left, right):
                return False
            left = right
        return True
    if isinstance(expr, ast.IfExp):
        return _walk(expr.body if _walk(expr.test, env) else expr.orelse, env)
    if (
        isinstance(expr, ast.Call)
        and isinstance(expr.func, ast.Name)
        and expr.func.id in _FUNCTIONS
    ):
        return _FUNCTIONS[expr.func.id](*[_walk(arg, env) for arg in expr.args])
    raise ExpressionError(f"Unsupported expression: {type(expr).__name__}.")


_LOGICAL_OPS_RE = re.compile(r"(\"[^\"]*\"|'[^']*')|(&&|&|\|\||\||\bAND\b|\bOR\b)")


def _normalize_logical_ops(source: str) -> str:
    def _replace(match: re.Match[str]) -> str:
        if match.group(1):
            return match.group(1)
        op = match.group(2)
        if op in ("&&", "&", "AND"):
            return " and "
        if op in ("||", "|", "OR"):
            return " or "
        return op

    return _LOGICAL_OPS_RE.sub(_replace, source)


def evaluate(expression: str, row: dict[str, Any]) -> Any:
    source = expression.strip()
    source = re.sub(r"\{\{\s*(.*?)\s*\}\}", r"\1", source)
    source = source.replace("$json", "json").replace("$item", "item")
    source = _normalize_logical_ops(source)
    # Bare snake_case names resolve to row fields: {{company}} == {{ $json.company }}.
    # Row fields win over helper functions for a bare name; `json`/`item` stay reserved
    # so the legacy $json form keeps working untouched.
    # snake_case aliases let {{company_name}} match a spaced header like
    # "Company Name" without renaming columns.
    safe_row = _safe(row)
    row_env: dict[str, Any] = {}
    for key, value in row.items():
        if not isinstance(key, str) or key.startswith("_"):
            continue
        safe_value = _safe(value)
        row_env[key] = safe_value
        normalized = to_snake_case(key)
        if normalized and normalized not in row_env:
            row_env[normalized] = safe_value
    env: dict[str, Any] = {**_FUNCTIONS, **row_env, "json": safe_row, "item": safe_row}
    try:
        parsed = ast.parse(source, mode="eval")
        return _walk(parsed.body, env)
    except ExpressionError as exc:
        # Unknown field on a plain path: try the spaced/bracket-free lookup
        # before surfacing the error (covers "Company Name").
        if "Unknown field" in str(exc):
            found, value = _lookup_field_path(row, source)
            if found:
                return value
        raise
    except Exception as exc:
        # Syntax errors (e.g. "Company Name") still resolve as field names.
        found, value = _lookup_field_path(row, source)
        if found:
            return value
        raise ExpressionError(str(exc)) from exc


_TEMPLATE = re.compile(r"\{\{\s*(.*?)\s*\}\}")


def render(template: Any, row: dict[str, Any]) -> Any:
    if not isinstance(template, str):
        return template
    matches = list(_TEMPLATE.finditer(template))
    if len(matches) == 1 and matches[0].span() == (0, len(template)):
        return evaluate(matches[0].group(1), row)
    return _TEMPLATE.sub(lambda match: str(evaluate(match.group(1), row)), template)
