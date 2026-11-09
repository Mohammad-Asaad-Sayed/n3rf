from __future__ import annotations

import asyncio
import json
import math
from typing import Any

import httpx

from app.contracts import Item, ItemList
from app.errors import NodeError
from app.expressions import render
from app.llm import LLMClient, SchemaValidationError
from app.params import Param
from app.registry import node

# Provider presets (Bricks-style): picking a provider fills in the endpoint,
# default model and key name. "custom" keeps the user-typed base URL so any
# OpenAI-compatible endpoint still works.
PROVIDERS: dict[str, dict[str, str]] = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "api_key_env": "OPENAI_API_KEY",
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "model": "gpt-oss-120b",
        "api_key_env": "GROQ_API_KEY",
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "model": "gemini-2.5-flash",
        "api_key_env": "GEMINI_API_KEY",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "model": "meta-llama/llama-3.3-70b-instruct:free",
        "api_key_env": "OPENROUTER_API_KEY",
    },
    "mistral": {
        "base_url": "https://api.mistral.ai/v1",
        "model": "mistral-small-latest",
        "api_key_env": "MISTRAL_API_KEY",
    },
    "huggingface": {
        "base_url": "https://router.huggingface.co/v1",
        "model": "mistralai/Mistral-7B-Instruct-v0.3",
        "api_key_env": "HUGGINGFACE_API_KEY",
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "model": "llama3.1:8b",
        "api_key_env": "",
    },
    "cloudflare": {
        "base_url": "",
        "model": "@cf/meta/llama-3.3-70b-instruct",
        "api_key_env": "CLOUDFLARE_API_TOKEN",
    },
    "custom": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "api_key_env": "OPENAI_API_KEY",
    },
}

PROVIDER_DEFAULT_BASE_URL = PROVIDERS["openai"]["base_url"]
PROVIDER_DEFAULT_MODEL = PROVIDERS["openai"]["model"]
PROVIDER_DEFAULT_ENV = PROVIDERS["openai"]["api_key_env"]


def _resolve(ctx: Any) -> tuple[str, str, str, str, str]:
    """Return (provider, base_url, api_key_env, model, api_key_override).

    Preset defaults only apply when the inspector value is still at its
    generic default — a user-typed value (or a saved workflow with a custom
    endpoint) is always respected.
    """
    provider = ctx.param("provider", str, "openai") or "openai"
    preset = PROVIDERS.get(provider, PROVIDERS["custom"])

    base_url = ctx.param("base_url", str, PROVIDER_DEFAULT_BASE_URL) or ""
    if provider == "custom":
        if not base_url:
            raise NodeError("Parameter 'base_url' is required for the Custom provider.")
    elif base_url == PROVIDER_DEFAULT_BASE_URL:
        base_url = preset["base_url"]
    elif not base_url:
        base_url = preset["base_url"]

    model = ctx.param("model", str, PROVIDER_DEFAULT_MODEL) or ""
    if model == PROVIDER_DEFAULT_MODEL and provider not in {"openai", "custom"}:
        model = preset["model"]
    elif not model:
        model = preset["model"]
    if not model:
        raise NodeError("Parameter 'model' is required.")

    api_key_env = ctx.param("api_key_env", str, PROVIDER_DEFAULT_ENV) or ""
    if provider == "ollama":
        api_key_env = ""
    elif api_key_env == PROVIDER_DEFAULT_ENV and provider not in {"openai", "custom"}:
        api_key_env = preset["api_key_env"]

    api_key_override = (ctx.param("api_key", str, "") or "").strip()
    if provider == "ollama":
        api_key_override = ""

    return provider, base_url, api_key_env, model, api_key_override


def _client(ctx: Any) -> tuple[LLMClient, str]:
    _provider, base_url, api_key_env, model, api_key_override = _resolve(ctx)
    return LLMClient(base_url, api_key_env, api_key_override=api_key_override), model


