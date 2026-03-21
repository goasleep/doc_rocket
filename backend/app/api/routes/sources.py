"""Source management routes — CRUD + manual fetch trigger + celery-redbeat scheduling."""
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser
from app.models import (
    Source,
    SourceCreate,
    SourcePublic,
    SourcesPublic,
    SourceUpdate,
    Message,
)

router = APIRouter(prefix="/sources", tags=["sources"])


def _update_redbeat(source: Source, action: str) -> None:
    """Add, update, or remove a celery-redbeat schedule entry for a source."""
    try:
        from redbeat import RedBeatSchedulerEntry
        from celery.schedules import crontab
        from app.celery_app import celery_app

        entry_name = f"fetch_source_{source.id}"

        if action == "delete":
            key = RedBeatSchedulerEntry.create_key(entry_name, celery_app)
            entry = RedBeatSchedulerEntry.from_key(key, app=celery_app)
            entry.delete()
            return

        interval = source.fetch_config.interval_minutes
        entry = RedBeatSchedulerEntry(
            name=entry_name,
            task="fetch_source_task",
            schedule=crontab(minute=f"*/{interval}"),
            args=[str(source.id)],
            enabled=source.is_active,
            app=celery_app,
        )
        entry.save()
    except Exception:
        pass  # Don't fail CRUD if redbeat isn't available (e.g. in tests)


@router.get("/", response_model=SourcesPublic)
async def list_sources(current_user: CurrentUser, skip: int = 0, limit: int = 100) -> Any:
    import asyncio
    count, sources = await asyncio.gather(
        Source.count(),
        Source.find_all().sort("-created_at").skip(skip).limit(limit).to_list(),
    )
    return SourcesPublic(data=sources, count=count)


@router.post("/", response_model=SourcePublic, status_code=201)
async def create_source(current_user: CurrentUser, body: SourceCreate) -> Any:
    # Validate: API type requires api_config
    if body.type == "api" and not body.api_config:
        raise HTTPException(status_code=422, detail="api_config is required for API type sources")

    # Check duplicate name
    existing = await Source.find_one(Source.name == body.name)
    if existing:
        raise HTTPException(status_code=400, detail="A source with this name already exists")

    source = Source(**body.model_dump())
    await source.insert()
    _update_redbeat(source, "create")
    return source


@router.get("/{id}", response_model=SourcePublic)
async def get_source(current_user: CurrentUser, id: uuid.UUID) -> Any:
    source = await Source.find_one(Source.id == id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


@router.patch("/{id}", response_model=SourcePublic)
async def update_source(current_user: CurrentUser, id: uuid.UUID, body: SourceUpdate) -> Any:
    source = await Source.find_one(Source.id == id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(source, field, value)
    await source.save()
    _update_redbeat(source, "update")
    return source


@router.delete("/{id}", status_code=204)
async def delete_source(current_user: CurrentUser, id: uuid.UUID) -> None:
    source = await Source.find_one(Source.id == id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    _update_redbeat(source, "delete")
    await source.delete()


@router.post("/{id}/fetch", status_code=202)
async def trigger_fetch(current_user: CurrentUser, id: uuid.UUID) -> Message:
    source = await Source.find_one(Source.id == id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    from app.tasks.fetch import fetch_source_task
    fetch_source_task.delay(str(id))
    return Message(message="Fetch task enqueued")
