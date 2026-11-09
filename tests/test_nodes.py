"""Per-node contract tests: happy path, empty input, one bad param."""

import asyncio
import base64

import httpx
import pytest

from app.contracts import new_item
from app.engine import RunContext, run_workflow
from app.errors import NodeError
from app.nodes.data import (
    aggregate,
    compare_datasets,
    dedupe,
    expand_arrays,
    filter_node,
    if_else,
    limit,
    merge,
    remove_fields,
    rename_fields,
    set_fields,
    sort_node,
)
from app.nodes.input import (
    csv_file,
    example_dataset,
    field_builder,
    file_upload,
    manual_json,
    spreadsheet_paste,
    text_lines,
)
from tests.mock_provider import install_mock_provider


def _ctx(**params):
    base = {
        "condition": "score >= 5",
        "output": "all_rows",
        "true_fields": [{"name": "branch", "value": "high"}],
        "false_fields": [{"name": "branch", "value": "low"}],
        "keep_empty": False,
    }
    base.update(params)
    return RunContext(base)


def test_if_else_applies_matching_branch_fields():
    rows = [new_item({"score": 8}), new_item({"score": 2})]
    out = if_else(rows, _ctx())
    assert [row["json"] for row in out] == [
        {"score": 8, "branch": "high"},
        {"score": 2, "branch": "low"},
    ]
    # meta stays in meta, never leaks into json
    assert all("branch" not in row["meta"] for row in out)
    assert all("meta" not in row["json"] for row in out)


def test_if_else_output_modes_filter_branches():
    rows = [new_item({"score": 8}), new_item({"score": 2})]
    true_out = if_else(rows, _ctx(output="true_only"))
    false_out = if_else(rows, _ctx(output="false_only"))
    assert [row["json"]["score"] for row in true_out] == [8]
    assert [row["json"]["score"] for row in false_out] == [2]


def test_if_else_renders_expressions_in_branch_values():
    rows = [new_item({"score": 9, "name": "Acme"})]
    out = if_else(
        rows,
        _ctx(true_fields=[{"name": "label", "value": "{{name}} high"}]),
    )
    assert out[0]["json"]["label"] == "Acme high"


def test_if_else_empty_input():
    assert if_else([], _ctx()) == []


def test_if_else_bad_field_raises():
    with pytest.raises(NodeError, match="name"):
        if_else([new_item({"score": 8})], _ctx(true_fields=[{"name": "", "value": "x"}]))


def test_if_else_via_engine_keeps_meta_separate():
    nodes = [
        {
            "id": "source",
            "type": "manual_json",
            "params": {"data": [{"score": 9}, {"score": 1}]},
        },
        {
            "id": "branch",
            "type": "if_else",
            "params": {
                "condition": "score >= 5",
                "output": "all_rows",
                "true_fields": [{"name": "tier", "value": "high"}],
                "false_fields": [{"name": "tier", "value": "low"}],
            },
        },
    ]
    result = asyncio.run(run_workflow(nodes, [{"source": "source", "target": "branch"}]))
    assert result["status"] == "success"
    assert result["output"] == [
        {"score": 9, "tier": "high"},
        {"score": 1, "tier": "low"},
    ]
    assert result["nodes"][1]["rows_in"] == 2
    assert result["nodes"][1]["rows_out"] == 2


def test_filter_still_behaves():
    rows = [new_item({"active": True}), new_item({"active": False})]
    out = filter_node(rows, RunContext({"condition": "active == true", "keep_empty": False}))
    assert [row["json"] for row in out] == [{"active": True}]
    assert filter_node([], RunContext({"condition": "active == true", "keep_empty": False})) == []


def test_filter_bad_condition_via_engine():
    nodes = [
        {"id": "a", "type": "manual_json", "params": {"data": [{"v": 1}]}},
        {"id": "f", "type": "filter", "params": {"condition": ""}},
    ]
    with pytest.raises(NodeError, match="condition"):
        asyncio.run(run_workflow(nodes, [{"source": "a", "target": "f"}]))


