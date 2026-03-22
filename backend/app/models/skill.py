"""Skill document model — stores agent skill packages."""
import uuid
from datetime import datetime, timezone
from typing import Literal

from beanie import Document
from pydantic import BaseModel, ConfigDict, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SkillScript(BaseModel):
    """A script bundled with a skill."""
    filename: str
    content: str
    language: str = "python"


class Skill(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str  # unique, kebab-case identifier
    description: str = ""  # trigger condition shown in catalog
    body: str = ""  # full SKILL.md Markdown content
    scripts: list[SkillScript] = Field(default_factory=list)
    needs_network: bool = False
    is_active: bool = True
    source: Literal["imported", "user"] = "user"
    imported_from: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    class Settings:
        name = "skills"
        indexes = ["name"]


class SkillCreate(BaseModel):
    name: str
    description: str = ""
    body: str = ""
    scripts: list[SkillScript] = Field(default_factory=list)
    needs_network: bool = False
    is_active: bool = True
    source: Literal["imported", "user"] = "user"
    imported_from: str | None = None


class SkillUpdate(BaseModel):
    description: str | None = None
    body: str | None = None
    scripts: list[SkillScript] | None = None
    needs_network: bool | None = None
    is_active: bool | None = None


class SkillPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    description: str
    body: str
    scripts: list[SkillScript]
    needs_network: bool
    is_active: bool
    source: str
    imported_from: str | None
    created_at: datetime
    updated_at: datetime


class SkillsPublic(BaseModel):
    data: list[SkillPublic]
    count: int
