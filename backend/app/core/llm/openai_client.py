"""OpenAI LLM client."""
from openai import AsyncOpenAI

from app.core.llm.openai_compatible import OpenAICompatibleClient


class OpenAIClient(OpenAICompatibleClient):
    def __init__(self, api_key: str, default_model: str = "gpt-4o") -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self._default_model = default_model
