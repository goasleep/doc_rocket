import pytest
from pwdlib.hashers.bcrypt import BcryptHasher

from app.core.security import verify_password
from app.core.users import UserManager, _password_helper
from app.models import User, UserCreate
from fastapi_users_db_beanie import BeanieUserDatabase
from tests.utils.utils import random_email, random_lower_string


def _make_manager() -> UserManager:
    user_db: BeanieUserDatabase = BeanieUserDatabase(User)  # type: ignore[type-arg,arg-type]
    return UserManager(user_db, _password_helper)  # type: ignore[arg-type]


@pytest.mark.anyio
async def test_create_user(db: None) -> None:
    email = random_email()
    password = random_lower_string()
    user_in = UserCreate(email=email, password=password)
    manager = _make_manager()
    user = await manager.create(user_in)
    assert user.email == email
    assert hasattr(user, "hashed_password")


@pytest.mark.anyio
async def test_not_authenticate_user(db: None) -> None:
    """Verifying a wrong password fails."""
    email = random_email()
    password = random_lower_string()
    wrong_password = random_lower_string()
    user_in = UserCreate(email=email, password=password)
    manager = _make_manager()
    user = await manager.create(user_in)
    verified, _ = manager.password_helper.verify_and_update(
        wrong_password, user.hashed_password
    )
    assert not verified


@pytest.mark.anyio
async def test_check_if_user_is_active(db: None) -> None:
    email = random_email()
    password = random_lower_string()
    user_in = UserCreate(email=email, password=password)
    manager = _make_manager()
    user = await manager.create(user_in)
    assert user.is_active is True


@pytest.mark.anyio
async def test_check_if_user_is_active_inactive(db: None) -> None:
    email = random_email()
    password = random_lower_string()
    user_in = UserCreate(email=email, password=password, is_active=False)
    manager = _make_manager()
    user = await manager.create(user_in, safe=False)
    assert user.is_active is False


@pytest.mark.anyio
async def test_check_if_user_is_superuser(db: None) -> None:
    email = random_email()
    password = random_lower_string()
    user_in = UserCreate(email=email, password=password, is_superuser=True)
    manager = _make_manager()
    user = await manager.create(user_in, safe=False)
    assert user.is_superuser is True


@pytest.mark.anyio
async def test_check_if_user_is_superuser_normal_user(db: None) -> None:
    email = random_email()
    password = random_lower_string()
    user_in = UserCreate(email=email, password=password)
    manager = _make_manager()
    user = await manager.create(user_in)
    assert user.is_superuser is False


@pytest.mark.anyio
async def test_get_user(db: None) -> None:
    password = random_lower_string()
    email = random_email()
    user_in = UserCreate(email=email, password=password, is_superuser=True)
    manager = _make_manager()
    user = await manager.create(user_in, safe=False)
    user_2 = await User.find_one(User.id == user.id)
    assert user_2
    assert user.email == user_2.email
    assert user.id == user_2.id
    assert user.is_superuser == user_2.is_superuser


@pytest.mark.anyio
async def test_update_user_password(db: None) -> None:
    password = random_lower_string()
    email = random_email()
    user_in = UserCreate(email=email, password=password, is_superuser=True)
    manager = _make_manager()
    user = await manager.create(user_in, safe=False)
    new_password = random_lower_string()
    # Update password directly via Beanie save
    user.hashed_password = manager.password_helper.hash(new_password)
    await user.save()
    user_2 = await User.find_one(User.id == user.id)
    assert user_2
    assert user.email == user_2.email
    verified, _ = verify_password(new_password, user_2.hashed_password)
    assert verified


@pytest.mark.anyio
async def test_password_helper_bcrypt_upgrades_to_argon2(db: None) -> None:
    """Test that verify_and_update upgrades bcrypt hashes to argon2."""
    email = random_email()
    password = random_lower_string()

    bcrypt_hasher = BcryptHasher()
    bcrypt_hash = bcrypt_hasher.hash(password)
    assert bcrypt_hash.startswith("$2")

    user = User(email=email, hashed_password=bcrypt_hash, is_active=True)
    await user.insert()

    manager = _make_manager()
    verified, updated_hash = manager.password_helper.verify_and_update(
        password, user.hashed_password
    )
    assert verified
    assert updated_hash is not None
    assert updated_hash.startswith("$argon2")

    # Save the updated hash (simulating what UserManager.authenticate does)
    user.hashed_password = updated_hash
    await user.save()

    user_db = await User.find_one(User.id == user.id)
    assert user_db
    assert user_db.hashed_password.startswith("$argon2")
    verified2, updated2 = verify_password(password, user_db.hashed_password)
    assert verified2
    assert updated2 is None
