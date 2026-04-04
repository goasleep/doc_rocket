import uuid

import pytest
from httpx import AsyncClient

from app.models import Article, ArticleAnalysis


@pytest.mark.anyio
async def test_bulk_delete_articles(client: AsyncClient, superuser_token_headers: dict[str, str]) -> None:
    # Create test articles and analyses
    article1 = Article(title="A1", content="c1")
    article2 = Article(title="A2", content="c2")
    article3 = Article(title="A3", content="c3")
    await article1.insert()
    await article2.insert()
    await article3.insert()

    analysis1 = ArticleAnalysis(article_id=article1.id, quality_score=50)
    analysis2 = ArticleAnalysis(article_id=article2.id, quality_score=60)
    await analysis1.insert()
    await analysis2.insert()

    response = await client.post(
        "/api/v1/articles/bulk-delete",
        headers=superuser_token_headers,
        json={"ids": [str(article1.id), str(article2.id)]},
    )
    assert response.status_code == 200
    assert response.json()["deleted_count"] == 2

    remaining_article = await Article.find_one(Article.id == article3.id)
    assert remaining_article is not None

    deleted_analysis1 = await ArticleAnalysis.find_one(ArticleAnalysis.article_id == article1.id)
    deleted_analysis2 = await ArticleAnalysis.find_one(ArticleAnalysis.article_id == article2.id)
    assert deleted_analysis1 is None
    assert deleted_analysis2 is None


@pytest.mark.anyio
async def test_bulk_delete_empty_ids(client: AsyncClient, superuser_token_headers: dict[str, str]) -> None:
    response = await client.post(
        "/api/v1/articles/bulk-delete",
        headers=superuser_token_headers,
        json={"ids": []},
    )
    assert response.status_code == 400


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
