from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.db import init_db
from app.main import app
from app.models import (
    Item,
    User,
    Source,
    Article,
    ArticleAnalysis,
    AgentConfig,
    WorkflowRun,
    Draft,
    SystemConfig,
)
from tests.utils.user import authentication_token_from_email
from tests.utils.utils import get_superuser_token_headers


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="session")
async def db() -> AsyncGenerator[None, None]:
    client = await init_db()

    yield

    await Item.delete_all()
    await User.delete_all()
    await Source.delete_all()
    await Article.delete_all()
    await ArticleAnalysis.delete_all()
    await AgentConfig.delete_all()
    await WorkflowRun.delete_all()
    await Draft.delete_all()
    await SystemConfig.delete_all()
    client.close()


@pytest.fixture(scope="module")
async def client(db: None) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


@pytest.fixture(scope="module")
async def superuser_token_headers(client: AsyncClient) -> dict[str, str]:
    return await get_superuser_token_headers(client)


@pytest.fixture(scope="module")
async def normal_user_token_headers(client: AsyncClient) -> dict[str, str]:
    return await authentication_token_from_email(
        client=client, email=settings.EMAIL_TEST_USER
    )
