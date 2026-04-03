"""Draft management routes — CRUD, approve, export, rewrite-section, preview, publish."""
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from app.api.deps import CurrentUser
from app.core.markdown import markdown_to_wechat_html
from app.core.wechat_mp import WeChatMPClient, WeChatMPError
from app.models import (
    Draft,
    DraftPublic,
    DraftsPublic,
    DraftUpdate,
    EditHistoryEntry,
    Message,
    PublishHistory,
    RewriteSectionRequest,
    RewriteSectionResponse,
)


class DraftPreviewResponse(BaseModel):
    """Response schema for draft preview."""
    title: str
    html_content: str


class PublishRequest(BaseModel):
    """Request schema for publishing a draft."""
    confirmed: bool = False


class PublishResponse(BaseModel):
    """Response schema for publish operation."""
    success: bool
    publish_id: str | None = None
    article_url: str | None = None
    message: str

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


@router.post("/{id}/preview", response_model=DraftPreviewResponse)
async def preview_draft(
    current_user: CurrentUser, id: uuid.UUID
) -> Any:
    """Preview draft content as WeChat MP compatible HTML."""
    draft = await Draft.find_one(Draft.id == id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    html_content = markdown_to_wechat_html(draft.content, draft.title)
    return DraftPreviewResponse(title=draft.title, html_content=html_content)


@router.post("/{id}/publish", response_model=PublishResponse)
async def publish_draft(
    current_user: CurrentUser, id: uuid.UUID, body: PublishRequest
) -> Any:
    """Publish draft to WeChat MP.

    Requires confirmed=True to proceed with publishing.
    Creates a PublishHistory record to track the publish attempt.
    """
    if not body.confirmed:
        raise HTTPException(
            status_code=400,
            detail="Publication must be confirmed by setting confirmed=true"
        )

    draft = await Draft.find_one(Draft.id == id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    # Create PublishHistory record with pending status
    publish_history = PublishHistory(
        draft_id=draft.id,
        title=draft.title,
        target_platform="wechat_mp",
        target_name="",  # Will be updated after getting account info
        status="pending",
    )
    await publish_history.insert()

    try:
        # Get WeChat MP client from config
        client = await WeChatMPClient.from_config()

        # Get account info for target_name
        try:
            account_info = await client.get_account_info()
            publish_history.target_name = account_info.get("nick_name", "Unknown")
        except WeChatMPError:
            publish_history.target_name = "WeChat MP"

        # Convert content to HTML
        html_content = markdown_to_wechat_html(draft.content, draft.title)

        # Create draft on WeChat MP
        media_id = await client.add_draft(
            title=draft.title,
            content=html_content,
        )

        # Submit for publishing
        publish_id = await client.submit_publish(media_id=media_id)

        # Update PublishHistory with success
        publish_history.status = "success"
        publish_history.publish_id = publish_id
        publish_history.updated_at = datetime.now(timezone.utc)
        await publish_history.save()

        # Close client
        await client.close()

        return PublishResponse(
            success=True,
            publish_id=publish_id,
            message="Draft published successfully to WeChat MP"
        )

    except WeChatMPError as e:
        # Update PublishHistory with failure
        publish_history.status = "failed"
        publish_history.error_message = str(e)
        publish_history.updated_at = datetime.now(timezone.utc)
        await publish_history.save()

        raise HTTPException(
            status_code=502,
            detail=f"WeChat MP API error: {str(e)}"
        )
    except Exception as e:
        # Update PublishHistory with failure
        publish_history.status = "failed"
        publish_history.error_message = str(e)
        publish_history.updated_at = datetime.now(timezone.utc)
        await publish_history.save()

        raise HTTPException(
            status_code=502,
            detail=f"Failed to publish: {str(e)}"
        )