# --- input nodes: happy, empty-items, bad param ---


def test_manual_json_triple():
    assert [r["json"] for r in manual_json([], RunContext({"data": [{"a": 1}]}))] == [{"a": 1}]
    assert manual_json([], RunContext({"data": []})) == []
    with pytest.raises(NodeError, match="data"):
        manual_json([], RunContext({"data": "not-a-list"}))


def test_text_lines_triple():
    out = text_lines([], RunContext({"text": "Acme\nNorthstar", "delimiter": "line"}))
    assert [r["json"] for r in out] == [{"value": "Acme"}, {"value": "Northstar"}]
    assert text_lines([], RunContext({"text": "", "delimiter": "line"})) == []
    with pytest.raises((NodeError, KeyError)):
        text_lines([], RunContext({"text": "a,b", "delimiter": "bogus"}))


def test_csv_file_triple():
    out = csv_file([], RunContext({"text": "a,b\n1,2", "delimiter": ",", "header": True}))
    assert [r["json"] for r in out] == [{"a": "1", "b": "2"}]
    # File param support with base64 payload
    file_payload = base64.b64encode(b"col1,col2\nx,y").decode("ascii")
    file_out = csv_file([], RunContext({"file": file_payload, "delimiter": ",", "header": True}))
    assert [r["json"] for r in file_out] == [{"col1": "x", "col2": "y"}]
    assert csv_file([], RunContext({"text": "", "delimiter": ",", "header": True})) == []
    with pytest.raises(NodeError, match="delimiter"):
        csv_file([], RunContext({"text": "a", "delimiter": "..", "header": True}))


def test_spreadsheet_paste_triple():
    out = spreadsheet_paste([], RunContext({"text": "a\tb\n1\t2", "header": True}))
    assert [r["json"] for r in out] == [{"a": "1", "b": "2"}]
    assert spreadsheet_paste([], RunContext({"text": "", "header": True})) == []
    # empty header still parses without crashing
    assert spreadsheet_paste([], RunContext({"text": "1\t2\n3\t4", "header": False})) != []


def test_field_builder_triple():
    out = field_builder(
        [], RunContext({"fields": [{"name": "company", "type": "string", "value": "Acme"}]})
    )
    assert out[0]["json"] == {"company": "Acme"}
    # empty fields still yields one (empty) row by design
    assert field_builder([], RunContext({"fields": []})) == [new_item({})]
    with pytest.raises(NodeError, match="name"):
        field_builder([], RunContext({"fields": [{"name": "", "type": "string", "value": "x"}]}))


def test_example_dataset_triple():
    out = example_dataset([], RunContext({"dataset": "companies", "rows": 2}))
    assert len(out) == 2
    assert example_dataset([], RunContext({"dataset": "companies", "rows": 0})) == []
    with pytest.raises(NodeError, match="rows"):
        example_dataset([], RunContext({"dataset": "companies", "rows": 99999}))


def test_file_upload_triple():
    payload = base64.b64encode(b"a,b\n1,2").decode()
    out = file_upload([], RunContext({"content": payload, "encoding": "csv", "filename": "x.csv"}))
    assert [r["json"] for r in out] == [{"a": "1", "b": "2"}]
    # Auto-detection from filename
    auto_out = file_upload(
        [], RunContext({"content": payload, "encoding": "auto", "filename": "data.csv"})
    )
    assert [r["json"] for r in auto_out] == [{"a": "1", "b": "2"}]
    assert (
        file_upload(
            [],
            RunContext(
                {"content": base64.b64encode(b"").decode(), "encoding": "csv", "filename": "x.csv"}
            ),
        )
        == []
    )
    with pytest.raises(NodeError, match="content"):
        file_upload(
            [], RunContext({"content": "!!!not-base64!!!", "encoding": "text", "filename": "x.txt"})
        )


