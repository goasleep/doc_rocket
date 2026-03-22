"""Manual article submission — text mode and URL mode."""
from typing import Any

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from app.api.deps import CurrentUser
from app.models import Article
from app.tasks.fetch import fetch_url_and_analyze_task

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
