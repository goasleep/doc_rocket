"""OpenAI LLM client."""
from typing import Any

from openai import AsyncOpenAI

from app.core.llm.base import LLMClient


class OpenAIClient(LLMClient):
    def __init__(self, api_key: str, default_model: str = "gpt-4o") -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self._default_model = default_model

    async def chat(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        response_format: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> str:
        params: dict[str, Any] = {
            "model": model or self._default_model,
            "messages": messages,
        }
        if response_format:
            params["response_format"] = response_format
        params.update(kwargs)

        response = await self._client.chat.completions.create(**params)
        return response.choices[0].message.content or ""
