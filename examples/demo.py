import asyncio

from app.engine import run_workflow

NODES = [
    {
        "id": "source",
        "type": "manual_json",
        "params": {
            "data": [
                {"company": "Northstar Labs", "notes": "health software"},
                {"company": "Acme Retail", "notes": "online shop"},
            ]
        },
    },
    {
        "id": "classify",
        "type": "ask_ai",
        "params": {
            "provider": "custom",
            "model": "gpt-4o-mini",
            "prompt": "Classify this company using its notes.",
            "schema": {
                "type": "object",
                "properties": {"category": {"type": "string"}},
                "required": ["category"],
                "additionalProperties": False,
            },
        },
    },
    {
        "id": "sort",
        "type": "sort",
        "params": {"field": "company", "direction": "asc"},
    },
    {"id": "limit", "type": "limit", "params": {"max": 10, "offset": 0}},
]
EDGES = [
    {"source": source, "target": target}
    for source, target in zip(
        ("source", "classify", "sort"),
        ("classify", "sort", "limit"),
        strict=True,
    )
]


async def main() -> None:
    result = await run_workflow(NODES, EDGES)
    for item in result["nodes"]:
        print(f"{item['id']}: {item['rows_in']} -> {item['rows_out']} rows ({item['ms']} ms)")
    print(f"Run status: {result['status']}; model calls: {result['metrics']['llm_calls']}")


if __name__ == "__main__":
    asyncio.run(main())
