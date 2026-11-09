"""T-007: registry rules — duplicate ids, idempotent load, catalog shape."""

import pytest

from app.registry import REGISTRY, load_all, node


def test_duplicate_id_rejected():
    load_all()  # populate registry first so "filter" exists
    with pytest.raises(ValueError, match="already registered"):

        @node("filter", "Dup", group="transform", description="dup")
        def dup_node(items, ctx):  # pragma: no cover
            return items


def test_load_all_is_idempotent():
    first = load_all()
    second = load_all()
    assert first is second
    assert len(first) == 30
    assert load_all() == first


def test_every_node_has_group_description_and_params():
    catalog = load_all()
    assert catalog
    for spec in catalog.values():
        assert spec.group, spec.id
        assert spec.description.strip(), spec.id
        assert spec.name.strip(), spec.id
        for param in spec.params:
            assert param.type, f"{spec.id}:{param.key}"
            assert param.label, f"{spec.id}:{param.key}"
            public = param.public()
            assert public["key"] == param.key
            assert public["label"] == param.label


def test_groups_are_known():
    groups = {spec.group for spec in load_all().values()}
    assert groups == {"input", "transform", "search", "ai", "code"}


def test_registry_is_module_level_dict():
    assert isinstance(REGISTRY, dict)
    assert load_all() is REGISTRY
