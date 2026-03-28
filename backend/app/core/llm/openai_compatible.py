"""Shared base for OpenAI-compatible LLM clients (Kimi, OpenAI)."""
import json
from typing import Any

from openai import AsyncOpenAI

from app.core.llm.base import ChatResponse, LLMClient, ToolCall, UsageData


class OpenAICompatibleClient(LLMClient):
    """Base class for providers using the OpenAI API format."""

    _client: AsyncOpenAI
    _default_model: str

    async def chat(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        response_format: dict[str, str] | None = None,
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> ChatResponse:
        params: dict[str, Any] = {
            "model": model or self._default_model,
            "messages": messages,
        }
        if response_format:
            params["response_format"] = response_format
        if tools:
            params["tools"] = tools
        params.update(kwargs)

        try:
            response = await self._client.chat.completions.create(**params)
        except Exception as e:
            error_msg = str(e).lower()
            print(f"[DEBUG] OpenAI compatible error: {error_msg}")
            print(f"[DEBUG] Params had temperature: {'temperature' in params}")
            # Handle models that don't support temperature parameter
            # Matches: "invalid temperature", "only 1 is allowed for this model", etc.
            if "temperature" in error_msg and ("invalid" in error_msg or "only" in error_msg or "support" in error_msg):
                # Remove temperature and retry
                params.pop("temperature", None)
                print(f"[DEBUG] Retrying without temperature")
                response = await self._client.chat.completions.create(**params)
            else:
                raise
        message = response.choices[0].message

        # Parse tool calls if present
        tool_calls: list[ToolCall] = []
        if message.tool_calls:
            for tc in message.tool_calls:
                try:
                    arguments = json.loads(tc.function.arguments)
                except (json.JSONDecodeError, AttributeError):
                    arguments = {}
                tool_calls.append(ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=arguments,
                ))

        # Extract usage data if available
        usage: UsageData | None = None
        if response.usage:
            usage = UsageData(
                prompt_tokens=response.usage.prompt_tokens or 0,
                completion_tokens=response.usage.completion_tokens or 0,
                total_tokens=response.usage.total_tokens or 0,
            )

        content = message.content or None
        reasoning_content = getattr(message, 'reasoning_content', None)
        return ChatResponse(content=content, tool_calls=tool_calls, reasoning_content=reasoning_content, usage=usage)
