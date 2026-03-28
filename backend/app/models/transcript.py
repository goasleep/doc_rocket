"""Transcript model for persisting compressed conversation history."""
from datetime import datetime, timezone
from typing import Any

from beanie import Document
from pydantic import Field


def get_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


class Transcript(Document):
    """Stores full conversation history before compression."""

    id: str  # UUID string
    workflow_run_id: str | None = None
    messages: list[dict[str, Any]] = Field(default_factory=list)
    message_count: int = 0
    compressed_at: datetime = Field(default_factory=get_datetime_utc)
    # Optional metadata
    compression_reason: str = ""
    original_token_estimate: int = 0

    class Settings:
        name = "transcripts"
