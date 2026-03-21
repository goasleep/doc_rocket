"""Claude (Anthropic) LLM client."""
from typing import Any

import anthropic

from app.core.llm.base import LLMClient


class ClaudeClient(LLMClient):
    def __init__(self, api_key: str, default_model: str = "claude-sonnet-4-6") -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._default_model = default_model

    async def chat(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        response_format: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> str:
        # Anthropic uses a separate system param; extract if present
        system = ""
        filtered_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                filtered_messages.append(msg)

        params: dict[str, Any] = {
            "model": model or self._default_model,
            "max_tokens": kwargs.pop("max_tokens", 4096),
            "messages": filtered_messages,
        }
        if system:
            params["system"] = system
        params.update(kwargs)

        # For JSON mode: use tool_use to enforce structured output
        if response_format and response_format.get("type") == "json_object":
            params["tools"] = [
                {
                    "name": "structured_output",
                    "description": "Return structured JSON output",
                    "input_schema": {"type": "object", "properties": {}, "additionalProperties": True},
                }
            ]
            params["tool_choice"] = {"type": "tool", "name": "structured_output"}
            response = await self._client.messages.create(**params)
            # Extract tool_use content
            for block in response.content:
                if block.type == "tool_use":
                    import json
                    return json.dumps(block.input)
            return ""

        response = await self._client.messages.create(**params)
        return "".join(
            block.text for block in response.content if hasattr(block, "text")
        )
