import asyncio
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi_users.exceptions import UserAlreadyExists

from app.api.deps import (
    CurrentUser,
    get_current_active_superuser,
)
from app.core.config import settings
from app.core.users import UserManager, get_user_manager
from app.models import (
    Item,
    Message,
    UpdatePassword,
    User,
    UserCreate,
    UserRead,
    UsersPublic,
)
from app.utils import generate_new_account_email, send_email

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=UsersPublic,
)
async def read_users(skip: int = 0, limit: int = 100) -> Any:
    """
    Retrieve users.
    """
    count, users = await asyncio.gather(
        User.count(),
        User.find_all().sort("-created_at").skip(skip).limit(limit).to_list(),
    )
    return UsersPublic(data=users, count=count)


@router.post(
    "/", dependencies=[Depends(get_current_active_superuser)], response_model=UserRead
)
async def create_user(
    *,
    background_tasks: BackgroundTasks,
    user_in: UserCreate,
    user_manager: UserManager = Depends(get_user_manager),
) -> Any:
    """
    Create new user.
    """
    try:
        user = await user_manager.create(user_in, safe=False)
    except UserAlreadyExists:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )
    if settings.emails_enabled and user_in.email:
        email_data = generate_new_account_email(
            email_to=user_in.email, username=user_in.email, password=user_in.password
        )
        background_tasks.add_task(
            send_email,
            email_to=user_in.email,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )
    return user


@router.patch("/me/password", response_model=Message)
async def update_password_me(
    *,
    body: UpdatePassword,
    current_user: CurrentUser,
    user_manager: UserManager = Depends(get_user_manager),
) -> Any:
    """
    Update own password.
    """
    verified, _ = user_manager.password_helper.verify_and_update(
        body.current_password, current_user.hashed_password
    )
    if not verified:
        raise HTTPException(status_code=400, detail="Incorrect password")
    if body.current_password == body.new_password:
        raise HTTPException(
            status_code=400, detail="New password cannot be the same as the current one"
        )
    current_user.hashed_password = user_manager.password_helper.hash(body.new_password)
    await current_user.save()
    return Message(message="Password updated successfully")


@router.delete("/me", response_model=Message)
async def delete_user_me(current_user: CurrentUser) -> Any:
    """
    Delete own user.
    """
    if current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="Super users are not allowed to delete themselves"
        )
    await Item.find(Item.owner_id == current_user.id).delete()
    await current_user.delete()
    return Message(message="User deleted successfully")
