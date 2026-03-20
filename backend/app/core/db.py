from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings
from app.models import Item, User, UserCreate


async def init_db() -> AsyncIOMotorClient:  # type: ignore[type-arg]
    client: AsyncIOMotorClient = AsyncIOMotorClient(settings.MONGODB_URL)  # type: ignore
    await init_beanie(
        database=client[settings.MONGODB_DB],
        document_models=[User, Item],
    )

    existing = await User.find_one(User.email == settings.FIRST_SUPERUSER)
    if not existing:
        from fastapi_users.db import BeanieUserDatabase
        from app.core.users import UserManager, _password_helper

        user_db: BeanieUserDatabase = BeanieUserDatabase(User)  # type: ignore[type-arg,misc]
        manager = UserManager(user_db, _password_helper)  # type: ignore[arg-type]
        await manager.create(
            UserCreate(
                email=settings.FIRST_SUPERUSER,
                password=settings.FIRST_SUPERUSER_PASSWORD,
                is_superuser=True,
            ),
            safe=False,
        )

    return client
