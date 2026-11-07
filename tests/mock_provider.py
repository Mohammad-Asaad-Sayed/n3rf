import json

import httpx


def install_mock_provider(monkeypatch, replies: list[dict]) -> list[httpx.Request]:
    requests = []
    queue = iter(replies)

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        reply = next(queue)
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": json.dumps(reply)}}],
                "usage": {"prompt_tokens": 7, "completion_tokens": 3},
            },
        )

    original = httpx.AsyncClient

    def mocked_client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return original(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", mocked_client)
    return requests
