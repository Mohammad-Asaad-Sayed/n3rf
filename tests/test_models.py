import asyncio

import httpx

from app import llm
from app.main import app


def test_model_profiles_and_connection_test(monkeypatch, tmp_path):
    monkeypatch.setenv("N3RF_DB_PATH", str(tmp_path / "models.sqlite3"))
    monkeypatch.setenv("TEST_PROVIDER_KEY", "not-persisted")
    request_headers = []
    real_async_client = httpx.AsyncClient

    class MockProviderClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def get(self, url, headers):
            request_headers.append((url, headers))
            request = httpx.Request("GET", url)
            return httpx.Response(
                200,
                json={"data": [{"id": "test-model"}]},
                request=request,
            )

    monkeypatch.setattr(
        llm.httpx,
        "AsyncClient",
        lambda **_kwargs: MockProviderClient(),
    )
    asyncio.run(
        _exercise_model_profiles(
            real_async_client,
            request_headers,
        )
    )


async def _exercise_model_profiles(real_async_client, request_headers):
    async with real_async_client(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        profile_response = await client.post(
            "/models",
            json={
                "name": "Local test provider",
                "base_url": "http://localhost:1234/v1/",
                "model": "test-model",
                "api_key_env": "TEST_PROVIDER_KEY",
            },
        )
        assert profile_response.status_code == 201
        profile = profile_response.json()
        assert profile["base_url"] == "http://localhost:1234/v1/"
        assert "api_key" not in profile
        assert "not-persisted" not in profile_response.text

        updated = await client.post(
            "/models",
            json={
                **profile,
                "name": "Updated local provider",
                "base_url": "http://localhost:1234/v1",
            },
        )
        assert updated.status_code == 201
        assert updated.json()["name"] == "Updated local provider"

        connection = await client.post(
            "/models/test",
            json={
                "name": "Local test provider",
                "base_url": "http://localhost:1234/v1",
                "model": "test-model",
                "api_key_env": "TEST_PROVIDER_KEY",
            },
        )
        assert connection.status_code == 200
        assert connection.json()["model_available"] is True
        assert request_headers == [
            (
                "http://localhost:1234/v1/models",
                {"Authorization": "Bearer not-persisted"},
            )
        ]

        missing_key = await client.post(
            "/models/test",
            json={
                "name": "Missing key provider",
                "base_url": "http://localhost:1234/v1",
                "model": "test-model",
                "api_key_env": "MISSING_TEST_PROVIDER_KEY",
            },
        )
        assert missing_key.status_code == 502
        assert "is not set" in missing_key.json()["detail"]

        invalid_url = await client.post(
            "/models",
            json={
                "name": "Invalid",
                "base_url": "https://provider.example/v1?api_key=secret",
                "model": "test-model",
                "api_key_env": "",
            },
        )
        assert invalid_url.status_code == 422

        profiles = await client.get("/models")
        assert [item["id"] for item in profiles.json()] == [profile["id"]]
        assert profiles.json()[0]["name"] == "Updated local provider"
        deleted = await client.delete(f"/models/{profile['id']}")
        assert deleted.status_code == 204
        assert (await client.get("/models")).json() == []


def test_model_connection_test_with_pasted_key(monkeypatch, tmp_path):
    monkeypatch.setenv("N3RF_DB_PATH", str(tmp_path / "models_paste.sqlite3"))
    monkeypatch.delenv("MISSING_PASTE_PROFILE_KEY", raising=False)
    request_headers = []
    real_async_client = httpx.AsyncClient

    class MockProviderClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def get(self, url, headers):
            request_headers.append((url, headers))
            request = httpx.Request("GET", url)
            return httpx.Response(
                200,
                json={"data": [{"id": "test-model"}]},
                request=request,
            )

    monkeypatch.setattr(
        llm.httpx,
        "AsyncClient",
        lambda **_kwargs: MockProviderClient(),
    )
    asyncio.run(_exercise_pasted_model_key(real_async_client, request_headers))


async def _exercise_pasted_model_key(real_async_client, request_headers):
    async with real_async_client(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        connection = await client.post(
            "/models/test",
            json={
                "name": "Pasted key provider",
                "base_url": "http://localhost:1234/v1",
                "model": "test-model",
                "api_key_env": "MISSING_PASTE_PROFILE_KEY",
                "api_key": "paste-test-secret",
            },
        )
        assert connection.status_code == 200
        assert connection.json()["model_available"] is True
        assert "paste-test-secret" not in connection.text
        assert request_headers == [
            (
                "http://localhost:1234/v1/models",
                {"Authorization": "Bearer paste-test-secret"},
            )
        ]

        saved = await client.post(
            "/models",
            json={
                "name": "Pasted key provider",
                "base_url": "http://localhost:1234/v1",
                "model": "test-model",
                "api_key_env": "MISSING_PASTE_PROFILE_KEY",
                "api_key": "paste-test-secret",
            },
        )
        assert saved.status_code == 201
        assert "paste-test-secret" not in saved.text
        assert "api_key" not in saved.json()
        listed = (await client.get("/models")).json()
        assert listed and "paste-test-secret" not in str(listed)
        assert "api_key" not in listed[0]
