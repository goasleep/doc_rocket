"""Abstract base class for LLM clients."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


class LLMProviderNotConfiguredError(Exception):
    """Raised when a provider's API key is not configured."""

    def __init__(self, provider: str) -> None:
        super().__init__(f"LLM provider '{provider}' is not configured. Set the API key in system settings.")
        self.provider = provider


@dataclass
class ToolCall:
    """Represents a single tool call returned by the LLM."""
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class UsageData:
    """Token usage data from an LLM API response."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass
class ChatResponse:
    """Unified response from any LLM client."""
    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    reasoning_content: str | None = None  # For models with thinking enabled
    usage: UsageData | None = None  # Token usage data (if available)


class LLMClient(ABC):
    """Unified interface for all LLM providers."""

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        response_format: dict[str, str] | None = None,
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> ChatResponse:
        """Send a chat completion request and return a ChatResponse."""
        ...
