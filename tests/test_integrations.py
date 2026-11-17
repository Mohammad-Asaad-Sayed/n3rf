import asyncio
import json

import httpx
import pytest

from app.contracts import new_item
from app.engine import RunContext
from app.errors import NodeError
from app.nodes.slack import slack_add_reaction, slack_fetch_thread, slack_send_message
from app.nodes.supabase import supabase_rpc, supabase_select, supabase_upsert


def _install_httpx(monkeypatch, handler):
    original = httpx.AsyncClient

    def mocked_client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return original(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", mocked_client)


def _supabase_ctx(**overrides):
    base = {
        "url_env": "SUPABASE_URL",
        "api_key_env": "SUPABASE_API_KEY",
        "api_key": "",
        "url": "",
        "table": "decisions",
        "columns": "*",
        "filter": "",
        "limit": 50,
        "per_row": False,
        "on_conflict": "id",
        "function": "",
        "payload": {},
    }
    base.update(overrides)
    return RunContext(base)


def _slack_ctx(**overrides):
    base = {
        "token_env": "SLACK_BOT_TOKEN",
        "token": "",
        "api_url": "https://slack.com/api",
        "channel": "#general",
        "text": "",
        "thread_ts": "",
        "emoji": "eyes",
        "ts": "1700000000.000100",
        "limit": 50,
    }
    base.update(overrides)
    return RunContext(base)


# ── Supabase ──────────────────────────────────────────────────


def test_supabase_select_happy(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://demo.supabase.co")
    monkeypatch.setenv("SUPABASE_API_KEY", "service-key")
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        assert request.url.path == "/rest/v1/decisions"
        assert request.url.params["select"] == "id,path"
        assert request.url.params["kb_domain"] == "eq.launches"
        assert request.url.params["limit"] == "25"
        assert request.headers["apikey"] == "service-key"
        assert request.headers["Authorization"] == "Bearer service-key"
        return httpx.Response(
            200, json=[{"id": 1, "path": "answer"}, {"id": 2, "path": "escalate"}]
        )

    _install_httpx(monkeypatch, handler)
    out = asyncio.run(
        supabase_select(
            [new_item({"ignored": True})],
            _supabase_ctx(columns="id,path", filter="kb_domain=eq.launches", limit=25),
        )
    )
    assert [row["json"]["id"] for row in out] == [1, 2]
    assert out[0]["meta"]["supabase_table"] == "decisions"
    assert len(seen) == 1


def test_supabase_select_missing_env(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_API_KEY", raising=False)
    with pytest.raises(NodeError, match="SUPABASE_URL"):
        asyncio.run(supabase_select([], _supabase_ctx()))


def test_supabase_select_http_error(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://demo.supabase.co")
    monkeypatch.setenv("SUPABASE_API_KEY", "service-key")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"message": "column not found"})

    _install_httpx(monkeypatch, handler)
    with pytest.raises(NodeError, match="400"):
        asyncio.run(supabase_select([], _supabase_ctx()))


def test_supabase_select_rejects_private_url(monkeypatch):
    monkeypatch.setenv("SUPABASE_API_KEY", "service-key")
    with pytest.raises(NodeError):
        asyncio.run(supabase_select([], _supabase_ctx(url="http://127.0.0.1:54321")))


def test_supabase_upsert_happy(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://demo.supabase.co")
    monkeypatch.setenv("SUPABASE_API_KEY", "service-key")
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        assert request.url.path == "/rest/v1/decisions"
        assert request.url.params["on_conflict"] == "thread_id"
        assert "merge-duplicates" in request.headers["Prefer"]
        payload = json.loads(request.content)
        assert payload == [{"id": 1, "path": "answer"}, {"id": 2, "path": "ask"}]
        return httpx.Response(201, headers={"content-range": "0-1/2"})

    _install_httpx(monkeypatch, handler)
    items = [new_item({"id": 1, "path": "answer"}), new_item({"id": 2, "path": "ask"})]
    out = asyncio.run(supabase_upsert(items, _supabase_ctx(on_conflict="thread_id")))
    assert out[0]["meta"]["supabase_status"] == 201
    assert out[0]["json"] == {"id": 1, "path": "answer"}
    assert len(seen) == 1


def test_supabase_upsert_too_many_rows(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://demo.supabase.co")
    monkeypatch.setenv("SUPABASE_API_KEY", "service-key")
    items = [new_item({"id": i}) for i in range(1001)]
    with pytest.raises(NodeError, match="1000"):
        asyncio.run(supabase_upsert(items, _supabase_ctx()))


def test_supabase_rpc_happy_and_error(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://demo.supabase.co")
    monkeypatch.setenv("SUPABASE_API_KEY", "service-key")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/rpc/log_decision":
            return httpx.Response(200, json=[{"id": 7}, {"id": 8}])
        assert request.url.path == "/rpc/missing_fn"
        return httpx.Response(404, json={"message": "function not found"})

    _install_httpx(monkeypatch, handler)
    out = asyncio.run(supabase_rpc([], _supabase_ctx(function="log_decision", payload={"p": "x"})))
    assert [row["json"]["id"] for row in out] == [7, 8]

    _install_httpx(monkeypatch, handler)
    with pytest.raises(NodeError, match="404"):
        asyncio.run(supabase_rpc([], _supabase_ctx(function="missing_fn", payload={})))


def test_supabase_rpc_renders_templates_per_row(monkeypatch):
    """Dict payloads must render nested {{ }} per row — render() alone no-ops on non-str."""
    monkeypatch.setenv("SUPABASE_URL", "https://demo.supabase.co")
    monkeypatch.setenv("SUPABASE_API_KEY", "service-key")
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return httpx.Response(200, json={"ok": True})

    _install_httpx(monkeypatch, handler)
    items = [new_item({"path": "answer"}), new_item({"path": "escalate"})]
    asyncio.run(
        supabase_rpc(
            items,
            _supabase_ctx(
                function="log_decision",
                payload={"p_path": "{{path}}", "p_wrap": {"inner": "{{path}}"}},
            ),
        )
    )
    assert [b["p_path"] for b in seen] == ["answer", "escalate"]
    assert [b["p_wrap"]["inner"] for b in seen] == ["answer", "escalate"]


# ── Slack ─────────────────────────────────────────────────────


class FakeSlackClient:
    """Records calls and plays canned responses. Monkeypatched over AsyncWebClient."""

    instances: list = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.calls: list = []
        self.responses: dict[str, dict] = {}
        FakeSlackClient.instances.append(self)

    def respond(self, method, payload):
        self.responses[method] = payload

    async def chat_postMessage(self, **kwargs):
        self.calls.append(("chat_postMessage", kwargs))
        canned = self.responses.get("chat_postMessage")
        if canned is not None:
            return canned
        return {"ok": True, "channel": kwargs.get("channel"), "ts": "1700000001.000100"}

    async def reactions_add(self, **kwargs):
        self.calls.append(("reactions_add", kwargs))
        return self.responses.get("reactions_add", {"ok": True})

    async def conversations_replies(self, **kwargs):
        self.calls.append(("conversations_replies", kwargs))
        return self.responses.get(
            "conversations_replies",
            {
                "ok": True,
                "channel": kwargs.get("channel"),
                "messages": [
                    {
                        "text": "parent question",
                        "user": "U1",
                        "ts": "1700000000.000100",
                        "thread_ts": "1700000000.000100",
                        "reply_count": 2,
                    },
                    {
                        "text": "some context",
                        "user": "U2",
                        "ts": "1700000000.000200",
                        "thread_ts": "1700000000.000100",
                    },
                    {
                        "text": "another fact",
                        "user": "U3",
                        "ts": "1700000000.000300",
                        "thread_ts": "1700000000.000100",
                    },
                ],
            },
        )


def _install_slack(monkeypatch):
    FakeSlackClient.instances = []
    monkeypatch.setattr("app.nodes.slack.AsyncWebClient", FakeSlackClient)
    return FakeSlackClient


def test_slack_send_message_happy(monkeypatch):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test")
    cls = _install_slack(monkeypatch)

    out = asyncio.run(
        slack_send_message(
            [new_item({"thread_id": "abc"})],
            _slack_ctx(channel="#tech-problems", text="Routing — thread_abc", thread_ts="1.2"),
        )
    )
    client = cls.instances[0]
    assert client.kwargs == {"token": "xoxb-test", "base_url": "https://slack.com/api/"}
    assert client.calls == [
        (
            "chat_postMessage",
            {"channel": "#tech-problems", "text": "Routing — thread_abc", "thread_ts": "1.2"},
        )
    ]
    assert out[0]["json"]["slack_ts"] == "1700000001.000100"
    assert out[0]["json"]["slack_channel"] == "#tech-problems"


def test_slack_send_message_slack_error(monkeypatch):
    from slack_sdk.errors import SlackApiError

    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test")
    _install_slack(monkeypatch)

    class Boom(FakeSlackClient):
        async def chat_postMessage(self, **kwargs):
            class FakeResponse:
                data = {"ok": False, "error": "channel_not_found"}

                def get(self, key, default=None):
                    return self.data.get(key, default)

            raise SlackApiError("boom", FakeResponse())

    monkeypatch.setattr("app.nodes.slack.AsyncWebClient", Boom)
    with pytest.raises(NodeError, match="channel_not_found"):
        asyncio.run(slack_send_message([new_item({})], _slack_ctx(text="hi")))


def test_slack_missing_token(monkeypatch):
    monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
    _install_slack(monkeypatch)
    with pytest.raises(NodeError, match="SLACK_BOT_TOKEN"):
        asyncio.run(slack_send_message([], _slack_ctx(text="hi")))


def test_slack_add_reaction_happy(monkeypatch):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test")
    cls = _install_slack(monkeypatch)

    out = asyncio.run(
        slack_add_reaction(
            [new_item({})], _slack_ctx(channel="C123", ts="1.2", emoji="white_check_mark")
        )
    )
    client = cls.instances[0]
    assert client.calls == [
        ("reactions_add", {"channel": "C123", "timestamp": "1.2", "name": "white_check_mark"})
    ]
    assert out[0]["json"]["slack_reacted"] is True


def test_slack_response_not_a_dict(monkeypatch):
    """Real AsyncSlackResponse is NOT a dict — payload lives on .data.

    Guards against ``dict(response)`` regressions: the SDK response raises
    TypeError when treated as dict-iterable, which the fakes never surface.
    """

    class SDKLikeResponse:
        def __init__(self, data):
            self.data = data

    class SDKLikeClient(FakeSlackClient):
        async def chat_postMessage(self, **kwargs):
            self.calls.append(("chat_postMessage", kwargs))
            return SDKLikeResponse(
                {"ok": True, "channel": kwargs.get("channel"), "ts": "1700000001.000100"}
            )

    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test")
    monkeypatch.setattr("app.nodes.slack.AsyncWebClient", SDKLikeClient)

    out = asyncio.run(slack_send_message([new_item({})], _slack_ctx(channel="C123", text="hi")))
    assert out[0]["json"]["slack_ts"] == "1700000001.000100"
    assert out[0]["json"]["slack_channel"] == "C123"


def test_slack_fetch_thread_happy(monkeypatch):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test")
    cls = _install_slack(monkeypatch)

    out = asyncio.run(slack_fetch_thread([], _slack_ctx()))
    client = cls.instances[0]
    assert client.calls == [
        ("conversations_replies", {"channel": "#general", "ts": "1700000000.000100", "limit": 50})
    ]
    assert [row["json"]["text"] for row in out] == [
        "parent question",
        "some context",
        "another fact",
    ]
    assert out[0]["json"]["is_parent"] is True
    assert out[0]["json"]["reply_count"] == 2
    assert out[1]["json"]["is_parent"] is False
