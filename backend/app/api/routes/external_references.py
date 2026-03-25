"""External reference routes."""
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser, SuperuserDep
from app.models import (
    ExternalReference,
    ExternalReferenceCreate,
    ExternalReferenceDetail,
    ExternalReferencePublic,
    ExternalReferencesPublic,
    ExternalReferenceUpdate,
    Message,
)

router = APIRouter(prefix="/external-references", tags=["external-references"])


@router.get("/", response_model=ExternalReferencesPublic)
async def list_external_references(
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
    search: str = "",
    source: str = "",
) -> Any:
    """List external references with optional filtering."""
    import asyncio

    query = {}
    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"url": {"$regex": search, "$options": "i"}},
        ]
    if source:
        query["source"] = source

    if query:
        count = await ExternalReference.find(query).count()
        refs = await ExternalReference.find(query).sort("-created_at").skip(skip).limit(limit).to_list()
    else:
        count, refs = await asyncio.gather(
            ExternalReference.count(),
            ExternalReference.find_all().sort("-created_at").skip(skip).limit(limit).to_list(),
        )

    return ExternalReferencesPublic(data=refs, count=count)


@router.get("/{ref_id}", response_model=ExternalReferenceDetail)
async def get_external_reference(
    current_user: CurrentUser,
    ref_id: uuid.UUID,
) -> Any:
    """Get a specific external reference with full content."""
    ref = await ExternalReference.find_one(ExternalReference.id == ref_id)
    if not ref:
        raise HTTPException(status_code=404, detail="External reference not found")
    return ref


@router.post("/", response_model=ExternalReferencePublic, status_code=201)
async def create_external_reference(
    current_user: CurrentUser,
    body: ExternalReferenceCreate,
) -> Any:
    """Manually add an external reference."""
    from datetime import datetime, timezone

    # Check for duplicate URL
    existing = await ExternalReference.find_one(ExternalReference.url == body.url)
    if existing:
        raise HTTPException(status_code=400, detail="External reference with this URL already exists")

    ref = ExternalReference(
        url=body.url,
        title=body.title,
        source=body.source,
        content=body.content,
        content_snippet=body.content_snippet,
        search_query=body.search_query,
        metadata=body.metadata,
        referencer_article_ids=[],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await ref.insert()
    return ref


@router.patch("/{ref_id}", response_model=ExternalReferencePublic)
async def update_external_reference(
    current_user: SuperuserDep,
    ref_id: uuid.UUID,
    body: ExternalReferenceUpdate,
) -> Any:
    """Update an external reference (admin only)."""
    from datetime import datetime, timezone

    ref = await ExternalReference.find_one(ExternalReference.id == ref_id)
    if not ref:
        raise HTTPException(status_code=404, detail="External reference not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(ref, field, value)

    ref.updated_at = datetime.now(timezone.utc)
    await ref.save()
    return ref


@router.delete("/{ref_id}", response_model=Message)
async def delete_external_reference(
    current_user: SuperuserDep,
    ref_id: uuid.UUID,
) -> Any:
    """Delete an external reference (admin only, cannot delete if referenced)."""
    ref = await ExternalReference.find_one(ExternalReference.id == ref_id)
    if not ref:
        raise HTTPException(status_code=404, detail="External reference not found")

    if ref.referencer_article_ids:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete: referenced by {len(ref.referencer_article_ids)} articles"
        )

    await ref.delete()
    return Message(message="External reference deleted successfully")


@router.post("/{ref_id}/refetch", response_model=ExternalReferencePublic)
async def refetch_external_reference(
    current_user: CurrentUser,
    ref_id: uuid.UUID,
) -> Any:
    """Re-fetch content for an external reference."""
    from datetime import datetime, timezone

    from app.core.tools.registry import dispatch_tool

    ref = await ExternalReference.find_one(ExternalReference.id == ref_id)
    if not ref:
        raise HTTPException(status_code=404, detail="External reference not found")

    # Fetch new content
    result = await dispatch_tool("fetch_url", {"url": ref.url, "max_chars": 10000})

    if result.startswith("fetch_url error:"):
        raise HTTPException(status_code=400, detail=f"Failed to fetch: {result}")

    ref.content = result[:10000]
    ref.content_snippet = result[:500]
    ref.fetched_at = datetime.now(timezone.utc)
    await ref.save()

    return ref
