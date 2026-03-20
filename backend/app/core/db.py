from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from app import crud
from app.core.config import settings
from app.models import Item, User, UserCreate


async def init_db() -> AsyncIOMotorClient:
    client: AsyncIOMotorClient = AsyncIOMotorClient(settings.MONGODB_URL)  # type: ignore
    await init_beanie(
        database=client[settings.MONGODB_DB],
        document_models=[User, Item],
    )

    user = await User.find_one(User.email == settings.FIRST_SUPERUSER)
    if not user:
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            is_superuser=True,
        )
        await crud.create_user(user_create=user_in)

    return client
