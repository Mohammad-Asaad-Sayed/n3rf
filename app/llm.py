from __future__ import annotations

import asyncio
import json
import os
import random
from typing import Any

import httpx
from jsonschema import ValidationError, validate

from app.errors import NodeError


class SchemaValidationError(ValidationError):
    def __init__(self, error: ValidationError, tokens_in: int, tokens_out: int):
        super().__init__(error.message)
        self.tokens_in = tokens_in
        self.tokens_out = tokens_out


class LLMClient:
    def __init__(
        self,
        base_url: str,
        api_key_env: str,
        *,
        api_key_override: str | None = None,
        timeout: float = 60.0,
        retries: int = 2,
    ):
        self.base_url = base_url.rstrip("/")
        override = (api_key_override or "").strip()
        if override:
            self.api_key = override
        else:
            self.api_key = os.environ.get(api_key_env, "") if api_key_env else ""
        self.timeout = timeout
        self.retries = retries
        if not self.api_key and api_key_env != "" and not override:
            raise NodeError(f"Environment variable '{api_key_env}' is not set.")

    async def complete(
        self, model: str, prompt: str, *, schema: dict[str, Any] | None = None
    ) -> tuple[Any, int, int]:
        if not model:
            raise NodeError("Parameter 'model' is required.")
        headers = {"Authorization": "Bearer " + self.api_key} if self.api_key else {}
        url = f"{self.base_url}/chat/completions"
        body = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"} if schema else None,
        }
        body = {key: value for key, value in body.items() if value is not None}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(self.retries + 1):
                try:
                    response = await client.post(url, headers=headers, json=body)
                    response.raise_for_status()
                    payload = response.json()
                    content = payload["choices"][0]["message"]["content"]
                    result = json.loads(content)
                    usage = payload.get("usage", {})
                    tokens_in = int(usage.get("prompt_tokens", 0))
                    tokens_out = int(usage.get("completion_tokens", 0))
                    if schema:
                        try:
                            validate(result, schema)
                        except ValidationError as exc:
                            raise SchemaValidationError(exc, tokens_in, tokens_out) from exc
                    return result, tokens_in, tokens_out
                except SchemaValidationError:
                    raise
                except (
                    httpx.HTTPError,
                    KeyError,
                    IndexError,
                    TypeError,
                    json.JSONDecodeError,
                ) as exc:
                    if attempt >= self.retries:
                        raise NodeError(f"Model request failed: {exc}") from exc
                    await asyncio.sleep(min(2**attempt * 0.25 + random.random() * 0.15, 3.0))
        raise NodeError("Model request failed after retries.")

    async def embed(self, model: str, text: str) -> tuple[list[float], int]:
        headers = {"Authorization": "Bearer " + self.api_key} if self.api_key else {}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(self.retries + 1):
                try:
                    response = await client.post(
                        f"{self.base_url}/embeddings",
                        headers=headers,
                        json={"model": model, "input": text},
                    )
                    response.raise_for_status()
                    payload = response.json()
                    vector = payload["data"][0]["embedding"]
                    if not isinstance(vector, list) or not vector:
                        raise NodeError("Embedding response did not contain a vector.")
                    tokens = int(payload.get("usage", {}).get("prompt_tokens", 0))
                    return [float(value) for value in vector], tokens
                except NodeError:
                    raise
                except (
                    httpx.HTTPError,
                    KeyError,
                    IndexError,
                    TypeError,
                    ValueError,
                ) as exc:
                    if attempt >= self.retries:
                        raise NodeError(f"Embedding request failed: {exc}") from exc
                    await asyncio.sleep(min(2**attempt * 0.25 + random.random() * 0.15, 3.0))
        raise NodeError("Embedding request failed after retries.")


async def test_connection(
    base_url: str, api_key_env: str, model: str, api_key_override: str = ""
) -> dict[str, Any]:
    endpoint = httpx.URL(base_url.rstrip("/"))
    if endpoint.scheme not in {"http", "https"} or not endpoint.host:
        raise NodeError("Base URL must be an absolute HTTP or HTTPS URL.")
    if endpoint.username or endpoint.password:
        raise NodeError("Credentials must use an environment variable, not the URL.")
    override = (api_key_override or "").strip()
    if override:
        api_key = override
    else:
        api_key = os.environ.get(api_key_env, "") if api_key_env else ""
        if api_key_env and not api_key:
            raise NodeError(f"Environment variable '{api_key_env}' is not set.")
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(f"{str(endpoint).rstrip('/')}/models", headers=headers)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise NodeError(f"Model endpoint returned HTTP {exc.response.status_code}.") from exc
    except httpx.HTTPError as exc:
        raise NodeError(f"Could not reach the model endpoint: {type(exc).__name__}.") from exc
    try:
        payload = response.json()
        models = payload["data"]
        model_ids = [entry["id"] for entry in models if isinstance(entry.get("id"), str)]
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        raise NodeError("Model endpoint returned an invalid models response.") from exc
    if model_ids and model not in model_ids:
        return {
            "ok": True,
            "model_available": False,
            "message": "Connection succeeded, but the configured model was not listed.",
            "models": model_ids[:50],
        }
    return {
        "ok": True,
        "model_available": True,
        "message": "Connection succeeded.",
        "models": model_ids[:50],
    }