# --- transform nodes: happy, empty, bad ---


def test_sort_limit_set_remove_rename_triples():
    rows = [new_item({"v": 2}), new_item({"v": 1})]
    assert [
        r["json"]["v"]
        for r in sort_node(rows, RunContext({"field": "v", "direction": "asc", "numeric": True}))
    ] == [1, 2]
    assert sort_node([], RunContext({"field": "v"})) == []
    with pytest.raises(NodeError, match="field"):
        sort_node(rows, RunContext({}))
    assert [
        r["json"]["v"]
        for r in limit(
            [new_item({"v": 1}), new_item({"v": 2})], RunContext({"max": 1, "offset": 0})
        )
    ] == [1]
    assert limit([], RunContext({"max": 1, "offset": 0})) == []
    with pytest.raises(NodeError):
        limit([], RunContext({"max": -1, "offset": 0}))
    # set / remove / rename
    assert set_fields([new_item({"a": 1})], RunContext({"fields": [{"name": "b", "value": "x"}]}))[
        0
    ]["json"] == {"a": 1, "b": "x"}
    assert set_fields([], RunContext({"fields": []})) == []
    with pytest.raises(NodeError, match="name"):
        set_fields([new_item({})], RunContext({"fields": [{"name": "", "value": "x"}]}))
    assert remove_fields([new_item({"a": 1, "b": 2})], RunContext({"fields": "b"}))[0]["json"] == {
        "a": 1
    }
    assert remove_fields([], RunContext({"fields": "b"})) == []
    with pytest.raises(NodeError):
        remove_fields([new_item({})], RunContext({"fields": ""}))
    assert rename_fields([new_item({"a": 1})], RunContext({"fields": [{"from": "a", "to": "b"}]}))[
        0
    ]["json"] == {"b": 1}
    assert rename_fields([], RunContext({"fields": []})) == []


def test_aggregate_expand_dedupe_triples():
    rows = [new_item({"g": "x", "v": 1}), new_item({"g": "x", "v": 3})]
    out = aggregate(
        rows, RunContext({"group_by": "g", "fields": [{"field": "v", "op": "sum", "as": "total"}]})
    )
    assert out[0]["json"] == {"g": "x", "total": 4.0}
    assert aggregate([], RunContext({"group_by": "g", "fields": []})) == []
    with pytest.raises(NodeError):
        aggregate(
            rows,
            RunContext({"group_by": "g", "fields": [{"field": "v", "op": "bogus", "as": "x"}]}),
        )
    assert [
        r["json"]["t"]
        for r in expand_arrays(
            [new_item({"t": [1, 2]})], RunContext({"field": "t", "max_output_rows": 500})
        )
    ] == [1, 2]
    assert expand_arrays([], RunContext({"field": "t", "max_output_rows": 500})) == []
    with pytest.raises(NodeError):
        expand_arrays([new_item({"t": 1})], RunContext({"field": "t", "max_output_rows": 500}))
    assert [
        r["json"]["c"]
        for r in dedupe(
            [new_item({"c": "A"}), new_item({"c": "A"})],
            RunContext({"field": "c", "keep": "first"}),
        )
    ] == ["A"]
    assert dedupe([], RunContext({"field": "c", "keep": "first"})) == []
    with pytest.raises(NodeError, match="field"):
        dedupe([new_item({})], RunContext({"field": "", "keep": "first"}))


