"""Quality rubric routes - code-defined, read-only."""
from typing import Any

from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser
from app.models.quality_rubric import (
    QualityRubricPublic,
    QualityRubricsPublic,
    get_default_rubric,
)

router = APIRouter(prefix="/rubrics", tags=["rubrics"])

# Singleton instance of the code-defined rubric
_DEFAULT_RUBRIC = get_default_rubric()


@router.get("/", response_model=QualityRubricsPublic)
async def list_rubrics(current_user: CurrentUser) -> Any:
    """List all quality rubrics - returns only the code-defined default rubric."""
    return QualityRubricsPublic(data=[QualityRubricPublic.model_validate(_DEFAULT_RUBRIC)], count=1)


@router.get("/active", response_model=QualityRubricPublic)
async def get_active_rubric(current_user: CurrentUser) -> Any:
    """Get the currently active quality rubric - returns the code-defined default."""
    return QualityRubricPublic.model_validate(_DEFAULT_RUBRIC)


@router.get("/{rubric_id}", response_model=QualityRubricPublic)
async def get_rubric(current_user: CurrentUser, rubric_id: str) -> Any:
    """Get a specific quality rubric - only the default rubric is available."""
    # Only accept the fixed ID of the default rubric
    if rubric_id != str(_DEFAULT_RUBRIC.id):
        raise HTTPException(status_code=404, detail="Rubric not found - only default rubric available")
    return QualityRubricPublic.model_validate(_DEFAULT_RUBRIC)


# Create, Update, Activate, Delete endpoints removed
# Rubrics are now code-defined - modify backend/app/models/quality_rubric.py to change
