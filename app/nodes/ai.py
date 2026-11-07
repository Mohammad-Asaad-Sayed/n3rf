from __future__ import annotations

import asyncio
import math
from typing import Any

from app.contracts import Item, ItemList
from app.errors import NodeError
from app.expressions import render
from app.llm import LLMClient, SchemaValidationError
from app.params import Param
from app.registry import node


def _client(ctx: Any) -> tuple[LLMClient, str]:
    base_url = ctx.param("base_url", str, "https://api.openai.com/v1")
    env_key = ctx.param("api_key_env", str, "OPENAI_API_KEY")
    model = ctx.param("model", str, "gpt-4o-mini")
    return LLMClient(base_url, env_key), model


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
    Param("base_url", "string", "Base URL", default="https://api.openai.com/v1"),
    Param(
        "api_key_env",
        "string",
        "API key environment variable",
        default="OPENAI_API_KEY",
    ),
    Param("model", "string", "Model", default="gpt-4o-mini", required=True),
    Param(
        "prompt",
        "textarea",
        "Prompt",
        default="",
        expression=True,
        hint=(
            "Each incoming row is automatically included in the prompt. "
            "Type @ to insert a specific field."
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
    "llm_structured",
    "LLM Structured",
    group="ai",
    description="Generate schema-validated JSON from each incoming row.",
    params=_COMMON
    + [
        Param("schema", "json", "Output schema", default={}),
        Param(
            "mode",
            "select",
            "Output mode",
            default="per_input",
            options=["per_input", "expand_arrays"],
        ),
    ],
)
async def llm_structured(items: ItemList, ctx: Any) -> ItemList:
    if not items:
        return []
    client, model = _client(ctx)
    schema = ctx.param("schema", dict, {})
    template = ctx.param("prompt", str, "")
    mode = ctx.param("mode", str, "per_input")

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
    description="Keep rows matching an AI criterion.",
    params=_COMMON
    + [
        Param(
            "criterion",
            "textarea",
            "Keep rows that",
            default="",
            required=True,
            expression=True,
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
    description="Score rows and keep the top results.",
    params=_COMMON
    + [
        Param("criterion", "textarea", "Rank by", default="", expression=True),
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
    description="Collapse semantically similar rows.",
    params=_COMMON
    + [
        Param("field", "string", "Text field", default="text", required=True),
        Param("threshold", "number", "Similarity threshold", default=0.9),
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