def test_merge_compare_triples():
    left = [new_item({"k": "A"})]
    right = [new_item({"k": "B"})]
    ctx = RunContext({"mode": "append"})
    ctx.inputs = [left, right]
    assert len(merge(left, ctx)) == 2
    ctx_empty = RunContext({"mode": "append"})
    ctx_empty.inputs = [[], []]
    assert merge([], ctx_empty) == []
    ctx_bad = RunContext({"mode": "merge_by_key", "key": ""})
    ctx_bad.inputs = [left, right]
    with pytest.raises(NodeError, match="key"):
        merge(left, ctx_bad)
    cl = RunContext({"key": "k", "mode": "inner"})
    cl.inputs = [[new_item({"k": "A"}), new_item({"k": "B"})], [new_item({"k": "A"})]]
    assert len(compare_datasets(cl.inputs[0], cl)) == 1
    cl_empty = RunContext({"key": "k", "mode": "inner"})
    cl_empty.inputs = [[], []]
    assert compare_datasets([], cl_empty) == []
    cl_bad = RunContext({"key": "", "mode": "inner"})
    cl_bad.inputs = [[], []]
    with pytest.raises(NodeError, match="key"):
        compare_datasets([], cl_bad)


# --- http_request happy/empty/bad (mocked) ---


def _install_httpx(monkeypatch, handler):
    original = httpx.AsyncClient

    def mocked_client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return original(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", mocked_client)


def test_http_request_triple(monkeypatch):
    from app.nodes.http import http_request

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True})

    _install_httpx(monkeypatch, handler)
    ctx = RunContext(
        {
            "method": "GET",
            "url": "https://example.com/{{company}}",
            "headers": {},
            "body": {},
            "per_row": True,
        }
    )
    out = asyncio.run(http_request([new_item({"company": "acme"})], ctx))
    assert out[0]["json"] == {"response": {"ok": True}, "status_code": 200}
    # per_row=False with empty items still issues one call to a blank target
    ctx_once = RunContext(
        {
            "method": "GET",
            "url": "https://example.com/static",
            "headers": {},
            "body": {},
            "per_row": False,
        }
    )
    out_once = asyncio.run(http_request([], ctx_once))
    assert out_once[0]["json"]["status_code"] == 200
    with pytest.raises(NodeError, match="secret"):
        asyncio.run(
            http_request(
                [new_item({})],
                RunContext(
                    {
                        "method": "GET",
                        "url": "https://example.com",
                        "headers": {"Authorization": "Bearer x"},
                        "body": {},
                        "per_row": True,
                    }
                ),
            )
        )


# --- AI nodes (mocked) ---


def _ai_ctx(monkeypatch, replies, **over):
    install_mock_provider(monkeypatch, replies)
    base = {
        "provider": "custom",
        "base_url": "https://provider.invalid/v1",
        "api_key_env": "",
        "model": "test-model",
        "prompt": "Hi",
        "schema": {},
        "concurrency": 1,
        "max_output_rows": 10,
        "on_error": "fail",
        "mode": "per_input",
        "criterion": "good",
        "top_n": 10,
        "score_field": "score",
        "field": "text",
        "threshold": 0.9,
        "embedding_model": "emb",
    }
    base.update(over)
    return RunContext(base)


def test_ai_filter_triple(monkeypatch):
    from app.nodes.ai import ai_filter

    ctx = _ai_ctx(monkeypatch, [{"keep": True}, {"keep": False}])
    rows = [new_item({"t": "a"}), new_item({"t": "b"})]
    out = asyncio.run(ai_filter(rows, ctx))
    assert [r["json"]["t"] for r in out] == ["a"]
    assert asyncio.run(ai_filter([], _ai_ctx(monkeypatch, []))) == []
    # bad: empty criterion raises via required path
    ctx_bad = _ai_ctx(monkeypatch, [{"keep": True}], criterion="")
    with pytest.raises(NodeError):
        asyncio.run(ai_filter([new_item({"t": "a"})], ctx_bad))


def test_ai_ranker_triple(monkeypatch):
    from app.nodes.ai import ai_ranker

    ctx = _ai_ctx(monkeypatch, [{"score": 0.2}, {"score": 0.9}])
    out = asyncio.run(ai_ranker([new_item({"t": "a"}), new_item({"t": "b"})], ctx))
    assert out[0]["json"]["score"] == 0.9
    assert asyncio.run(ai_ranker([], _ai_ctx(monkeypatch, []))) == []
    # bad: non-numeric score
    with pytest.raises(NodeError):
        asyncio.run(ai_ranker([new_item({"t": "a"})], _ai_ctx(monkeypatch, [{"score": "high"}])))


