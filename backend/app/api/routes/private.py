from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.users import UserManager, get_user_manager
from app.models import UserCreate, UserRead

router = APIRouter(tags=["private"], prefix="/private")


class PrivateUserCreate(BaseModel):
    email: str
    password: str
    full_name: str
    is_verified: bool = False


@router.post("/users/", response_model=UserRead)
async def create_user(
    user_in: PrivateUserCreate,
    user_manager: UserManager = Depends(get_user_manager),
) -> Any:
    """
    Create a new user.
    """
    user_create = UserCreate(
        email=user_in.email,
        full_name=user_in.full_name,
        password=user_in.password,
    )
    user = await user_manager.create(user_create)
    return user
