"""Integration tests for /skills API routes."""
import uuid

import pytest
import respx
from httpx import AsyncClient, Response

from app.models import Skill


@pytest.mark.anyio
async def test_create_skill_returns_201(
    client: AsyncClient,
    superuser_token_headers: dict,
    db: None,
):
    """POST /skills/ creates a new skill and returns 201."""
    r = await client.post(
        "/api/v1/skills/",
        json={
            "name": "test-summarizer",
            "description": "Summarise long texts into bullet points.",
            "body": "## Instructions\nCondense the content into 5 bullets.",
        },
        headers=superuser_token_headers,
    )
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "test-summarizer"
    assert data["description"] == "Summarise long texts into bullet points."
    assert "id" in data

    # Cleanup
    await Skill.find_one(Skill.name == "test-summarizer").delete()  # type: ignore[union-attr]


@pytest.mark.anyio
async def test_create_skill_duplicate_name_returns_409(
    client: AsyncClient,
    superuser_token_headers: dict,
    db: None,
):
    """POST /skills/ with a name that already exists returns 409 Conflict."""
    payload = {
        "name": "duplicate-skill",
        "description": "First instance.",
        "body": "First body.",
    }

    # Create it once — must succeed
    r1 = await client.post(
        "/api/v1/skills/",
        json=payload,
        headers=superuser_token_headers,
    )
    assert r1.status_code == 201

    # Second attempt with the same name must conflict
    r2 = await client.post(
        "/api/v1/skills/",
        json=payload,
        headers=superuser_token_headers,
    )
    assert r2.status_code == 409
    assert "duplicate-skill" in r2.json()["detail"]

    # Cleanup
    skill = await Skill.find_one(Skill.name == "duplicate-skill")
    if skill:
        await skill.delete()