async def _cloudflare_complete(
    account_id: str,
    model: str,
    prompt: str,
    api_key: str,
) -> tuple[Any, int, int]:
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"
    headers = {"Authorization": f"Bearer {api_key}"}
    body = {"messages": [{"role": "user", "content": prompt}]}
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, headers=headers, json=body)
        if resp.status_code != 200:
            raise NodeError(f"Cloudflare request failed: {resp.status_code} {resp.text[:500]}")
        payload = resp.json()
    if not payload.get("success", False):
        raise NodeError(f"Cloudflare request failed: {payload.get('errors')}")
    text = payload.get("result", {}).get("response", "")
    try:
        value = json.loads(text)
    except (ValueError, TypeError):
        value = {"value": text}
    return value, 0, 0


async def _fanout(items: ItemList, ctx: Any, callback: Any) -> ItemList:
    concurrency = ctx.param("concurrency", int, 8)
    cap = ctx.param("max_output_rows", int, 500)
    policy = ctx.param("on_error", str, "error_item")
    if concurrency < 1 or concurrency > 64:
        raise NodeError("Parameter 'concurrency' must be between 1 and 64.")
    if cap < 1 or cap > 10000:
        raise NodeError("Parameter 'max_output_rows' must be between 1 and 10000.")
    semaphore = asyncio.Semaphore(concurrency)

    async def one(index: int, item: Item) -> ItemList:
        async with semaphore:
            try:
                return await callback(index, item)
            except Exception as exc:
                if policy == "fail":
                    raise NodeError(f"Row {index + 1}: {exc}") from exc
                if policy == "skip":
                    return []
                return [
                    {
                        "json": dict(item["json"]),
                        "meta": {**item["meta"], "error": str(exc)},
                    }
                ]

    results = await asyncio.gather(*(one(index, item) for index, item in enumerate(items)))
    output = [row for group in results for row in group]
    if len(output) > cap:
        raise NodeError(f"AI output exceeded max_output_rows ({cap}).")
    return output


_COMMON = [
    Param(
        "provider",
        "select",
        "Provider",
        default="openai",
        options=[
            "openai",
            "groq",
            "gemini",
            "openrouter",
            "mistral",
            "huggingface",
            "ollama",
            "cloudflare",
            "custom",
        ],
        hint="Pick a provider. Model and key name fill in automatically.",
    ),
    Param("model", "string", "Model", default="gpt-4o-mini", required=True),
    Param(
        "base_url",
        "string",
        "Base URL",
        default="https://api.openai.com/v1",
        show_if={"param": "provider", "in": ["custom"]},
        hint="Only for Custom. Any OpenAI-compatible endpoint works.",
    ),
    Param(
        "api_key_env",
        "string",
        "API key environment variable",
        default="OPENAI_API_KEY",
        show_if={
            "param": "provider",
            "in": [
                "openai",
                "groq",
                "gemini",
                "openrouter",
                "mistral",
                "huggingface",
                "cloudflare",
                "custom",
            ],
        },
        hint=(
            "Just the env-var name. The secret stays in the terminal that runs "
            "uvicorn. Or paste a key below for this run only."
        ),
    ),
    Param(
        "api_key",
        "password",
        "API key (paste — run only)",
        default="",
        show_if={
            "param": "provider",
            "in": [
                "openai",
                "groq",
                "gemini",
                "openrouter",
                "mistral",
                "huggingface",
                "cloudflare",
                "custom",
            ],
        },
        hint=(
            "Paste a key for this run only — never saved or logged. "
            "Leave blank to use the env var above."
        ),
    ),
    Param(
        "account_id",
        "string",
        "Account ID",
        default="",
        show_if={"param": "provider", "in": ["cloudflare"]},
        hint="Cloudflare dashboard > Account ID.",
    ),
    Param(
        "prompt",
        "textarea",
        "Prompt",
        default="",
        expression=True,
        hint=(
            "Each incoming row is automatically included. "
            '@ picks a field, e.g. "Summarize {{company}}".'
        ),
    ),
    Param("concurrency", "number", "Concurrency", default=8),
    Param("max_output_rows", "number", "Maximum output rows", default=500),
    Param(
        "on_error",
        "select",
        "On row error",
        default="error_item",
        options=["error_item", "skip", "fail"],
    ),
]


