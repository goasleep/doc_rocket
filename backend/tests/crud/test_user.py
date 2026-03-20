import pytest
from pwdlib.hashers.bcrypt import BcryptHasher

from app import crud
from app.core.security import verify_password
from app.models import User, UserCreate, UserUpdate
from tests.utils.utils import random_email, random_lower_string


@pytest.mark.anyio
async def test_create_user(db: None) -> None:
    email = random_email()
    password = random_lower_string()
    user_in = UserCreate(email=email, password=password)
    user = await crud.create_user(user_create=user_in)
    assert user.email == email
    assert hasattr(user, "hashed_password")


@pytest.mark.anyio
async def test_authenticate_user(db: None) -> None:
    email = random_email()
    password = random_lower_string()
    user_in = UserCreate(email=email, password=password)
    user = await crud.create_user(user_create=user_in)
    authenticated_user = await crud.authenticate(email=email, password=password)
    assert authenticated_user
    assert user.email == authenticated_user.email


@pytest.mark.anyio
async def test_not_authenticate_user(db: None) -> None:
    email = random_email()
    password = random_lower_string()
    user = await crud.authenticate(email=email, password=password)
    assert user is None


@pytest.mark.anyio
async def test_check_if_user_is_active(db: None) -> None:
    email = random_email()
    password = random_lower_string()
    user_in = UserCreate(email=email, password=password)
    user = await crud.create_user(user_create=user_in)
    assert user.is_active is True


@pytest.mark.anyio
async def test_check_if_user_is_active_inactive(db: None) -> None:
    email = random_email()
    password = random_lower_string()
    user_in = UserCreate(email=email, password=password, is_active=False)
    user = await crud.create_user(user_create=user_in)
    assert user.is_active is False


@pytest.mark.anyio
async def test_check_if_user_is_superuser(db: None) -> None:
    email = random_email()
    password = random_lower_string()
    user_in = UserCreate(email=email, password=password, is_superuser=True)
    user = await crud.create_user(user_create=user_in)
    assert user.is_superuser is True


@pytest.mark.anyio
async def test_check_if_user_is_superuser_normal_user(db: None) -> None:
    username = random_email()
    password = random_lower_string()
    user_in = UserCreate(email=username, password=password)
    user = await crud.create_user(user_create=user_in)
    assert user.is_superuser is False


@pytest.mark.anyio
async def test_get_user(db: None) -> None:
    password = random_lower_string()
    username = random_email()
    user_in = UserCreate(email=username, password=password, is_superuser=True)
    user = await crud.create_user(user_create=user_in)
    user_2 = await User.find_one(User.id == user.id)
    assert user_2
    assert user.email == user_2.email
    assert user.id == user_2.id
    assert user.is_superuser == user_2.is_superuser


@pytest.mark.anyio
async def test_update_user(db: None) -> None:
    password = random_lower_string()
    email = random_email()
    user_in = UserCreate(email=email, password=password, is_superuser=True)
    user = await crud.create_user(user_create=user_in)
    new_password = random_lower_string()
    user_in_update = UserUpdate(password=new_password, is_superuser=True)
    if user.id is not None:
        await crud.update_user(db_user=user, user_in=user_in_update)
    user_2 = await User.find_one(User.id == user.id)
    assert user_2
    assert user.email == user_2.email
    verified, _ = verify_password(new_password, user_2.hashed_password)
    assert verified


@pytest.mark.anyio
async def test_authenticate_user_with_bcrypt_upgrades_to_argon2(db: None) -> None:
    """Test that a user with bcrypt password hash gets upgraded to argon2 on login."""
    email = random_email()
    password = random_lower_string()

    # Create a bcrypt hash directly (simulating legacy password)
    bcrypt_hasher = BcryptHasher()
    bcrypt_hash = bcrypt_hasher.hash(password)
    assert bcrypt_hash.startswith("$2")  # bcrypt hashes start with $2

    # Create user with bcrypt hash directly in the database
    user = User(email=email, hashed_password=bcrypt_hash)
    await user.insert()

    # Verify the hash is bcrypt before authentication
    assert user.hashed_password.startswith("$2")

    # Authenticate - this should upgrade the hash to argon2
    authenticated_user = await crud.authenticate(email=email, password=password)
    assert authenticated_user
    assert authenticated_user.email == email

    user_db = await User.find_one(User.id == user.id)
    assert user_db

    # Verify the hash was upgraded to argon2
    assert user_db.hashed_password.startswith("$argon2")

    verified, updated_hash = verify_password(
        password, user_db.hashed_password
    )
    assert verified
    # Should not need another update since it's already argon2
    assert updated_hash is None
