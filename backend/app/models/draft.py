import uuid
from datetime import datetime, timezone

from beanie import Document
from pydantic import BaseModel, ConfigDict, Field


def get_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


class EditHistoryEntry(BaseModel):
    content: str
    edited_at: datetime = Field(default_factory=get_datetime_utc)
    note: str = ""


class Draft(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    source_article_ids: list[uuid.UUID] = Field(default_factory=list)
    workflow_run_id: uuid.UUID | None = None
    title: str = ""
    title_candidates: list[str] = Field(default_factory=list)
    content: str = ""
    status: str = "draft"  # draft | editing | approved
    edit_history: list[EditHistoryEntry] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=get_datetime_utc)
    # Cover image fields
    cover_image_url: str | None = None      # Qiniu permanent URL
    thumb_media_id: str | None = None       # WeChat temporary media_id

    class Settings:
        name = "drafts"


class DraftPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    source_article_ids: list[uuid.UUID]
    workflow_run_id: uuid.UUID | None
    title: str
    title_candidates: list[str]
    content: str
    status: str
    edit_history: list[EditHistoryEntry]
    created_at: datetime
    cover_image_url: str | None = None


class DraftsPublic(BaseModel):
    data: list[DraftPublic]
    count: int


class DraftUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    status: str | None = None


class RewriteSectionRequest(BaseModel):
    selected_text: str
    context: str = ""


class RewriteSectionResponse(BaseModel):
    rewritten_text: str