@node(
    "ask_ai",
    "Ask AI",
    group="ai",
    description=(
        "Ask one model to enrich each row. Pick any provider in the inspector "
        "— model and key name fill in automatically. Adds its JSON fields to each row."
    ),
    params=_COMMON
    + [
        Param(
            "schema",
            "json",
            "Output schema",
            default={},
            hint="Leave {} for free JSON. Set a schema to validate the model's reply.",
        ),
        Param(
            "mode",
            "select",
            "Output mode",
            default="per_input",
            options=["per_input", "expand_arrays"],
        ),
    ],
)
async def ask_ai(items: ItemList, ctx: Any) -> ItemList:
    if not items:
        return []
    provider, base_url, api_key_env, model, api_key_override = _resolve(ctx)
    schema = ctx.param("schema", dict, {})
    template = ctx.param("prompt", str, "")
    mode = ctx.param("mode", str, "per_input")

    if provider == "cloudflare":
        account_id = (ctx.param("account_id", str, "") or "").strip()
        if not account_id:
            raise NodeError("Parameter 'account_id' is required for the Cloudflare provider.")
        if api_key_override:
            api_key = api_key_override
        else:
            if not api_key_env:
                raise NodeError("Environment variable 'CLOUDFLARE_API_TOKEN' is not set.")
            import os

            api_key = os.environ.get(api_key_env, "")
            if not api_key:
                raise NodeError(f"Environment variable '{api_key_env}' is not set.")

        async def cloudflare_call(index: int, item: Item) -> ItemList:
            prompt = f"{render(template, item['json'])}\n\nInput row:\n{item['json']!r}"
            ctx.metrics["llm_calls"] += 1
            value, _tin, _tout = await _cloudflare_complete(account_id, model, prompt, api_key)
            if mode == "expand_arrays" and isinstance(value, list):
                return [{"json": {"value": row}, "meta": dict(item["meta"])} for row in value]
            if not isinstance(value, dict):
                value = {"value": value}
            return [{"json": {**item["json"], **value}, "meta": dict(item["meta"])}]

        return await _fanout(items, ctx, cloudflare_call)

    client = LLMClient(base_url, api_key_env, api_key_override=api_key_override)

    async def call(index: int, item: Item) -> ItemList:
        prompt = f"{render(template, item['json'])}\n\nInput row:\n{item['json']!r}"
        ctx.metrics["llm_calls"] += 1
        try:
            value, tokens_in, tokens_out = await client.complete(
                model, prompt, schema=schema or None
            )
        except SchemaValidationError as first:
            ctx.metrics["tokens_in"] += first.tokens_in
            ctx.metrics["tokens_out"] += first.tokens_out
            ctx.metrics["llm_calls"] += 1
            value, tokens_in, tokens_out = await client.complete(
                model,
                f"{prompt}\n\nYour previous response failed schema validation: "
                f"{first.message}. Return corrected JSON.",
                schema=schema or None,
            )
        ctx.metrics["tokens_in"] += tokens_in
        ctx.metrics["tokens_out"] += tokens_out
        if mode == "expand_arrays" and isinstance(value, list):
            return [{"json": {"value": row}, "meta": dict(item["meta"])} for row in value]
        if not isinstance(value, dict):
            value = {"value": value}
        return [{"json": {**item["json"], **value}, "meta": dict(item["meta"])}]

    return await _fanout(items, ctx, call)


@node(
    "ai_filter",
    "AI Filter",
    group="ai",
    description="Ask your model which rows to keep. Drops the rest. Costs one model call per row.",
    params=_COMMON
    + [
        Param(
            "criterion",
            "textarea",
            "Keep rows that",
            default="are software companies",
            required=True,
            expression=True,
            hint=('Rule to judge each row. @ picks a field. Example: "{{industry}} is fintech".'),
        )
    ],
)
async def ai_filter(items: ItemList, ctx: Any) -> ItemList:
    if not items:
        return []
    client, model = _client(ctx)
    criterion = ctx.param("criterion", str, required=True)

    async def call(index: int, item: Item) -> ItemList:
        ctx.metrics["llm_calls"] += 1
        value, tin, tout = await client.complete(
            model,
            f'Return JSON {{"keep": true|false}}. Criterion: '
            f"{render(criterion, item['json'])}\nRow: {item['json']!r}",
        )
        ctx.metrics["tokens_in"] += tin
        ctx.metrics["tokens_out"] += tout
        return [item] if isinstance(value, dict) and value.get("keep") is True else []

    return await _fanout(items, ctx, call)