@pytest.mark.anyio
async def test_update_skill_body(
    client: AsyncClient,
    superuser_token_headers: dict,
    db: None,
):
    """PATCH /skills/{id} updates the body field and returns the updated document."""
    # Seed a skill directly in DB
    skill = Skill(
        name="patch-target-skill",
        description="Original description.",
        body="Original body.",
    )
    await skill.insert()

    r = await client.patch(
        f"/api/v1/skills/{skill.id}",
        json={"body": "Updated body content."},
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["body"] == "Updated body content."
    # Other fields must not have changed
    assert data["description"] == "Original description."
    assert data["name"] == "patch-target-skill"

    # Cleanup
    await skill.delete()


@pytest.mark.anyio
async def test_delete_skill_returns_204(
    client: AsyncClient,
    superuser_token_headers: dict,
    db: None,
):
    """DELETE /skills/{id} removes the skill document and returns 204 No Content."""
    skill = Skill(
        name="to-be-deleted-skill",
        description="Will be deleted.",
        body="Body.",
    )
    await skill.insert()

    r = await client.delete(
        f"/api/v1/skills/{skill.id}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 204

    # Verify it is gone from the database
    gone = await Skill.find_one(Skill.id == skill.id)
    assert gone is None


@pytest.mark.anyio
async def test_import_skill_from_markdown_returns_201(
    client: AsyncClient,
    superuser_token_headers: dict,
    db: None,
):
    """POST /skills/import with valid SKILL.md text creates the skill and returns 201."""
    skill_md = """\
---
name: seo-optimizer
description: Optimises article headings for search engines.
---
## SEO Optimizer

Use this skill to rewrite H2/H3 headings so they include the target keyword.
"""
    r = await client.post(
        "/api/v1/skills/import",
        json={"content": skill_md},
        headers=superuser_token_headers,
    )
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "seo-optimizer"
    assert data["description"] == "Optimises article headings for search engines."
    assert "SEO Optimizer" in data["body"]
    assert data["source"] == "imported"

    # Cleanup
    skill = await Skill.find_one(Skill.name == "seo-optimizer")
    if skill:
        await skill.delete()


@pytest.mark.anyio
async def test_import_skill_missing_name_returns_422(
    client: AsyncClient,
    superuser_token_headers: dict,
    db: None,
):
    """POST /skills/import with frontmatter that lacks 'name' returns 422."""
    skill_md_no_name = """\
---
description: Missing the name field entirely.
---
Body without a name in frontmatter.
"""
    r = await client.post(
        "/api/v1/skills/import",
        json={"content": skill_md_no_name},
        headers=superuser_token_headers,
    )
    assert r.status_code == 422
    assert "name" in r.json()["detail"].lower()


@pytest.mark.anyio
async def test_list_skills_returns_paginated_list(
    client: AsyncClient,
    superuser_token_headers: dict,
    db: None,
):
    """GET /skills/ returns 200 with SkillsPublic structure containing data list and count."""
    # Seed 2 skills directly in DB
    skill_a = Skill(
        name="list-skill-alpha",
        description="First skill for list test.",
        body="Body alpha.",
    )
    skill_b = Skill(
        name="list-skill-beta",
        description="Second skill for list test.",
        body="Body beta.",
    )
    await skill_a.insert()
    await skill_b.insert()

    r = await client.get("/api/v1/skills/", headers=superuser_token_headers)
    assert r.status_code == 200
    data = r.json()
    assert "data" in data
    assert "count" in data
    assert isinstance(data["data"], list)
    assert data["count"] >= 2

    # Cleanup
    await skill_a.delete()
    await skill_b.delete()


@pytest.mark.anyio
async def test_get_skill_by_id(
    client: AsyncClient,
    superuser_token_headers: dict,
    db: None,
):
    """GET /skills/{id} returns 200 with the correct skill fields."""
    skill = Skill(
        name="get-by-id-skill",
        description="Skill retrieved by its ID.",
        body="Body content for ID lookup.",
    )
    await skill.insert()

    r = await client.get(
        f"/api/v1/skills/{skill.id}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "get-by-id-skill"
    assert data["description"] == "Skill retrieved by its ID."
    assert data["body"] == "Body content for ID lookup."
    assert data["id"] == str(skill.id)

    # Cleanup
    await skill.delete()


@pytest.mark.anyio
async def test_get_skill_not_found(
    client: AsyncClient,
    superuser_token_headers: dict,
    db: None,
):
    """GET /skills/{id} with a random valid UUID returns 404."""
    random_id = str(uuid.uuid4())
    r = await client.get(
        f"/api/v1/skills/{random_id}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 404


@pytest.mark.anyio
async def test_skills_require_superuser(
    client: AsyncClient,
    normal_user_token_headers: dict,
    db: None,
):
    """Non-superuser receives 403 on both POST /skills/ and GET /skills/."""
    r_post = await client.post(
        "/api/v1/skills/",
        json={
            "name": "unauthorized-skill",
            "description": "Should not be created.",
            "body": "Blocked body.",
        },
        headers=normal_user_token_headers,
    )
    assert r_post.status_code == 403

    r_get = await client.get("/api/v1/skills/", headers=normal_user_token_headers)
    assert r_get.status_code == 403


@pytest.mark.anyio
async def test_import_skill_via_url(
    client: AsyncClient,
    superuser_token_headers: dict,
    db: None,
):
    """POST /skills/import with a URL fetches the SKILL.md content and creates the skill."""
    mock_url = "https://example.com/skills/test-skill.md"
    skill_md_content = """\
---
name: url-imported-skill
description: Imported from a URL.
---
## URL Skill Body"""

    with respx.mock:
        respx.get(mock_url).mock(
            return_value=Response(200, text=skill_md_content)
        )

        r = await client.post(
            "/api/v1/skills/import",
            json={"url": mock_url},
            headers=superuser_token_headers,
        )

    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "url-imported-skill"
    assert data["description"] == "Imported from a URL."

    # Cleanup
    skill = await Skill.find_one(Skill.name == "url-imported-skill")
    if skill:
        await skill.delete()
