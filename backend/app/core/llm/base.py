"""Abstract base class for LLM clients."""
from abc import ABC, abstractmethod
from typing import Any


class LLMProviderNotConfiguredError(Exception):
    """Raised when a provider's API key is not configured."""

    def __init__(self, provider: str) -> None:
        super().__init__(f"LLM provider '{provider}' is not configured. Set the API key in system settings.")
        self.provider = provider


class LLMClient(ABC):
    """Unified interface for all LLM providers."""

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        response_format: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> str:
        """Send a chat completion request and return the response text."""
        ...