@node(
    "ai_ranker",
    "AI Ranker",
    group="ai",
    description=(
        "Score each row and keep the top N. Adds a score field. Costs one model call per row."
    ),
    params=_COMMON
    + [
        Param(
            "criterion",
            "textarea",
            "Rank by",
            default="how relevant this row is",
            expression=True,
            hint="What matters. @ picks a field. 1 = best match, 0 = worst.",
        ),
        Param("top_n", "number", "Top rows", default=10),
        Param("score_field", "string", "Score field", default="score"),
    ],
)
async def ai_ranker(items: ItemList, ctx: Any) -> ItemList:
    if not items:
        return []
    client, model = _client(ctx)
    criterion = ctx.param("criterion", str, "")
    score_field = ctx.param("score_field", str, "score")

    async def call(index: int, item: Item) -> ItemList:
        ctx.metrics["llm_calls"] += 1
        value, tin, tout = await client.complete(
            model,
            f"Score this row from 0 to 1 for: {render(criterion, item['json'])}\n"
            f'Return JSON {{"score": number}}.\nRow: {item["json"]!r}',
        )
        ctx.metrics["tokens_in"] += tin
        ctx.metrics["tokens_out"] += tout
        score = value.get("score") if isinstance(value, dict) else None
        if not isinstance(score, (int, float)):
            raise NodeError("Model response must contain a numeric score.")
        return [{"json": {**item["json"], score_field: score}, "meta": dict(item["meta"])}]

    output = await _fanout(items, ctx, call)
    top_n = ctx.param("top_n", int, 10)
    if top_n < 0:
        raise NodeError("Parameter 'top_n' must be zero or greater.")
    return sorted(output, key=lambda item: item["json"].get(score_field, 0), reverse=True)[:top_n]


@node(
    "semantic_dedup",
    "Semantic Dedup",
    group="ai",
    description="Collapse rows whose text means the same thing. Keeps the first of each group.",
    params=_COMMON
    + [
        Param(
            "field",
            "string",
            "Text field",
            default="text",
            required=True,
            hint="Field to compare. Example: company or text.",
        ),
        Param(
            "threshold",
            "number",
            "Similarity threshold",
            default=0.9,
            hint="0.9 = very similar. Lower merges more rows.",
        ),
        Param("embedding_model", "string", "Embedding model", default="text-embedding-3-small"),
    ],
)
async def semantic_dedup(items: ItemList, ctx: Any) -> ItemList:
    if not items:
        return []
    client, _ = _client(ctx)
    field = ctx.param("field", str, required=True)
    threshold = ctx.param("threshold", (int, float), 0.9)
    if not 0 <= threshold <= 1:
        raise NodeError("Parameter 'threshold' must be between 0 and 1.")
    concurrency = ctx.param("concurrency", int, 8)
    cap = ctx.param("max_output_rows", int, 500)
    if concurrency < 1 or concurrency > 64 or cap < 1 or cap > 10000:
        raise NodeError("Semantic dedup concurrency or output cap is out of range.")
    semaphore = asyncio.Semaphore(concurrency)
    embedding_model = ctx.param("embedding_model", str, "text-embedding-3-small")

    async def get_vector(item: Item) -> list[float]:
        async with semaphore:
            vector, tokens = await client.embed(embedding_model, str(item["json"].get(field, "")))
            ctx.metrics["llm_calls"] += 1
            ctx.metrics["tokens_in"] += tokens
            return vector

    vectors = await asyncio.gather(*(get_vector(item) for item in items))
    result = []
    kept_vectors: list[list[float]] = []
    for item, vector in zip(items, vectors, strict=True):
        if any(_cosine(vector, kept) >= threshold for kept in kept_vectors):
            continue
        if len(result) >= cap:
            raise NodeError(f"Semantic dedup exceeded max_output_rows ({cap}).")
        kept_vectors.append(vector)
        result.append(item)
    return result


def _cosine(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise NodeError("Embedding provider returned vectors with inconsistent dimensions.")
    denominator = math.sqrt(
        sum(value * value for value in left) * sum(value * value for value in right)
    )
    return (
        sum(a * b for a, b in zip(left, right, strict=True)) / denominator if denominator else 0.0
    )
