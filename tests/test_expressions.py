"""T-009: expression security — nothing escapes the ast allowlist."""

import pytest

from app.expressions import ExpressionError, evaluate, render, render_deep

ROW = {"name": "Acme", "score": 5, "tags": [1, 2], "user": {"name": "Ada"}}


def test_happy_paths():
    assert evaluate("$json.score >= 4", ROW) is True
    assert evaluate("score >= 4", ROW) is True
    assert evaluate("user.name", ROW) == "Ada"
    assert evaluate("len(tags)", ROW) == 2
    assert evaluate("score + 1", ROW) == 6
    assert evaluate("active == true", {"active": True}) is True
    assert evaluate("score >= 4 and name == 'Acme'", ROW) is True
    assert evaluate("score >= 4 && name == 'Acme'", ROW) is True
    assert evaluate("score >= 4 & name == 'Acme'", ROW) is True
    assert evaluate("score >= 4 AND name == 'Acme'", ROW) is True
    assert evaluate("score < 4 or name == 'Acme'", ROW) is True
    assert evaluate("score < 4 || name == 'Acme'", ROW) is True
    assert evaluate("score < 4 | name == 'Acme'", ROW) is True
    assert evaluate("score < 4 OR name == 'Acme'", ROW) is True
    assert evaluate("name == 'Acme' and (score > 10 or score < 10)", ROW) is True
    # Coercion between string numbers/booleans and literals (CSV / form data)
    assert evaluate("score >= 5", {"score": "5"}) is True
    assert evaluate("score >= 4", {"score": "10"}) is True
    assert evaluate("score == 5", {"score": "5"}) is True
    assert evaluate("active == true", {"active": "true"}) is True
    assert evaluate("active == false", {"active": "false"}) is True
    # Embedded {{ }} from UI autocomplete in filter / if-else conditions
    assert evaluate("{{score}} >= 5", {"score": "10"}) is True
    assert (
        evaluate("{{score}} >= 5 and {{active}} == true", {"score": "10", "active": "true"}) is True
    )
    assert render("Hi {{name}}", ROW) == "Hi Acme"
    assert render("Hi {{ $json.name }}", ROW) == "Hi Acme"


def test_render_deep():
    payload = {
        "p_path": "{{name}}",
        "p_count": "{{score}}",
        "p_whole": "{{user.name}}",
        "p_tags": ["{{name}}", "static"],
        "p_nested": {"inner": "{{name}}", "keep": 3},
        "p_plain": "no template",
    }
    out = render_deep(payload, ROW)
    assert out["p_path"] == "Acme"
    assert out["p_count"] == 5  # whole-string template keeps the typed value
    assert out["p_whole"] == "Ada"
    assert out["p_tags"] == ["Acme", "static"]
    assert out["p_nested"] == {"inner": "Acme", "keep": 3}
    assert out["p_plain"] == "no template"
    # dict keys are never rendered
    assert render_deep({"{{name}}": 1}, ROW) == {"{{name}}": 1}
    # scalars pass through
    assert render_deep(5, ROW) == 5
    assert render_deep(None, ROW) is None


@pytest.mark.parametrize(
    "expression",
    [
        "import os",
        "__import__('os')",
        "os.system('ls')",
        "eval('1+1')",
        "exec('1')",
        "open('/etc/passwd')",
        "$json.__class__",
        "$json['__class__']",
        "$json.__dict__",
        "$json.__subclasses__()",
        "$json.__init__",
        "__class__",
        "a.b.c.__init__",
        "(lambda: 1)()",
        "lambda x: x",
        "[x for x in [1]]",
        "{x: 1 for x in [1]}",
        "json.items()",
        "eval",
        "open",
    ],
)
def test_security_escapes_raise(expression):
    with pytest.raises(ExpressionError):
        evaluate(expression, ROW)


def test_attribute_traversal_raises():
    with pytest.raises(ExpressionError):
        evaluate("name.upper", ROW)


def test_private_and_unknown_raise():
    with pytest.raises(ExpressionError):
        evaluate("_secret", ROW)
    with pytest.raises(ExpressionError):
        evaluate("missing_field", ROW)


def test_calls_only_allowlist():
    with pytest.raises(ExpressionError):
        evaluate("print('hi')", ROW)
    # curated functions work
    assert evaluate("lower('ABC')", {}) == "abc"
    assert evaluate("len([1, 2, 3])", {}) == 3
