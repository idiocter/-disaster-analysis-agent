"""Shared Anthropic client wrapper for the two call shapes nodes need:
forced structured output (parse_query_node) and free-form text generation
(generate_narrative_node).
"""

from typing import Any

import anthropic

from src.config import settings

_client: anthropic.Anthropic | None = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
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
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user_content}],
        tools=[
            {
                "name": output_tool_name,
                "description": "Submit the final structured result.",
                "input_schema": output_schema,
            }
        ],
        tool_choice={"type": "tool", "name": output_tool_name},
    )
    for block in response.content:
        if block.type == "tool_use" and block.name == output_tool_name:
            return block.input
    raise RuntimeError("model did not return structured output")


def call_text(*, model: str, system: str, user_content: str, max_tokens: int = 1024) -> str:
    client = get_client()
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user_content}],
    )
    return "".join(block.text for block in response.content if block.type == "text")
