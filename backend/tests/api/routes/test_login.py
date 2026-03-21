from unittest.mock import patch

from httpx import AsyncClient
from pwdlib.hashers.bcrypt import BcryptHasher

from app.core.config import settings
from app.core.security import get_password_hash, verify_password
from app.models import User
from tests.utils.user import user_authentication_headers
from tests.utils.utils import random_email, random_lower_string


async def test_get_access_token(client: AsyncClient) -> None:
    login_data = {
        "username": settings.FIRST_SUPERUSER,
        "password": settings.FIRST_SUPERUSER_PASSWORD,
    }
    r = await client.post(f"{settings.API_V1_STR}/auth/jwt/login", data=login_data)
    tokens = r.json()
    assert r.status_code == 200
    assert "access_token" in tokens
    assert tokens["access_token"]


async def test_get_access_token_incorrect_password(client: AsyncClient) -> None:
    login_data = {
        "username": settings.FIRST_SUPERUSER,
        "password": "incorrect",
    }
    r = await client.post(f"{settings.API_V1_STR}/auth/jwt/login", data=login_data)
    assert r.status_code == 400


async def test_use_access_token(
    client: AsyncClient, superuser_token_headers: dict[str, str]
) -> None:
    r = await client.get(
        f"{settings.API_V1_STR}/users/me",
        headers=superuser_token_headers,
    )
    result = r.json()
    assert r.status_code == 200
    assert "email" in result


async def test_recovery_password(
    client: AsyncClient, normal_user_token_headers: dict[str, str]
) -> None:
    with (
        patch("app.core.config.settings.SMTP_HOST", "smtp.example.com"),
        patch("app.core.config.settings.SMTP_USER", "admin@example.com"),
    ):
        email = "test@example.com"
        r = await client.post(
            f"{settings.API_V1_STR}/auth/forgot-password",
            json={"email": email},
        )
        assert r.status_code == 202


async def test_recovery_password_user_not_exits(
    client: AsyncClient, normal_user_token_headers: dict[str, str]
) -> None:
    email = "nonexistent@example.com"
    r = await client.post(
        f"{settings.API_V1_STR}/auth/forgot-password",
        json={"email": email},
    )
    # fastapi-users always returns 202 to prevent email enumeration
    assert r.status_code == 202


async def test_reset_password_invalid_token(
    client: AsyncClient, superuser_token_headers: dict[str, str]
) -> None:
    data = {"token": "invalid", "password": "newpassword123"}
    r = await client.post(
        f"{settings.API_V1_STR}/auth/reset-password",
        json=data,
    )
    assert r.status_code == 400


async def test_login_with_bcrypt_password_upgrades_to_argon2(
    client: AsyncClient, db: None
) -> None:
    """Test that logging in with a bcrypt password hash upgrades it to argon2."""
    email = random_email()
    password = random_lower_string()

    bcrypt_hasher = BcryptHasher()
    bcrypt_hash = bcrypt_hasher.hash(password)
    assert bcrypt_hash.startswith("$2")

    user = User(email=email, hashed_password=bcrypt_hash, is_active=True)
    await user.insert()

    login_data = {"username": email, "password": password}
    r = await client.post(f"{settings.API_V1_STR}/auth/jwt/login", data=login_data)
    assert r.status_code == 200
    assert "access_token" in r.json()

    user_db = await User.find_one(User.id == user.id)
    assert user_db
    assert user_db.hashed_password.startswith("$argon2")

    verified, updated_hash = verify_password(password, user_db.hashed_password)
    assert verified
    assert updated_hash is None


async def test_login_with_argon2_password_keeps_hash(
    client: AsyncClient, db: None
) -> None:
    """Test that logging in with an argon2 password hash does not update it."""
    email = random_email()
    password = random_lower_string()

    argon2_hash = get_password_hash(password)
    assert argon2_hash.startswith("$argon2")

    user = User(email=email, hashed_password=argon2_hash, is_active=True)
    await user.insert()

    original_hash = user.hashed_password

    login_data = {"username": email, "password": password}
    r = await client.post(f"{settings.API_V1_STR}/auth/jwt/login", data=login_data)
    assert r.status_code == 200
    assert "access_token" in r.json()

    user_db = await User.find_one(User.id == user.id)
    assert user_db
    assert user_db.hashed_password == original_hash
    assert user_db.hashed_password.startswith("$argon2")
