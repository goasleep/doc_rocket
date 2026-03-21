"""Skills CRUD routes + SKILL.md import."""
import io
import re
import zipfile
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


# ClawHub page URL pattern: https://clawhub.ai/<user>/<slug>
_CLAWHUB_PAGE_RE = re.compile(
    r"^https?://clawhub\.ai/[^/]+/(?P<slug>[^/?#]+)",
    re.IGNORECASE,
)
# Download endpoint served by the Convex backend behind clawhub.ai
_CLAWHUB_DOWNLOAD_TPL = (
    "https://wry-manatee-359.convex.site/api/v1/download?slug={slug}"
)


# File extensions that are stored as SkillScript when extracted from a ZIP
_SCRIPT_EXTENSIONS = {".sh", ".bash", ".py", ".js", ".ts", ".rb", ".ps1"}
_SCRIPT_LANGUAGE_MAP = {
    ".sh": "bash", ".bash": "bash",
    ".py": "python",
    ".js": "javascript", ".ts": "typescript",
    ".rb": "ruby",
    ".ps1": "powershell",
}
# Paths inside the ZIP that contain executable assets (scripts & hooks)
_SCRIPT_DIRS = ("scripts/", "hooks/")


def _extract_zip_scripts(zf: zipfile.ZipFile) -> list[SkillScript]:
    """Return SkillScript objects for every script/hook file inside the ZIP."""
    scripts: list[SkillScript] = []
    for name in zf.namelist():
        # Only consider files under scripts/ or hooks/ subdirectories
        if not any(name.startswith(d) for d in _SCRIPT_DIRS):
            continue
        # Skip directories
        if name.endswith("/"):
            continue
        ext = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
        if ext not in _SCRIPT_EXTENSIONS:
            continue
        content = zf.read(name).decode("utf-8", errors="replace")
        language = _SCRIPT_LANGUAGE_MAP.get(ext, "text")
        scripts.append(SkillScript(filename=name, content=content, language=language))
    return scripts


async def _fetch_skill_md_from_url(url: str) -> tuple[str, list[SkillScript]]:
    """Fetch SKILL.md text (and any bundled scripts) from a URL.

    - ClawHub page URL  → download ZIP, extract SKILL.md + scripts/hooks files
    - Any other URL     → GET the URL, expect raw SKILL.md text, no extra scripts
    """
    m = _CLAWHUB_PAGE_RE.match(url)
    if m:
        slug = m.group("slug")
        download_url = _CLAWHUB_DOWNLOAD_TPL.format(slug=slug)
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                resp = await client.get(download_url)
                resp.raise_for_status()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=422, detail=f"Failed to download from ClawHub: {e}")

        try:
            zf = zipfile.ZipFile(io.BytesIO(resp.content))
        except zipfile.BadZipFile:
            raise HTTPException(status_code=422, detail="ClawHub response is not a valid ZIP archive")

        skill_md_names = [n for n in zf.namelist() if n.endswith("SKILL.md")]
        if not skill_md_names:
            raise HTTPException(status_code=422, detail="SKILL.md not found in ClawHub ZIP archive")

        skill_md_text = zf.read(skill_md_names[0]).decode("utf-8")
        extra_scripts = _extract_zip_scripts(zf)
        return skill_md_text, extra_scripts

    # Plain URL — expect raw SKILL.md text, no bundled scripts
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.text, []
    except httpx.HTTPError as e:
        raise HTTPException(status_code=422, detail=f"Failed to fetch URL: {e}")


@router.post("/import", response_model=SkillPublic, status_code=201)
async def import_skill(current_user: SuperuserDep, body: SkillImportBody) -> Any:
    if not body.content and not body.url:
        raise HTTPException(status_code=422, detail="Provide either 'content' or 'url'")

    if body.url:
        text, zip_scripts = await _fetch_skill_md_from_url(body.url)
    else:
        text, zip_scripts = body.content or "", []

    skill_data = _parse_skill_md(text)
    # Merge scripts declared in SKILL.md frontmatter with files extracted from ZIP
    skill_data.scripts = skill_data.scripts + zip_scripts
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
