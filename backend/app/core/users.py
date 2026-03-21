import uuid
from typing import Optional

from fastapi import Depends, Request
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users.password import PasswordHelper
from fastapi_users_db_beanie import BeanieUserDatabase
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher

from app.core.config import settings
from app.models import User

# Password helper: argon2 (primary) + bcrypt (legacy upgrade support)
_password_helper = PasswordHelper(PasswordHash((Argon2Hasher(), BcryptHasher())))


async def get_user_db():  # type: ignore[misc]
    yield BeanieUserDatabase(User)  # type: ignore[arg-type]


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = settings.SECRET_KEY  # type: ignore[assignment]
    verification_token_secret = settings.SECRET_KEY  # type: ignore[assignment]

    async def on_after_register(
        self, user: User, request: Optional[Request] = None
    ) -> None:
        pass

    async def on_after_forgot_password(
        self, user: User, token: str, request: Optional[Request] = None
    ) -> None:
        if settings.emails_enabled:
            from app.utils import generate_reset_password_email, send_email

            email_data = generate_reset_password_email(
                email_to=user.email, email=user.email, token=token
            )
            send_email(
                email_to=user.email,
                subject=email_data.subject,
                html_content=email_data.html_content,
            )

    async def on_after_request_verify(
        self, user: User, token: str, request: Optional[Request] = None
    ) -> None:
        pass


async def get_user_manager(user_db=Depends(get_user_db)):  # type: ignore[misc]
    yield UserManager(user_db, _password_helper)  # type: ignore[arg-type]


bearer_transport = BearerTransport(
    tokenUrl=f"{settings.API_V1_STR}/auth/jwt/login"
)


def get_jwt_strategy() -> JWTStrategy:  # type: ignore[type-arg]
    return JWTStrategy(
        secret=settings.SECRET_KEY,  # type: ignore[arg-type]
        lifetime_seconds=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])
current_active_user = fastapi_users.current_user(active=True)
current_superuser = fastapi_users.current_user(active=True, superuser=True)
