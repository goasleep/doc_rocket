"""Tool document model — stores metadata for agent-usable tools."""
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from beanie import Document
from pydantic import BaseModel, ConfigDict, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Tool(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str  # unique, matches TOOL_REGISTRY key
    description: str = ""  # shown to LLM in tool schema
    parameters_schema: dict[str, Any] = Field(default_factory=dict)  # JSON Schema
    executor: Literal["python", "script"] = "python"
    function_name: str = ""  # Python registry key
    is_builtin: bool = True
    is_active: bool = True
    category: str = ""
    created_at: datetime = Field(default_factory=_utcnow)

    class Settings:
        name = "tools"
        indexes = ["name"]


class ToolUpdate(BaseModel):
    description: str | None = None
    is_active: bool | None = None
    category: str | None = None
    parameters_schema: dict[str, Any] | None = None


class ToolPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    description: str
    parameters_schema: dict[str, Any]
    executor: str
    function_name: str
    is_builtin: bool
    is_active: bool
    category: str
    created_at: datetime


class ToolsPublic(BaseModel):
    data: list[ToolPublic]
    count: int
