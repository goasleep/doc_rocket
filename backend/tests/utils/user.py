import uuid

from httpx import AsyncClient

from app.core.config import settings
from app.core.security import get_password_hash
from app.core.users import UserManager, _password_helper
from app.models import User, UserCreate
from fastapi_users_db_beanie import BeanieUserDatabase
from tests.utils.utils import random_email, random_lower_string


def _make_manager() -> UserManager:
    user_db: BeanieUserDatabase = BeanieUserDatabase(User)  # type: ignore[type-arg,arg-type]
    return UserManager(user_db, _password_helper)  # type: ignore[arg-type]


async def user_authentication_headers(
    *, client: AsyncClient, email: str, password: str
) -> dict[str, str]:
    data = {"username": email, "password": password}
    r = await client.post(f"{settings.API_V1_STR}/auth/jwt/login", data=data)
    response = r.json()
    auth_token = response["access_token"]
    headers = {"Authorization": f"Bearer {auth_token}"}
    return headers


async def create_random_user() -> User:
    email = random_email()
    password = random_lower_string()
    user_in = UserCreate(email=email, password=password)
    manager = _make_manager()
    user = await manager.create(user_in)
    return user  # type: ignore[return-value]


async def authentication_token_from_email(
    *, client: AsyncClient, email: str
) -> dict[str, str]:
    """
    Return a valid token for the user with given email.

    If the user doesn't exist it is created first.
    """
    password = random_lower_string()
    user = await User.find_one(User.email == email)
    if not user:
        user_in = UserCreate(email=email, password=password)
        manager = _make_manager()
        await manager.create(user_in)
    else:
        # Update the password directly so we know what it is
        user.hashed_password = get_password_hash(password)
        await user.save()

    return await user_authentication_headers(client=client, email=email, password=password)
