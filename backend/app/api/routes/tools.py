"""Tools routes — list all tools and update metadata."""
from typing import Any

from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser, SuperuserDep
from app.models import Tool, ToolPublic, ToolsPublic, ToolUpdate

router = APIRouter(prefix="/tools", tags=["tools"])


def _to_public(tool: Tool) -> ToolPublic:
    return ToolPublic(
        id=tool.id,
        name=tool.name,
        description=tool.description,
        parameters_schema=tool.parameters_schema,
        executor=tool.executor,
        function_name=tool.function_name,
        is_builtin=tool.is_builtin,
        is_active=tool.is_active,
        category=tool.category,
        created_at=tool.created_at,
    )


@router.get("/", response_model=ToolsPublic)
async def list_tools(current_user: CurrentUser) -> Any:
    tools = await Tool.find_all().sort("name").to_list()
    return ToolsPublic(data=[_to_public(t) for t in tools], count=len(tools))


@router.patch("/{tool_id}", response_model=ToolPublic)
async def update_tool(
    current_user: SuperuserDep, tool_id: str, body: ToolUpdate
) -> Any:
    tool = await _get_or_404(tool_id)
    update_data = body.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(tool, field, value)
    await tool.save()
    return _to_public(tool)


async def _get_or_404(tool_id: str) -> Tool:
    import uuid as _uuid
    try:
        uid = _uuid.UUID(tool_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Tool not found")
    tool = await Tool.find_one(Tool.id == uid)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    return tool
