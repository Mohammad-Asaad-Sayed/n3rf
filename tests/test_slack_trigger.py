import hashlib
import hmac
import json
import time

from fastapi.testclient import TestClient

import app.slack_trigger as trigger
from app.main import create_app


def _signed_headers(body: bytes, secret: str = "test-secret", ts: str | None = None):
    ts = ts or str(int(time.time()))
    base = f"v0:{ts}:".encode() + body
    signature = "v0=" + hmac.new(secret.encode(), base, hashlib.sha256).hexdigest()
    return {
        "X-Slack-Request-Timestamp": ts,
        "X-Slack-Signature": signature,
        "Content-Type": "application/json",
    }


def _client():
    return TestClient(create_app(), raise_server_exceptions=False)


def _post(client, body: dict, secret="test-secret"):
    payload = json.dumps(body).encode()
    return client.post("/slack/events", content=payload, headers=_signed_headers(payload, secret))


def test_trigger_unconfigured_returns_503(monkeypatch):
    for name in ("SLACK_SIGNING_SECRET", "SLACK_BOT_TOKEN", "N3RF_SLACK_TRIGGER_WORKFLOW_ID"):
        monkeypatch.delenv(name, raising=False)
    response = _post(_client(), {"type": "url_verification", "challenge": "abc123"})
    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]


def test_url_verification_roundtrip(monkeypatch):
    monkeypatch.setenv("SLACK_SIGNING_SECRET", "test-secret")
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test")
    monkeypatch.setenv("N3RF_SLACK_TRIGGER_WORKFLOW_ID", "wf")
    response = _post(_client(), {"type": "url_verification", "challenge": "abc123"})
    assert response.status_code == 200
    assert response.json() == {"challenge": "abc123"}


def test_bad_signature_rejected(monkeypatch):
    monkeypatch.setenv("SLACK_SIGNING_SECRET", "test-secret")
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test")
    monkeypatch.setenv("N3RF_SLACK_TRIGGER_WORKFLOW_ID", "wf")
    body = json.dumps({"type": "url_verification", "challenge": "abc123"}).encode()
    response = _client().post(
        "/slack/events",
        content=body,
        headers={"X-Slack-Request-Timestamp": "1600000000", "X-Slack-Signature": "v0=deadbeef"},
    )
    assert response.status_code in (400, 401, 403)


def test_app_mention_triggers_workflow(monkeypatch):
    monkeypatch.setenv("SLACK_SIGNING_SECRET", "test-secret")
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test")
    monkeypatch.setenv("SLACK_BOT_ID", "B0001")
    monkeypatch.setenv("SLACK_BOT_USER_ID", "U0001")
    monkeypatch.setenv("N3RF_SLACK_TRIGGER_WORKFLOW_ID", "wf_123")
    monkeypatch.delenv("N3RF_SLACK_TRIGGER_CHANNELS", raising=False)

    calls = []

    class FakeStore:
        @staticmethod
        def get_workflow(workflow_id):
            assert workflow_id == "wf_123"
            return {"nodes": [], "edges": []}

    async def fake_execute(nodes, edges, override, workflow_id):
        calls.append(
            {"nodes": nodes, "edges": edges, "override": override, "workflow_id": workflow_id}
        )

    monkeypatch.setattr(trigger, "store", FakeStore)
    monkeypatch.setattr(trigger, "execute_workflow", fake_execute)

    event = {
        "type": "event_callback",
        "team_id": "T1",
        "api_app_id": "A1",
        "event_id": "Ev1",
        "event_time": 1700000000,
        "event": {
            "type": "app_mention",
            "user": "U100",
            "text": "<@U0001> what's our line on pricing?",
            "ts": "1700000000.000100",
            "channel": "C999",
        },
    }
    response = _post(_client(), event)
    assert response.status_code == 200

    deadline = time.time() + 2.0
    while not calls and time.time() < deadline:
        time.sleep(0.01)
    assert len(calls) == 1
    override = calls[0]["override"]
    assert override[0]["question"] == "what's our line on pricing?"
    assert override[0]["channel"] == "C999"
    assert override[0]["user"] == "U100"
    assert override[0]["thread_ts"] == "1700000000.000100"
    assert calls[0]["workflow_id"] == "wf_123"


def test_app_mention_ignored_outside_allowlist(monkeypatch):
    monkeypatch.setenv("SLACK_SIGNING_SECRET", "test-secret")
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test")
    monkeypatch.setenv("N3RF_SLACK_TRIGGER_WORKFLOW_ID", "wf_123")
    monkeypatch.setenv("N3RF_SLACK_TRIGGER_CHANNELS", "C_ALLOWED")

    calls = []

    async def fake_execute(*args, **kwargs):
        calls.append(kwargs or args)

    monkeypatch.setattr(trigger, "execute_workflow", fake_execute)

    event = {
        "type": "event_callback",
        "team_id": "T1",
        "api_app_id": "A1",
        "event_id": "Ev1",
        "event_time": 1700000000,
        "event": {
            "type": "app_mention",
            "user": "U100",
            "text": "<@U0001> hello",
            "ts": "1700000000.000100",
            "channel": "C_OTHER",
        },
    }
    response = _post(_client(), event)
    assert response.status_code == 200
    time.sleep(0.1)
    assert calls == []


def test_non_mention_event_is_noop(monkeypatch):
    monkeypatch.setenv("SLACK_SIGNING_SECRET", "test-secret")
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test")
    monkeypatch.setenv("N3RF_SLACK_TRIGGER_WORKFLOW_ID", "wf_123")

    calls = []

    async def fake_execute(*args, **kwargs):
        calls.append((args, kwargs))

    monkeypatch.setattr(trigger, "execute_workflow", fake_execute)

    response = _post(
        _client(),
        {
            "type": "event_callback",
            "team_id": "T1",
            "api_app_id": "A1",
            "event_id": "Ev2",
            "event_time": 1700000001,
            "event": {"type": "message", "channel": "C999", "ts": "1.0", "text": "hello"},
        },
    )
    assert response.status_code == 200
    time.sleep(0.1)
    assert calls == []


def test_mention_strips_mention_and_collapses_spacing():
    row = trigger.mention_row({"text": "<@UBOT>  what   is    this?", "channel": "C1", "ts": "9.9"})
    assert row["question"] == "what is this?"
    assert row["thread_ts"] == "9.9"
    assert row["channel"] == "C1"
