"""Following-open-model pricing (Altclay ``lib/pricing.ts`` → Python).

Prices are **published list prices** per 1M tokens, USD — no markup, no
credits. ``GET /pricing`` serves the table; ``POST /pricing/estimate``
answers “what will this row batch cost?” without running anything.
"""

from __future__ import annotations

MODEL_PRICES: dict[str, dict[str, float | str]] = {
    # Anthropic (May 2026)
    "claude-haiku-4-5-20251001": {
        "provider": "anthropic",
        "input_per_1m": 1.0,
        "output_per_1m": 5.0,
    },
    "claude-sonnet-4-5-20250929": {
        "provider": "anthropic",
        "input_per_1m": 3.0,
        "output_per_1m": 15.0,
    },
    "claude-opus-4-5-20251101": {
        "provider": "anthropic",
        "input_per_1m": 5.0,
        "output_per_1m": 25.0,
    },
    # Google (May 2026)
    "gemini-2.0-flash": {"provider": "gemini", "input_per_1m": 0.1, "output_per_1m": 0.4},
    "gemini-2.5-flash": {"provider": "gemini", "input_per_1m": 0.30, "output_per_1m": 2.50},
    "gemini-2.5-flash-lite": {"provider": "gemini", "input_per_1m": 0.10, "output_per_1m": 0.40},
    "gemini-2.5-pro": {"provider": "gemini", "input_per_1m": 1.25, "output_per_1m": 10.0},
    "gemini-3-flash-preview": {"provider": "gemini", "input_per_1m": 0.50, "output_per_1m": 3.00},
    "gemini-3.1-flash-lite-preview": {
        "provider": "gemini",
        "input_per_1m": 0.25,
        "output_per_1m": 1.50,
    },
    "gemini-3.1-pro-preview": {"provider": "gemini", "input_per_1m": 2.00, "output_per_1m": 12.00},
    # xAI (May 2026)
    "grok-4-1-fast": {"provider": "grok", "input_per_1m": 0.20, "output_per_1m": 0.50},
    "grok-4-0320": {"provider": "grok", "input_per_1m": 2.0, "output_per_1m": 6.0},
    # OpenAI (May 2026)
    "gpt-4.1-nano": {"provider": "openai", "input_per_1m": 0.10, "output_per_1m": 0.40},
    "gpt-5.4-nano": {"provider": "openai", "input_per_1m": 0.20, "output_per_1m": 1.25},
    "gpt-5.4-mini": {"provider": "openai", "input_per_1m": 0.75, "output_per_1m": 4.50},
    "gpt-5.4": {"provider": "openai", "input_per_1m": 2.50, "output_per_1m": 15.00},
    # n3rf local / free aliases
    "gpt-4o-mini": {"provider": "openai", "input_per_1m": 0.15, "output_per_1m": 0.60},
    "gpt-4o": {"provider": "openai", "input_per_1m": 5.00, "output_per_1m": 15.00},
    "gemini-2.5-flash-latest": {"provider": "gemini", "input_per_1m": 0.30, "output_per_1m": 2.50},
}

PRICING_LAST_UPDATED = "May 2026"


def estimate_cost(
    rows: int,
    input_tokens_per_row: int,
    output_tokens_per_row: int,
    model: str,
) -> dict[str, float | str | None]:
    price = MODEL_PRICES.get(model)
    if price is None:
        return {
            "model": model,
            "provider": None,
            "rows": rows,
            "estimated_cost": None,
            "estimated_per_row": None,
            "note": "No published price for this model — run the Test to see usage.",
        }
    cost = (
        rows * input_tokens_per_row * float(price["input_per_1m"])
        + rows * output_tokens_per_row * float(price["output_per_1m"])
    ) / 1_000_000
    return {
        "model": model,
        "provider": price["provider"],
        "rows": rows,
        "estimated_cost": round(cost, 4),
        "estimated_per_row": round(cost / rows, 6) if rows else 0.0,
        "note": f"List price, {PRICING_LAST_UPDATED}. You pay the provider directly; n3rf adds $0.",
    }
