"""Kimi (Moonshot) LLM client — uses OpenAI SDK with custom base_url."""
from openai import AsyncOpenAI

from app.core.llm.openai_compatible import OpenAICompatibleClient


class KimiClient(OpenAICompatibleClient):
    def __init__(self, api_key: str, default_model: str = "moonshot-v1-32k") -> None:
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.moonshot.cn/v1",
            timeout=60.0,
        )
        self._default_model = default_model
        self.supports_temperature = "moonshot-v1-32k" not in self._default_model.lower()
