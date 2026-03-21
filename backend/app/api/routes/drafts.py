"""Draft management routes — CRUD, approve, export, rewrite-section."""
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.api.deps import CurrentUser
from app.models import (
    Draft,
    DraftPublic,
    DraftsPublic,
    DraftUpdate,
    EditHistoryEntry,
    Message,
    RewriteSectionRequest,
    RewriteSectionResponse,
)

router = APIRouter(prefix="/drafts", tags=["drafts"])


@router.get("/", response_model=DraftsPublic)
async def list_drafts(
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
    status: str | None = None,
) -> Any:
    import asyncio

    if status:
        query = Draft.find(Draft.status == status)
    else:
        query = Draft.find_all()

    count, drafts = await asyncio.gather(
        query.count(),
        query.sort("-created_at").skip(skip).limit(limit).to_list(),
    )
    return DraftsPublic(data=drafts, count=count)


@router.get("/{id}", response_model=DraftPublic)
async def get_draft(current_user: CurrentUser, id: uuid.UUID) -> Any:
    draft = await Draft.find_one(Draft.id == id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


@router.patch("/{id}", response_model=DraftPublic)
async def update_draft(current_user: CurrentUser, id: uuid.UUID, body: DraftUpdate) -> Any:
    draft = await Draft.find_one(Draft.id == id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    update_data = body.model_dump(exclude_unset=True)

    # Save current content to history before overwriting
    if "content" in update_data and update_data["content"] != draft.content:
        draft.edit_history.append(EditHistoryEntry(content=draft.content))

    for field, value in update_data.items():
        setattr(draft, field, value)
    await draft.save()
    return draft


@router.delete("/{id}", status_code=204)
async def delete_draft(current_user: CurrentUser, id: uuid.UUID) -> None:
    draft = await Draft.find_one(Draft.id == id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    await draft.delete()


@router.post("/{id}/approve", response_model=DraftPublic)
async def approve_draft(current_user: CurrentUser, id: uuid.UUID) -> Any:
    draft = await Draft.find_one(Draft.id == id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    draft.status = "approved"
    await draft.save()
    return draft


@router.get("/{id}/export")
async def export_draft(
    current_user: CurrentUser, id: uuid.UUID, format: str = "markdown"
) -> Response:
    draft = await Draft.find_one(Draft.id == id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    filename = f"draft_{draft.id}.md"
    content = f"# {draft.title}\n\n{draft.content}"
    return Response(
        content=content,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{id}/rewrite-section", response_model=RewriteSectionResponse)
async def rewrite_section(
    current_user: CurrentUser, id: uuid.UUID, body: RewriteSectionRequest
) -> Any:
    """Rewrite selected text using EditorAgent (synchronous — user waits for result)."""
    from app.tasks.rewrite import _rewrite_section_async

    draft = await Draft.find_one(Draft.id == id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    rewritten = await _rewrite_section_async(
        draft_id=str(id),
        selected_text=body.selected_text,
        context=body.context,
    )
    return RewriteSectionResponse(rewritten_text=rewritten)
