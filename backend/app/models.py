import uuid
from datetime import datetime, timezone

from beanie import Document
from fastapi_users import schemas
from fastapi_users_db_beanie import BeanieBaseUserDocument
from pydantic import BaseModel, ConfigDict, Field


def get_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

class User(BeanieBaseUserDocument):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    full_name: str | None = Field(default=None, max_length=255)
    created_at: datetime = Field(default_factory=get_datetime_utc)

    class Settings(BeanieBaseUserDocument.Settings):
        name = "users"


class UserRead(schemas.BaseUser[uuid.UUID]):
    full_name: str | None = None
    created_at: datetime | None = None


class UserCreate(schemas.BaseUserCreate):
    full_name: str | None = None


class UserUpdate(schemas.BaseUserUpdate):
    full_name: str | None = None


class UpdatePassword(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class UsersPublic(BaseModel):
    data: list[UserRead]
    count: int


# ---------------------------------------------------------------------------
# Item
# ---------------------------------------------------------------------------

class ItemBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


class ItemCreate(ItemBase):
    pass


class ItemUpdate(ItemBase):
    title: str | None = Field(default=None, min_length=1, max_length=255)  # type: ignore


class Item(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)
    owner_id: uuid.UUID
    created_at: datetime = Field(default_factory=get_datetime_utc)

    class Settings:
        name = "items"


class ItemPublic(ItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime | None = None


class ItemsPublic(BaseModel):
    data: list[ItemPublic]
    count: int


# ---------------------------------------------------------------------------
# Generic models
# ---------------------------------------------------------------------------

class Message(BaseModel):
    message: str
