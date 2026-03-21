import uuid
from datetime import datetime, timezone

from fastapi_users import schemas
from fastapi_users_db_beanie import BeanieBaseUserDocument
from pydantic import BaseModel, ConfigDict, Field


def get_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


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
