"""Article management routes."""
import re
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.deps import CurrentUser
from app.models import Article, ArticleAnalysis, ArticleDetail, ArticlePublic, ArticlesPublic


class ArticleTitleUpdate(BaseModel):
    title: str

router = APIRouter(prefix="/articles", tags=["articles"])


@router.get("/", response_model=ArticlesPublic)
async def list_articles(
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
    status: str | None = None,
    source_id: uuid.UUID | None = None,
    input_type: str | None = None,
    sort: str = "created_at",
    search: str | None = None,
) -> Any:
    import asyncio
    from beanie.operators import RegEx

    filters: list[Any] = [Article.status != "archived"]
    if status:
        filters = [Article.status == status]
    if source_id:
        filters.append(Article.source_id == source_id)
    if input_type:
        filters.append(Article.input_type == input_type)
    if search:
        filters.append(RegEx(Article.title, re.escape(search), options="i"))

    query = Article.find(*filters)

    count, articles = await asyncio.gather(
        query.count(),
        query.sort("-created_at").skip(skip).limit(limit).to_list(),
    )

    # Build public list (exclude content, optionally join quality_score)
    public_items = []
    for art in articles:
        analysis = await ArticleAnalysis.find_one(ArticleAnalysis.article_id == art.id)
        public_items.append(ArticlePublic(
            id=art.id,
            source_id=art.source_id,
            title=art.title,
            url=art.url,
            author=art.author,
            published_at=art.published_at,
            status=art.status,
            input_type=art.input_type,
            refine_status=art.refine_status,
            created_at=art.created_at,
            quality_score=analysis.quality_score if analysis else None,
        ))

    return ArticlesPublic(data=public_items, count=count)


@router.get("/{id}", response_model=ArticleDetail)
async def get_article(current_user: CurrentUser, id: uuid.UUID) -> Any:
    article = await Article.find_one(Article.id == id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    analysis = await ArticleAnalysis.find_one(ArticleAnalysis.article_id == id)
    analysis_dict = analysis.model_dump() if analysis else None

    return ArticleDetail(
        id=article.id,
        source_id=article.source_id,
        title=article.title,
        content=article.content,
        url=article.url,
        author=article.author,
        published_at=article.published_at,
        status=article.status,
        input_type=article.input_type,
        refine_status=article.refine_status,
        content_md=article.content_md,
        created_at=article.created_at,
        quality_score=analysis.quality_score if analysis else None,
        analysis=analysis_dict,
    )


@router.post("/{id}/refetch", status_code=202)
async def refetch_article(current_user: CurrentUser, id: uuid.UUID) -> Any:
    """Re-fetch the original URL for an existing article, bypassing duplicate checks."""
    from app.tasks.fetch import refetch_article_task

    article = await Article.find_one(Article.id == id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    if not article.url:
        raise HTTPException(status_code=400, detail="Article has no URL to re-fetch")

    refetch_article_task.apply_async(args=[str(id)])
    return {"message": "重新抓取已触发", "article_id": str(id)}


@router.patch("/{id}/title", response_model=ArticlePublic)
async def update_article_title(current_user: CurrentUser, id: uuid.UUID, body: ArticleTitleUpdate) -> Any:
    """Update the title of an article."""
    article = await Article.find_one(Article.id == id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    article.title = body.title.strip()
    await article.save()
    return ArticlePublic(
        id=article.id,
        source_id=article.source_id,
        title=article.title,
        url=article.url,
        author=article.author,
        published_at=article.published_at,
        status=article.status,
        input_type=article.input_type,
        refine_status=article.refine_status,
        created_at=article.created_at,
        quality_score=None,
    )


@router.delete("/{id}", response_model=ArticlePublic)
async def archive_article(current_user: CurrentUser, id: uuid.UUID) -> Any:
    article = await Article.find_one(Article.id == id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    article.status = "archived"
    await article.save()
    return ArticlePublic(
        id=article.id,
        source_id=article.source_id,
        title=article.title,
        url=article.url,
        author=article.author,
        published_at=article.published_at,
        status=article.status,
        input_type=article.input_type,
        refine_status=article.refine_status,
        created_at=article.created_at,
        quality_score=None,
    )
