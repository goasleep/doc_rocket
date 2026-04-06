"""Manual article submission — text mode and URL mode."""
import re
from typing import Any

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from app.api.deps import CurrentUser
from app.models import Article
from app.tasks.fetch import fetch_url_and_analyze_task
from beanie.operators import In

router = APIRouter(prefix="/submit", tags=["submit"])


class SubmitText(BaseModel):
    mode: str = "text"  # "text" | "url"
    title: str = ""
    content: str = ""
    url: str = ""


class SubmitResponse(BaseModel):
    article_id: str
    status: str
    message: str


class SubmitUrlsBatch(BaseModel):
    urls: str  # 多行文本，换行或分号分隔


class SubmitBatchResponse(BaseModel):
    total: int      # 总共解析出的 URL 数
    accepted: int   # 新接受的任务数
    skipped: int    # 跳过的重复数
    message: str


@router.post("/", response_model=SubmitResponse)
async def submit_article(
    current_user: CurrentUser, body: SubmitText, response: Response
) -> Any:
    if body.mode == "url":
        if not body.url:
            raise HTTPException(status_code=422, detail="url is required for URL mode")

        # Dedup: check if URL already exists
        existing = await Article.find_one(Article.url == body.url)
        if existing:
            return SubmitResponse(
                article_id=str(existing.id),
                status=existing.status,
                message="Article with this URL already exists",
            )

        # Enqueue async fetch + analyze
        fetch_url_and_analyze_task.apply_async(
            args=[body.url, str(current_user.id)],
        )

        response.status_code = 202
        return SubmitResponse(
            article_id="",
            status="pending",
            message="URL fetch task enqueued. Check /articles for status.",
        )

    else:
        # Text mode
        if not body.content:
            raise HTTPException(status_code=422, detail="content is required for text mode")

        article = Article(
            title=body.title or "Untitled",
            content=body.content,
            status="raw",
            input_type="manual",
        )
        await article.insert()

        from app.models import TaskRun

        refine_task_run = TaskRun(
            task_type="refine",
            triggered_by="manual",
            entity_type="article",
            entity_id=article.id,
            entity_name=article.title,
            status="pending",
        )
        await refine_task_run.insert()

        from app.tasks.refine import refine_article_task

        result = refine_article_task.apply_async(
            args=[str(article.id)],
            kwargs={"task_run_id": str(refine_task_run.id)},
            task_id=f"refine_{article.id}",
        )
        refine_task_run.celery_task_id = result.id
        await refine_task_run.save()

        response.status_code = 201
        return SubmitResponse(
            article_id=str(article.id),
            status="raw",
            message="Article submitted and analysis enqueued",
        )


def parse_urls(text: str) -> list[str]:
    """从文本中解析 URL，支持换行符、分号、逗号分隔。"""
    # 按分隔符分割
    parts = re.split(r'[\n;]+', text)

    urls = []
    for part in parts:
        # 清理空白
        url = part.strip()
        # 去除可能的逗号后缀
        url = url.rstrip(',')
        # 跳过空字符串
        if not url:
            continue
        # 基本 URL 验证（以 http:// 或 https:// 开头）
        if url.startswith(('http://', 'https://')):
            urls.append(url)

    return urls


@router.post("/batch", response_model=SubmitBatchResponse)
async def submit_urls_batch(
    current_user: CurrentUser, body: SubmitUrlsBatch, response: Response
) -> Any:
    """批量提交 URL 进行抓取和分析。"""
    urls = parse_urls(body.urls)

    if not urls:
        raise HTTPException(status_code=422, detail="未找到有效的 URL")

    # 去重：同一批次内的重复 URL
    unique_urls = list(dict.fromkeys(urls))

    # Bulk check existing URLs
    existing_urls = {
        a.url
        for a in await Article.find(In(Article.url, unique_urls)).to_list()
    }

    accepted = 0
    skipped = 0

    for url in unique_urls:
        if url in existing_urls:
            skipped += 1
            continue

        fetch_url_and_analyze_task.apply_async(
            args=[url, str(current_user.id)],
        )
        accepted += 1

    response.status_code = 202
    return SubmitBatchResponse(
        total=len(unique_urls),
        accepted=accepted,
        skipped=skipped,
        message=f"已提交 {accepted} 个 URL 进行抓取，跳过 {skipped} 个重复",
    )
