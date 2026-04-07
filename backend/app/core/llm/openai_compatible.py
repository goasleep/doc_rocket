"""Shared base for OpenAI-compatible LLM clients (Kimi, OpenAI)."""
import asyncio
import json
import logging
import random
from typing import Any

from openai import AsyncOpenAI

from app.core.llm.base import ChatResponse, LLMClient, ToolCall, UsageData

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3


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
        # Extract images from kwargs and convert to vision message format
        images: list[str] | None = kwargs.pop("images", None)
        if images and messages:
            last_msg = messages[-1]
            if last_msg.get("role") == "user":
                content_parts: list[dict[str, Any]] = [
                    {"type": "text", "text": str(last_msg.get("content", ""))}
                ]
                for url in images:
                    content_parts.append(
                        {"type": "image_url", "image_url": {"url": url}}
                    )
                last_msg["content"] = content_parts

        params: dict[str, Any] = {
            "model": model or self._default_model,
            "messages": messages,
        }
        if response_format:
            params["response_format"] = response_format
        if tools:
            params["tools"] = tools
        params.update(kwargs)

        response = None
        last_exception: Exception | None = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                response = await self._client.chat.completions.create(**params)
                break
            except Exception as e:
                last_exception = e
                error_msg = str(e).lower()
                status_code = getattr(e, "status_code", None)
                is_transient = (
                    status_code in (429, 503, 504)
                    or "timeout" in error_msg
                    or "rate limit" in error_msg
                    or "temporarily unavailable" in error_msg
                )
                if not is_transient or attempt >= _MAX_RETRIES:
                    break
                wait = (2 ** attempt) + random.uniform(0, 1)
                logger.debug(
                    "Transient LLM error on attempt %s, retrying in %.1fs: %s",
                    attempt + 1,
                    wait,
                    e,
                )
                await asyncio.sleep(wait)

        if response is None:
            error_msg = str(last_exception).lower()
            logger.debug("OpenAI compatible error: %s", error_msg)
            logger.debug("Params had temperature: %s", "temperature" in params)
            if "temperature" in error_msg and ("invalid" in error_msg or "only" in error_msg or "support" in error_msg):
                params.pop("temperature", None)
                logger.debug("Retrying without temperature")
                response = await self._client.chat.completions.create(**params)
            else:
                raise last_exception
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
