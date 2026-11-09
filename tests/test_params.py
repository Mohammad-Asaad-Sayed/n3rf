"""T-005: param coercion matrix, required, json/rows failures, show_if."""

import pytest

from app.errors import NodeError
from app.params import Param, resolve_show_if, validate_params


def test_coercion_for_every_type():
    specs = [
        Param("s", "string", "S"),
        Param("t", "textarea", "T"),
        Param("c", "code", "C"),
        Param("f", "file", "F"),
        Param("n", "number", "N"),
        Param("b", "boolean", "B"),
        Param("sel", "select", "Sel", options=["a", "b"]),
        Param("j", "json", "J"),
        Param("r", "rows", "R"),
    ]
    out = validate_params(
        specs,
        {
            "s": "x",
            "t": "hi",
            "c": "x=1",
            "f": "abc",
            "n": "3.5",
            "b": "yes",
            "sel": "a",
            "j": '{"k": 1}',
            "r": '[{"a": 1}]',
        },
    )
    assert out["s"] == "x"
    assert out["n"] == 3.5
    assert out["b"] is True
    assert out["j"] == {"k": 1}
    assert out["r"] == [{"a": 1}]
    # integer-valued numbers stay ints
    assert validate_params(specs, {"n": "5"})["n"] == 5


def test_number_rejects_bool_and_text():
    specs = [Param("n", "number", "N")]
    with pytest.raises(NodeError, match="n"):
        validate_params(specs, {"n": True})
    with pytest.raises(NodeError, match="n"):
        validate_params(specs, {"n": "not-a-number"})


def test_boolean_accepts_common_spellings():
    specs = [Param("b", "boolean", "B")]
    for raw, expected in [
        (True, True),
        ("true", True),
        ("On", True),
        ("1", True),
        (False, False),
        ("off", False),
        ("0", False),
        ("No", False),
    ]:
        assert validate_params(specs, {"b": raw})["b"] is expected
    with pytest.raises(NodeError, match="b"):
        validate_params(specs, {"b": "maybe"})


def test_required_rejects_missing_and_empty():
    specs = [Param("req", "string", "Req", required=True)]
    with pytest.raises(NodeError, match="req"):
        validate_params(specs, {})
    with pytest.raises(NodeError, match="req"):
        validate_params(specs, {"req": ""})


def test_json_and_rows_parse_failures_name_the_field():
    specs = [
        Param("j", "json", "J"),
        Param("r", "rows", "R"),
    ]
    with pytest.raises(NodeError, match="j"):
        validate_params(specs, {"j": "not json{"})
    with pytest.raises(NodeError, match="r"):
        validate_params(specs, {"r": "[1,2]"})
    with pytest.raises(NodeError, match="r"):
        validate_params(specs, {"r": '{"a": 1}'})


def test_select_rejects_unknown_option():
    specs = [Param("sel", "select", "Sel", options=["a", "b"])]
    with pytest.raises(NodeError, match="sel"):
        validate_params(specs, {"sel": "z"})


def test_show_if_toggles_visibility_for_validation():
    specs = [
        Param("mode", "select", "Mode", default="off", options=["off", "on"]),
        Param(
            "limit",
            "number",
            "Limit",
            default=10,
            show_if={"param": "mode", "in": ["on"]},
        ),
    ]
    assert resolve_show_if(specs, {"mode": "on"}) == {"mode", "limit"}
    assert resolve_show_if(specs, {"mode": "off"}) == {"mode"}
    # hidden param keeps its default without coercion errors
    out = validate_params(specs, {"mode": "off", "limit": "not-a-number"})
    assert out["mode"] == "off"
    assert out["limit"] == "not-a-number"  # untouched, hidden
    # visible param is coerced and errors name the field
    assert validate_params(specs, {"mode": "on", "limit": "5"})["limit"] == 5
    with pytest.raises(NodeError, match="limit"):
        validate_params(specs, {"mode": "on", "limit": "xx"})


def test_unknown_param_rejected():
    specs = [Param("a", "string", "A")]
    with pytest.raises(NodeError, match="bogus"):
        validate_params(specs, {"bogus": 1})
