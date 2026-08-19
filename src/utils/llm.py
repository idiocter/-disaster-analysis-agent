"""Shared OpenAI client wrapper for the two call shapes nodes need:
forced structured output (parse_query_node) and free-form text generation
(generate_narrative_node).

Differences from the Anthropic implementation on `main`, since they bite:
  - the system prompt is a message with role="system", not a separate param
  - a forced tool call comes back as `tool_calls[].function.arguments`, which
    is a JSON *string* that must be parsed -- not an already-decoded dict
"""

import json
from typing import Any

from openai import OpenAI

from src.config import settings

_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not set in .env")
        _client = OpenAI(api_key=settings.openai_api_key)
    return _client


def call_structured(
    *,
    model: str,
    system: str,
    user_content: str,
    output_schema: dict[str, Any],
    output_tool_name: str = "submit_result",
    max_tokens: int = 1024,
) -> dict[str, Any]:
    client = get_client()
    response = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": output_tool_name,
                    "description": "Submit the final structured result.",
                    "parameters": output_schema,
                },
            }
        ],
        tool_choice={"type": "function", "function": {"name": output_tool_name}},
    )

    tool_calls = response.choices[0].message.tool_calls or []
    for call in tool_calls:
        if call.function.name == output_tool_name:
            return json.loads(call.function.arguments)
    raise RuntimeError("model did not return structured output")


def call_text(*, model: str, system: str, user_content: str, max_tokens: int = 1024) -> str:
    client = get_client()
    response = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ],
    )
    return response.choices[0].message.content or ""
