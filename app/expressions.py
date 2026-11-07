from __future__ import annotations

import ast
import json
import operator
import re
from typing import Any


class ExpressionError(ValueError):
    pass


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


def _walk(expr: ast.AST, env: dict[str, Any]) -> Any:
    if isinstance(expr, ast.Constant):
        return expr.value
    if isinstance(expr, ast.Name):
        if expr.id not in env:
            raise ExpressionError(f"Unknown name '{expr.id}'.")
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
        values = [_walk(item, env) for item in expr.values]
        if isinstance(expr.op, ast.And):
            return all(values)
        if isinstance(expr.op, ast.Or):
            return any(values)
    if isinstance(expr, ast.Compare):
        left = _walk(expr.left, env)
        for op, comparator in zip(expr.ops, expr.comparators, strict=True):
            right = _walk(comparator, env)
            if type(op) not in _COMPARE or not _COMPARE[type(op)](left, right):
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


def evaluate(expression: str, row: dict[str, Any]) -> Any:
    source = expression.strip()
    if source.startswith("{{") and source.endswith("}}"):
        source = source[2:-2].strip()
    source = source.replace("$json", "json").replace("$item", "item")
    try:
        parsed = ast.parse(source, mode="eval")
        return _walk(parsed.body, {"json": _safe(row), "item": _safe(row), **_FUNCTIONS})
    except ExpressionError:
        raise
    except Exception as exc:
        raise ExpressionError(str(exc)) from exc


_TEMPLATE = re.compile(r"\{\{\s*(.*?)\s*\}\}")


def render(template: Any, row: dict[str, Any]) -> Any:
    if not isinstance(template, str):
        return template
    matches = list(_TEMPLATE.finditer(template))
    if len(matches) == 1 and matches[0].span() == (0, len(template)):
        return evaluate(matches[0].group(1), row)
    return _TEMPLATE.sub(lambda match: str(evaluate(match.group(1), row)), template)
