import pytest
from httpx import AsyncClient

from app.models import Article


@pytest.mark.anyio
async def test_list_articles_search(client: AsyncClient, superuser_token_headers: dict[str, str]) -> None:
    article1 = Article(title="FastAPI tutorial", content="c1")
    article2 = Article(title="React patterns", content="c2")
    await article1.insert()
    await article2.insert()

    response = await client.get(
        "/api/v1/articles/?search=fastapi",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert len(data["data"]) == 1
    assert data["data"][0]["title"] == "FastAPI tutorial"
