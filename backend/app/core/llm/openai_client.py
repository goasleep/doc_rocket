"""OpenAI LLM client."""
from openai import AsyncOpenAI

from app.core.llm.openai_compatible import OpenAICompatibleClient


class OpenAIClient(OpenAICompatibleClient):
    def __init__(
        self,
        api_key: str,
        default_model: str = "gpt-4o",
        base_url: str | None = None,
    ) -> None:
        kwargs: dict = {"api_key": api_key, "timeout": 60.0}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = AsyncOpenAI(**kwargs)
        self._default_model = default_model
        self.supports_temperature = "o3" not in self._default_model.lower() and "o1" not in self._default_model.lower()
