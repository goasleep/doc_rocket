"""Skills CRUD routes + SKILL.md import."""
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException

from app.api.deps import SuperuserDep
from app.models import (
    Skill,
    SkillCreate,
    SkillPublic,
    SkillScript,
    SkillsPublic,
    SkillUpdate,
)

router = APIRouter(prefix="/skills", tags=["skills"])


def _to_public(skill: Skill) -> SkillPublic:
    return SkillPublic(
        id=skill.id,
        name=skill.name,
        description=skill.description,
        body=skill.body,
        scripts=skill.scripts,
        needs_network=skill.needs_network,
        is_active=skill.is_active,
        source=skill.source,
        imported_from=skill.imported_from,
        created_at=skill.created_at,
        updated_at=skill.updated_at,
    )


@router.get("/", response_model=SkillsPublic)
async def list_skills(
    current_user: SuperuserDep,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    skills = await Skill.find_all().sort("name").skip(skip).limit(limit).to_list()
    count = await Skill.count()
    return SkillsPublic(data=[_to_public(s) for s in skills], count=count)


@router.post("/", response_model=SkillPublic, status_code=201)
async def create_skill(current_user: SuperuserDep, body: SkillCreate) -> Any:
    existing = await Skill.find_one(Skill.name == body.name)
    if existing:
        raise HTTPException(status_code=409, detail=f"Skill '{body.name}' already exists")
    skill = Skill(**body.model_dump())
    await skill.insert()
    return _to_public(skill)


@router.get("/{skill_id}", response_model=SkillPublic)
async def get_skill(current_user: SuperuserDep, skill_id: str) -> Any:
    skill = await _get_or_404(skill_id)
    return _to_public(skill)


@router.patch("/{skill_id}", response_model=SkillPublic)
async def update_skill(
    current_user: SuperuserDep, skill_id: str, body: SkillUpdate
) -> Any:
    from datetime import datetime, timezone
    skill = await _get_or_404(skill_id)
    update_data = body.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(skill, field, value)
    skill.updated_at = datetime.now(timezone.utc)
    await skill.save()
    return _to_public(skill)


@router.delete("/{skill_id}", status_code=204)
async def delete_skill(current_user: SuperuserDep, skill_id: str) -> None:
    skill = await _get_or_404(skill_id)
    await skill.delete()


# ── SKILL.md import ────────────────────────────────────────────────────────────

class SkillImportRequest(SuperuserDep.__class__ if False else object):  # noqa: just a placeholder
    pass


from pydantic import BaseModel as _BaseModel  # noqa: E402


class SkillImportBody(_BaseModel):
    content: str | None = None  # raw SKILL.md text
    url: str | None = None      # URL to fetch SKILL.md from


def _parse_skill_md(text: str) -> SkillCreate:
    """Parse a SKILL.md document into SkillCreate.

    Expected format:
    ---
    name: my-skill
    description: What this skill does
    ---
    Body content here...
    """
    import yaml

    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            frontmatter_text = parts[1].strip()
            body_text = parts[2].strip()
        else:
            frontmatter_text = ""
            body_text = text
    else:
        frontmatter_text = ""
        body_text = text

    if frontmatter_text:
        try:
            meta = yaml.safe_load(frontmatter_text) or {}
        except yaml.YAMLError as e:
            raise HTTPException(status_code=422, detail=f"Invalid YAML frontmatter: {e}")
    else:
        meta = {}

    name = meta.get("name")
    if not name:
        raise HTTPException(status_code=422, detail="SKILL.md frontmatter must include 'name' field")

    description = meta.get("description", "")

    # Parse optional scripts from frontmatter
    scripts: list[SkillScript] = []
    for s in meta.get("scripts", []):
        if isinstance(s, dict):
            scripts.append(SkillScript(
                filename=s.get("filename", "script.py"),
                content=s.get("content", ""),
                language=s.get("language", "python"),
            ))

    return SkillCreate(
        name=name,
        description=description,
        body=body_text,
        scripts=scripts,
        source="imported",
    )


@router.post("/import", response_model=SkillPublic, status_code=201)
async def import_skill(current_user: SuperuserDep, body: SkillImportBody) -> Any:
    if not body.content and not body.url:
        raise HTTPException(status_code=422, detail="Provide either 'content' or 'url'")

    if body.url:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(body.url)
                resp.raise_for_status()
                text = resp.text
        except httpx.HTTPError as e:
            raise HTTPException(status_code=422, detail=f"Failed to fetch URL: {e}")
    else:
        text = body.content or ""

    skill_data = _parse_skill_md(text)
    if body.url:
        skill_data.imported_from = body.url

    existing = await Skill.find_one(Skill.name == skill_data.name)
    if existing:
        raise HTTPException(status_code=409, detail=f"Skill '{skill_data.name}' already exists")

    skill = Skill(**skill_data.model_dump())
    await skill.insert()
    return _to_public(skill)


async def _get_or_404(skill_id: str) -> Skill:
    import uuid as _uuid
    try:
        uid = _uuid.UUID(skill_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Skill not found")
    skill = await Skill.find_one(Skill.id == uid)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill
