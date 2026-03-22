"""Idempotent seed script for built-in tools.

Run from container or dev machine:
    uv run python scripts/seed_tools.py
Called automatically by prestart.sh on container startup.
"""
import asyncio
import os

from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie


BUILTIN_TOOLS = [
    {
        "name": "web_search",
        "description": "Search the web for information. Use this to find recent news, facts, or data on any topic.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "max_results": {"type": "integer", "description": "Maximum number of results to return", "default": 5},
            },
            "required": ["query"],
        },
        "executor": "python",
        "function_name": "web_search",
        "is_builtin": True,
        "category": "search",
    },
    {
        "name": "fetch_url",
        "description": "Fetch and extract text content from a URL. Strips HTML tags and truncates long content.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to fetch"},
                "max_chars": {"type": "integer", "description": "Maximum characters to return", "default": 8000},
            },
            "required": ["url"],
        },
        "executor": "python",
        "function_name": "fetch_url",
        "is_builtin": True,
        "category": "web",
    },
    {
        "name": "activate_skill",
        "description": "Load a skill's instructions into context. Use when you need specialized knowledge for a task.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Skill name (kebab-case)"},
            },
            "required": ["name"],
        },
        "executor": "python",
        "function_name": "activate_skill",
        "is_builtin": True,
        "category": "skill",
    },
    {
        "name": "run_skill_script",
        "description": "Execute a script bundled with a skill. Returns stdout, stderr, and exit code.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "skill_name": {"type": "string", "description": "Name of the skill containing the script"},
                "script": {"type": "string", "description": "Filename of the script to run"},
                "args": {"type": "string", "description": "Command-line arguments", "default": ""},
            },
            "required": ["skill_name", "script"],
        },
        "executor": "python",
        "function_name": "run_skill_script",
        "is_builtin": True,
        "category": "skill",
    },
    {
        "name": "query_articles",
        "description": "Search articles in the knowledge base by keywords. Returns matching article IDs, titles, and URLs.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "keywords": {"type": "string", "description": "Search keywords or phrase"},
                "limit": {"type": "integer", "description": "Maximum number of results", "default": 5},
            },
            "required": ["keywords"],
        },
        "executor": "python",
        "function_name": "query_articles",
        "is_builtin": True,
        "category": "knowledge",
    },
    {
        "name": "save_draft",
        "description": "Save the current content as a draft document. Returns the draft ID.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "Draft content in Markdown format"},
                "workflow_run_id": {"type": "string", "description": "Associated workflow run ID"},
            },
            "required": ["content", "workflow_run_id"],
        },
        "executor": "python",
        "function_name": "save_draft",
        "is_builtin": True,
        "category": "output",
    },
]


async def seed() -> None:
    mongodb_url = os.environ.get("MONGODB_URL", "mongodb://localhost:27017")
    mongodb_db = os.environ.get("MONGODB_DB", "app")

    client = AsyncIOMotorClient(mongodb_url)
    db = client[mongodb_db]

    from app.models.tool import Tool
    await init_beanie(database=db, document_models=[Tool])

    created = 0
    updated = 0
    for tool_data in BUILTIN_TOOLS:
        existing = await Tool.find_one(Tool.name == tool_data["name"])
        if existing:
            # Always update description and parameters_schema (upsert, not skip)
            existing.description = tool_data["description"]
            existing.parameters_schema = tool_data["parameters_schema"]
            existing.function_name = tool_data["function_name"]
            existing.category = tool_data["category"]
            await existing.save()
            updated += 1
        else:
            tool = Tool(**tool_data)
            await tool.insert()
            created += 1

    print(f"seed_tools: created={created}, updated={updated}")
    client.close()


if __name__ == "__main__":
    asyncio.run(seed())
