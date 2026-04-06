"""Draft management routes — CRUD, approve, export, rewrite-section, preview, publish."""
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel

from app.api.deps import CurrentUser
from app.core.config import settings
from app.core.image import ImageProcessError, process_cover_image
from app.core.markdown import extract_images_from_markdown, markdown_to_wechat_html
from app.core.qiniu_oss import QiniuOSSClient
from app.core.wechat_mp import WeChatMPClient, WeChatMPError
from app.models import (
    Draft,
    DraftPublic,
    DraftsPublic,
    DraftUpdate,
    EditHistoryEntry,
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
    theme: str = "qing-mo"  # Theme to use for styling


class PublishResponse(BaseModel):
    """Response schema for publish operation."""
    success: bool
    publish_id: str | None = None
    article_url: str | None = None
    message: str


class CoverUploadResponse(BaseModel):
    """Response schema for cover image upload."""
    cover_image_url: str
    thumb_media_id: str


router = APIRouter(prefix="/drafts", tags=["drafts"])


@router.get("/themes")
async def get_themes(current_user: CurrentUser) -> dict[str, str]:
    """Get available markdown themes for WeChat MP publishing.

    Returns:
        Dictionary mapping theme names to descriptions.
    """
    from app.core.markdown_themes import get_available_themes
    return get_available_themes()


@router.post("/{id}/upload-cover", response_model=CoverUploadResponse)
async def upload_cover_image(
    current_user: CurrentUser,
    id: uuid.UUID,
    file: UploadFile,
) -> Any:
    """Upload cover image for draft.

    Processes the image (resize to 900x500, compress),
    uploads to Qiniu OSS for permanent storage,
    uploads to WeChat MP for thumb_media_id,
    and saves both to the draft.

    Args:
        current_user: Current authenticated user
        id: Draft ID
        file: Image file to upload

    Returns:
        CoverUploadResponse with cover_image_url and thumb_media_id

    Raises:
        HTTPException: If draft not found, image processing fails,
                      or WeChat MP upload fails
    """
    # Get draft
    draft = await Draft.find_one(Draft.id == id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    # Validate file type
    allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. "
                   f"Allowed: {', '.join(allowed_types)}"
        )

    # Read file
    image_data = await file.read()
    if len(image_data) > 10 * 1024 * 1024:  # 10MB max
        raise HTTPException(
            status_code=413,
            detail="File too large. Maximum size is 10MB."
        )

    # Process image
    try:
        processed_data = process_cover_image(image_data)
    except ImageProcessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Upload to Qiniu
    try:
        qiniu_client = QiniuOSSClient.from_settings()
        key = qiniu_client.generate_key(processed_data, "covers", "jpg")
        cover_image_url = await qiniu_client.upload_file(processed_data, key)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to upload to Qiniu: {exc}"
        ) from exc

    # Upload to WeChat MP to get thumb_media_id
    try:
        wechat_client = await WeChatMPClient.from_config()
        thumb_media_id = await wechat_client.upload_media(processed_data, "cover.jpg")
    except WeChatMPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to upload to WeChat MP: {exc}"
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"WeChat MP not configured: {exc}"
        ) from exc

    # Save to draft
    draft.cover_image_url = cover_image_url
    draft.thumb_media_id = thumb_media_id
    await draft.save()

    return CoverUploadResponse(
        cover_image_url=cover_image_url,
        thumb_media_id=thumb_media_id,
    )


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
    current_user: CurrentUser, id: uuid.UUID, theme: str = "qing-mo"
) -> Any:
    """Preview draft content as WeChat MP compatible HTML.

    Args:
        current_user: Current authenticated user
        id: Draft ID
        theme: Theme to use for styling. Options: qing-mo, github-markdown, github-markdown-light, github-markdown-dark, etc.
    """
    draft = await Draft.find_one(Draft.id == id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    html_content = markdown_to_wechat_html(draft.content, draft.title, theme=theme)
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

    # Check cover image is uploaded
    if not draft.thumb_media_id:
        raise HTTPException(
            status_code=400,
            detail="Cover image is required. Please upload a cover image first."
        )

    # Create PublishHistory record with pending status
    publish_history = PublishHistory(
        draft_id=draft.id,
        title=draft.title,
        target_platform="wechat_mp",
        target_name="",  # Will be updated after getting account info
        status="pending",
    )
    await publish_history.insert()

    client: WeChatMPClient | None = None
    failed_image_urls: list[str] = []

    try:
        # Get WeChat MP client from config
        client = await WeChatMPClient.from_config()

        # Get account info for target_name
        try:
            account_info = await client.get_account_info()
            publish_history.target_name = account_info.get("nick_name", "Unknown")
        except WeChatMPError:
            publish_history.target_name = "WeChat MP"

        # Sync Qiniu images to WeChat MP before publishing
        qiniu_domain = settings.QINIU_DOMAIN.rstrip("/")
        if qiniu_domain and draft.content:
            image_urls = extract_images_from_markdown(draft.content)
            qiniu_urls = [url for url in image_urls if url.startswith(qiniu_domain)]
            if qiniu_urls:
                image_replacements: dict[str, str] = {}
                async with httpx.AsyncClient(timeout=30.0) as http_client:
                    for raw_url in qiniu_urls:
                        try:
                            response = await http_client.get(raw_url)
                            response.raise_for_status()
                            image_data = response.content
                            filename = (raw_url.split("/")[-1] or "image.jpg").split("?")[0]
                            mp_url = await client.upload_image(image_data, filename)
                            image_replacements[raw_url] = mp_url
                        except Exception as exc:  # noqa: BLE001
                            logging.warning("Failed to sync Qiniu image %s to WeChat MP: %s", raw_url, exc)
                            failed_image_urls.append(raw_url)

                for raw_url, mp_url in image_replacements.items():
                    draft.content = draft.content.replace(raw_url, mp_url)

                # Persist updated content with replaced image URLs
                await draft.save()

        # Convert content to HTML with selected theme
        html_content = markdown_to_wechat_html(draft.content, draft.title, theme=body.theme)

        # Create draft on WeChat MP with thumb_media_id
        media_id = await client.add_draft(
            title=draft.title,
            content=html_content,
            thumb_media_id=draft.thumb_media_id,
        )

        # Submit for publishing
        publish_id = await client.submit_publish(media_id=media_id)

        # Update PublishHistory with success
        publish_history.status = "success"
        publish_history.publish_id = publish_id
        publish_history.updated_at = datetime.now(timezone.utc)
        await publish_history.save()

        message = "Draft published successfully to WeChat MP"
        if failed_image_urls:
            message += f" (failed to sync {len(failed_image_urls)} image(s))"

        return PublishResponse(
            success=True,
            publish_id=publish_id,
            message=message
        )

    except WeChatMPError as e:
        # Update PublishHistory with failure
        publish_history.status = "failed"
        publish_history.error_message = str(e)
        publish_history.updated_at = datetime.now(timezone.utc)
        await publish_history.save()

        # Provide more helpful error message for common errors
        error_msg = str(e)
        if "api unauthorized" in error_msg.lower() or "48001" in error_msg:
            error_msg = (
                "微信公众号未认证，无法发布文章。\n"
                "草稿已成功创建到微信草稿箱，但发布功能需要完成微信认证。\n"
                "请登录微信公众平台完成认证，或手动在后台发布草稿。"
            )
        elif "invalid media_id" in error_msg.lower() or "40007" in error_msg:
            error_msg = (
                "封面图片无效。请重新上传封面图片后再试。"
            )

        raise HTTPException(
            status_code=502,
            detail=f"WeChat MP API error: {error_msg}"
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
    finally:
        if client is not None:
            await client.close()
