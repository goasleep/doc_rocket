"""Quality rubric routes."""
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser, SuperuserDep
from app.models import (
    Message,
    QualityRubric,
    QualityRubricCreate,
    QualityRubricPublic,
    QualityRubricsPublic,
    QualityRubricUpdate,
)

router = APIRouter(prefix="/rubrics", tags=["rubrics"])


@router.get("/", response_model=QualityRubricsPublic)
async def list_rubrics(
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """List all quality rubrics."""
    import asyncio
    count, rubrics = await asyncio.gather(
        QualityRubric.count(),
        QualityRubric.find_all().sort("-created_at").skip(skip).limit(limit).to_list(),
    )
    return QualityRubricsPublic(data=rubrics, count=count)


@router.get("/active", response_model=QualityRubricPublic)
async def get_active_rubric(current_user: CurrentUser) -> Any:
    """Get the currently active quality rubric."""
    rubric = await QualityRubric.find_one(QualityRubric.is_active == True)  # noqa: E712
    if not rubric:
        raise HTTPException(status_code=404, detail="No active rubric found")
    return rubric


@router.post("/", response_model=QualityRubricPublic, status_code=201)
async def create_rubric(
    current_user: SuperuserDep,
    body: QualityRubricCreate,
) -> Any:
    """Create a new quality rubric (admin only)."""
    from datetime import datetime, timezone

    rubric = QualityRubric(
        version=body.version,
        name=body.name,
        description=body.description,
        dimensions=body.dimensions,
        is_active=body.is_active,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await rubric.insert()
    return rubric


@router.get("/{rubric_id}", response_model=QualityRubricPublic)
async def get_rubric(
    current_user: CurrentUser,
    rubric_id: uuid.UUID,
) -> Any:
    """Get a specific quality rubric."""
    rubric = await QualityRubric.find_one(QualityRubric.id == rubric_id)
    if not rubric:
        raise HTTPException(status_code=404, detail="Rubric not found")
    return rubric


@router.patch("/{rubric_id}", response_model=QualityRubricPublic)
async def update_rubric(
    current_user: SuperuserDep,
    rubric_id: uuid.UUID,
    body: QualityRubricUpdate,
) -> Any:
    """Update a quality rubric (admin only)."""
    from datetime import datetime, timezone

    rubric = await QualityRubric.find_one(QualityRubric.id == rubric_id)
    if not rubric:
        raise HTTPException(status_code=404, detail="Rubric not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rubric, field, value)

    rubric.updated_at = datetime.now(timezone.utc)
    await rubric.save()
    return rubric


@router.post("/{rubric_id}/activate", response_model=QualityRubricPublic)
async def activate_rubric(
    current_user: SuperuserDep,
    rubric_id: uuid.UUID,
) -> Any:
    """Activate a specific rubric (deactivates all others)."""
    from datetime import datetime, timezone

    # Deactivate all rubrics
    await QualityRubric.find(
        QualityRubric.is_active == True  # noqa: E712
    ).update({"$set": {"is_active": False}})

    # Activate the selected rubric
    rubric = await QualityRubric.find_one(QualityRubric.id == rubric_id)
    if not rubric:
        raise HTTPException(status_code=404, detail="Rubric not found")

    rubric.is_active = True
    rubric.updated_at = datetime.now(timezone.utc)
    await rubric.save()

    return rubric


@router.delete("/{rubric_id}", response_model=Message)
async def delete_rubric(
    current_user: SuperuserDep,
    rubric_id: uuid.UUID,
) -> Any:
    """Delete a quality rubric (admin only, cannot delete active rubric)."""
    rubric = await QualityRubric.find_one(QualityRubric.id == rubric_id)
    if not rubric:
        raise HTTPException(status_code=404, detail="Rubric not found")

    if rubric.is_active:
        raise HTTPException(status_code=400, detail="Cannot delete active rubric")

    await rubric.delete()
    return Message(message="Rubric deleted successfully")
