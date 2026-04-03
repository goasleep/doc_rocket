"""Publish history routes — list and check status."""
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.deps import CurrentUser
from app.core.wechat_mp import WeChatMPClient, WeChatMPError
from app.models import PublishHistory, PublishHistoriesPublic


class PublishStatusResponse(BaseModel):
    """Response schema for publish status check."""
    status: str
    article_url: str | None = None
    raw_data: dict[str, Any] | None = None


# WeChat publish status codes
PUBLISH_STATUS_SUCCESS = "0"  # Published successfully
PUBLISH_STATUS_PUBLISHING = "1"  # Publishing in progress
PUBLISH_STATUS_FAIL_ORIGINAL = "2"  # Original check failed
PUBLISH_STATUS_FAIL_AUDIT = "3"  # Audit failed
PUBLISH_STATUS_FAIL = "4"  # Publish failed

router = APIRouter(prefix="/publish-history", tags=["publish-history"])


@router.get("/", response_model=PublishHistoriesPublic)
async def list_publish_history(
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
    status: str | None = None,
) -> Any:
    """List publish history with optional status filter."""
    import asyncio

    if status:
        query = PublishHistory.find(PublishHistory.status == status)
    else:
        query = PublishHistory.find_all()

    count, histories = await asyncio.gather(
        query.count(),
        query.sort("-created_at").skip(skip).limit(limit).to_list(),
    )
    return PublishHistoriesPublic(data=histories, count=count)


@router.get("/{id}/status", response_model=PublishStatusResponse)
async def check_publish_status(
    current_user: CurrentUser,
    id: uuid.UUID,
) -> Any:
    """Check publish status from WeChat MP API and update local record.

    If the publish history has a publish_id, queries WeChat MP API for
    the latest status and updates the local record accordingly.
    """
    history = await PublishHistory.find_one(PublishHistory.id == id)
    if not history:
        raise HTTPException(status_code=404, detail="Publish history not found")

    # If no publish_id, return current status without querying WeChat
    if not history.publish_id:
        return PublishStatusResponse(
            status=history.status,
            article_url=history.published_url,
            raw_data=None,
        )

    try:
        # Get WeChat MP client and check status
        client = await WeChatMPClient.from_config()
        status_data = await client.get_publish_status(history.publish_id)
        await client.close()

        # Parse WeChat status
        wechat_status = str(status_data.get("publish_status", ""))
        article_url: str | None = None

        # Map WeChat status to our status and extract URL
        if wechat_status == PUBLISH_STATUS_SUCCESS:
            history.status = "success"
            # Extract article URL from response
            article_detail = status_data.get("article_detail", {})
            if article_detail:
                # article_detail is a dict with article_ids as keys
                # Each value contains article_url
                for article_id, article_info in article_detail.items():
                    if isinstance(article_info, dict) and "article_url" in article_info:
                        article_url = article_info["article_url"]
                        break
            if article_url:
                history.published_url = article_url
        elif wechat_status == PUBLISH_STATUS_PUBLISHING:
            history.status = "pending"
        elif wechat_status in (PUBLISH_STATUS_FAIL_ORIGINAL, PUBLISH_STATUS_FAIL_AUDIT, PUBLISH_STATUS_FAIL):
            history.status = "failed"
            # Try to extract error message from fail_idx or other fields
            fail_idx = status_data.get("fail_idx", [])
            if fail_idx:
                history.error_message = f"Publish failed for articles at indices: {fail_idx}"

        history.updated_at = datetime.now(timezone.utc)
        await history.save()

        return PublishStatusResponse(
            status=history.status,
            article_url=history.published_url,
            raw_data=status_data,
        )

    except WeChatMPError as e:
        raise HTTPException(
            status_code=502,
            detail=f"WeChat MP API error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to check publish status: {str(e)}"
        )
