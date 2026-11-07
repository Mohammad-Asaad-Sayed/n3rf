from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

from app.errors import NodeError


@dataclass(frozen=True)
class Param:
    key: str
    type: str
    label: str
    default: Any = None
    options: list[str] | None = None
    unit: str | None = None
    required: bool = False
    show_if: dict[str, Any] | None = None
    columns: list[dict[str, Any]] | None = None
    hint: str | None = None
    expression: bool = False

    def public(self) -> dict[str, Any]:
        value = asdict(self)
        return {
            key: item
            for key, item in value.items()
            if item is not None or key in {"default", "required"}
        }


def resolve_show_if(specs: list[Param], values: dict[str, Any]) -> set[str]:
    visible: set[str] = set()
    defaults = {spec.key: spec.default for spec in specs}
    effective = {**defaults, **values}
    for spec in specs:
        condition = spec.show_if
        if not condition or effective.get(condition.get("param")) in condition.get("in", []):
            visible.add(spec.key)
    return visible


def _coerce(param: Param, value: Any) -> Any:
    if value is None:
        if param.required:
            raise NodeError(f"Parameter '{param.key}' is required.")
        return param.default
    try:
        if param.type in {"string", "textarea", "code", "file"}:
            result = str(value)
        elif param.type == "number":
            if isinstance(value, bool):
                raise ValueError
            number = float(value)
            result = int(number) if number.is_integer() else number
        elif param.type == "boolean":
            if isinstance(value, bool):
                result = value
            elif str(value).lower() in {"true", "1", "yes", "on"}:
                result = True
            elif str(value).lower() in {"false", "0", "no", "off"}:
                result = False
            else:
                raise ValueError
        elif param.type == "select":
            result = str(value)
            if param.options and result not in param.options:
                raise ValueError
        elif param.type == "json":
            result = json.loads(value) if isinstance(value, str) else value
        elif param.type == "rows":
            result = json.loads(value) if isinstance(value, str) else value
            if not isinstance(result, list) or any(not isinstance(row, dict) for row in result):
                raise ValueError
        else:
            raise NodeError(f"Unsupported parameter type '{param.type}' for '{param.key}'.")
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise NodeError(f"Parameter '{param.key}' has an invalid {param.type} value.") from exc
    if param.required and result in ("", None):
        raise NodeError(f"Parameter '{param.key}' is required.")
    return result


def validate_params(specs: list[Param], values: dict[str, Any]) -> dict[str, Any]:
    allowed = {spec.key for spec in specs}
    unknown = set(values) - allowed
    if unknown:
        names = ", ".join(sorted(unknown))
        raise NodeError(f"Unknown parameter(s): {names}.")
    result: dict[str, Any] = dict(values)
    visible = resolve_show_if(specs, values)
    for spec in specs:
        if spec.key not in visible:
            continue
        result[spec.key] = _coerce(spec, result.get(spec.key, spec.default))
    return result


@dataclass
class ParamSource:
    specs: list[Param] = field(default_factory=list)
