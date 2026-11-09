import asyncio
import tempfile

import httpx
import pytest

from app.engine import RunContext
from app.errors import NodeError
from app.main import app
from app.nodes.http import http_request


def test_catalog_run_and_durable_run_history(monkeypatch):
    with tempfile.TemporaryDirectory() as directory:
        monkeypatch.setenv("N3RF_DB_PATH", f"{directory}/runs.sqlite3")
        asyncio.run(_exercise_api())


async def _exercise_api():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        catalog = await client.get("/nodes")
        assert catalog.status_code == 200
        assert len(catalog.json()) == 30

        response = await client.post(
            "/run",
            json={
                "nodes": [
                    {
                        "id": "input",
                        "type": "manual_json",
                        "params": {"data": [{"name": "A"}, {"name": "B"}]},
                    },
                    {"id": "limit", "type": "limit", "params": {"max": 1, "offset": 0}},
                ],
                "edges": [{"source": "input", "target": "limit"}],
            },
        )
        assert response.status_code == 200
        result = response.json()
        assert result["nodes"][1]["rows_in"] == 2
        assert result["nodes"][1]["rows_out"] == 1
        assert (await client.get(f"/runs/{result['run_id']}")).json() == result

        node_run = await client.post(
            "/run",
            json={
                "nodes": [
                    {
                        "id": "input",
                        "type": "manual_json",
                        "params": {"data": [{"name": "A"}, {"name": "B"}]},
                    },
                    {"id": "limit", "type": "limit", "params": {"max": 1, "offset": 0}},
                    {"id": "downstream", "type": "sort", "params": {}},
                ],
                "edges": [
                    {"source": "input", "target": "limit"},
                    {"source": "limit", "target": "downstream"},
                ],
                "target_node_id": "limit",
            },
        )
        assert node_run.status_code == 200
        node_result = node_run.json()
        assert [item["id"] for item in node_result["nodes"]] == ["input", "limit"]
        assert node_result["output"] == [{"name": "A"}]
        assert (await client.get(f"/runs/{node_result['run_id']}")).status_code == 404

        missing_target = await client.post(
            "/run",
            json={
                "nodes": [{"id": "input", "type": "manual_json", "params": {"data": []}}],
                "edges": [],
                "target_node_id": "missing",
            },
        )
        assert missing_target.status_code == 422

        invalid = await client.post(
            "/run",
            json={
                "nodes": [{"id": "sort", "type": "sort", "params": {}}],
                "edges": [],
            },
        )
        assert invalid.status_code == 422
        assert "field" in invalid.json()["detail"].lower()

        secret_param = await client.post(
            "/workflows",
            json={
                "name": "Invalid",
                "nodes": [
                    {
                        "id": "input",
                        "type": "manual_json",
                        "params": {"data": [], "api_key": "not-persisted"},
                    }
                ],
                "edges": [],
            },
        )
        assert secret_param.status_code == 422

        created = await client.post("/workflows", json={"name": "Saved", "nodes": [], "edges": []})
        assert created.status_code == 201
        workflow_id = created.json()["id"]
        assert (await client.get(f"/workflows/{workflow_id}")).json()["name"] == "Saved"
        assert (await client.get("/workflows")).json()[0]["id"] == workflow_id

        upload = await client.post(
            "/upload",
            files={"file": ("sample.txt", b"hello", "text/plain")},
        )
        assert upload.status_code == 200
        assert upload.json() == {"filename": "sample.txt", "content": "aGVsbG8="}


def test_http_credentials_must_reference_environment():
    context = RunContext(
        {
            "url": "https://example.invalid",
            "headers": {"Authorization": "Bearer placeholder"},
            "per_row": True,
        }
    )
    with pytest.raises(NodeError, match="secret"):
        asyncio.run(http_request([], context))


def test_workflow_save_strips_pasted_api_key(monkeypatch):
    with tempfile.TemporaryDirectory() as directory:
        monkeypatch.setenv("N3RF_DB_PATH", f"{directory}/saved.sqlite3")
        asyncio.run(_exercise_save_strip())


async def _exercise_save_strip():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        created = await client.post(
            "/workflows",
            json={
                "name": "Pasted",
                "nodes": [
                    {
                        "id": "ai",
                        "type": "ask_ai",
                        "params": {
                            "provider": "custom",
                            "base_url": "https://provider.invalid/v1",
                            "model": "test-model",
                            "api_key_env": "TEST_KEY",
                            "api_key": "paste-secret-never-saved",
                            "prompt": "hi",
                        },
                    }
                ],
                "edges": [],
            },
        )
        assert created.status_code == 201, created.text
        assert "paste-secret-never-saved" not in created.text
        workflow_id = created.json()["id"]
        saved = (await client.get(f"/workflows/{workflow_id}")).json()
        assert "paste-secret-never-saved" not in str(saved)
        params = saved["nodes"][0]["params"]
        assert "api_key" not in params
        assert params["api_key_env"] == "TEST_KEY"