def test_semantic_dedup_triple(monkeypatch):
    from app.nodes.ai import semantic_dedup

    vectors = iter([[1.0, 0.0], [1.0, 0.0], [0.0, 1.0]])

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url).endswith("/embeddings"):
            return httpx.Response(
                200,
                json={"data": [{"embedding": next(vectors)}], "usage": {"prompt_tokens": 2}},
            )
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": '{"keep": true}'}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            },
        )

    _install_httpx(monkeypatch, handler)
    base = {
        "provider": "custom",
        "base_url": "https://provider.invalid/v1",
        "api_key_env": "",
        "model": "test-model",
        "prompt": "Hi",
        "field": "text",
        "threshold": 0.9,
        "embedding_model": "emb",
        "concurrency": 1,
        "max_output_rows": 10,
        "on_error": "fail",
    }
    rows = [new_item({"text": "same"}), new_item({"text": "same"}), new_item({"text": "diff"})]
    out = asyncio.run(semantic_dedup(rows, RunContext(base)))
    assert len(out) == 2
    assert asyncio.run(semantic_dedup([], RunContext(base))) == []
    with pytest.raises(NodeError, match="threshold"):
        asyncio.run(semantic_dedup(rows, RunContext({**base, "threshold": 2})))


def test_exa_search_triple(monkeypatch):
    from app.nodes.enrichment import exa_search

    monkeypatch.setenv("EXA_API_KEY", "k")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"results": [{"title": "T", "url": "https://e.com"}]})

    _install_httpx(monkeypatch, handler)
    ctx = RunContext(
        {
            "query": "{{company}}",
            "api_key_env": "EXA_API_KEY",
            "num_results": 2,
            "type": "auto",
            "include_text": False,
            "concurrency": 1,
            "max_output_rows": 10,
            "on_error": "fail",
        }
    )
    assert (
        asyncio.run(exa_search([new_item({"company": "Acme"})], ctx))[0]["json"]["exa_results"][0][
            "title"
        ]
        == "T"
    )
    assert asyncio.run(exa_search([], ctx)) == []
    with pytest.raises(NodeError):
        asyncio.run(
            exa_search(
                [new_item({"company": "Acme"})], RunContext({**ctx.params, "num_results": 99})
            )
        )


def test_tavily_extract_and_jina_bad_url(monkeypatch):
    from app.nodes.enrichment import jina_reader, tavily_extract

    monkeypatch.setenv("TAVILY_API_KEY", "k")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"results": [{"raw_content": "# Hi"}]})

    _install_httpx(monkeypatch, handler)
    ctx = RunContext(
        {
            "url": "{{website}}",
            "api_key_env": "TAVILY_API_KEY",
            "extract_depth": "basic",
            "format": "markdown",
            "concurrency": 1,
            "max_output_rows": 10,
            "on_error": "fail",
        }
    )
    assert (
        asyncio.run(tavily_extract([new_item({"website": "https://e.com"})], ctx))[0]["json"][
            "tavily_content"
        ]
        == "# Hi"
    )
    assert asyncio.run(tavily_extract([], ctx)) == []
    with pytest.raises(NodeError):
        asyncio.run(tavily_extract([new_item({"website": "not-a-url"})], ctx))
    with pytest.raises(NodeError):
        asyncio.run(
            jina_reader(
                [new_item({"website": "nope"})],
                RunContext(
                    {
                        "url": "{{website}}",
                        "api_key_env": "",
                        "format": "markdown",
                        "concurrency": 1,
                        "max_output_rows": 10,
                        "on_error": "fail",
                    }
                ),
            )
        )
