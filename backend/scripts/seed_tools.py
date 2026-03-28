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
        "name": "load_skill",
        "description": "Load a skill's full content into context. Use this when you need to use a specific skill's knowledge. The skill content will be injected into the conversation.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "The skill name to load"},
            },
            "required": ["name"],
        },
        "executor": "python",
        "function_name": "load_skill",
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
    {
        "name": "compress_context",
        "description": "Compress conversation context to free up token space. Use when approaching context limits or before complex operations.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "reason": {"type": "string", "description": "Optional reason for compression", "default": ""},
            },
        },
        "executor": "python",
        "function_name": "compress_context",
        "is_builtin": True,
        "category": "system",
    },
    {
        "name": "spawn_subagent",
        "description": "Spawn an isolated subagent to complete a task independently. Creates a fresh agent context that runs independently and returns only the final result, preventing parent context bloat.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "The task description for the subagent"},
                "agent_role": {"type": "string", "description": "The role of agent to spawn (writer, editor, reviewer, analyzer, etc.)", "default": "general-purpose"},
                "agent_type": {"type": "string", "description": "Type of subagent - 'Explore' (read-only tools only) or 'general-purpose' (full tools)", "default": "general-purpose"},
                "max_iterations": {"type": "integer", "description": "Maximum iterations for the subagent", "default": 5},
                "model_config_name": {"type": "string", "description": "Optional specific LLM model config name to use", "default": ""},
            },
            "required": ["task"],
        },
        "executor": "python",
        "function_name": "spawn_subagent",
        "is_builtin": True,
        "category": "agent",
    },
    {
        "name": "background_run",
        "description": "Run a command in the background using Celery. Creates a Celery task that executes independently and returns a task ID immediately. Use check_background to poll for results.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The command to execute"},
                "timeout": {"type": "integer", "description": "Maximum execution time in seconds", "default": 120},
                "workflow_run_id": {"type": "string", "description": "Optional workflow run ID for tracking"},
            },
            "required": ["command"],
        },
        "executor": "python",
        "function_name": "background_run",
        "is_builtin": True,
        "category": "execution",
    },
    {
        "name": "check_background",
        "description": "Check the status of a background task. Use this to poll for results from background_run.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "The task ID to check. If None, checks all recent tasks."},
            },
        },
        "executor": "python",
        "function_name": "check_background",
        "is_builtin": True,
        "category": "execution",
    },
    {
        "name": "task_create",
        "description": "Create a task in the task graph. Use this to create tasks with optional dependencies for workflow coordination.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "workflow_run_id": {"type": "string", "description": "The workflow run ID"},
                "subject": {"type": "string", "description": "Task title/subject"},
                "description": {"type": "string", "description": "Detailed task description", "default": ""},
                "blocked_by": {"type": "array", "items": {"type": "string"}, "description": "List of task IDs this task depends on", "default": []},
                "priority": {"type": "integer", "description": "Task priority (higher = more important)", "default": 0},
                "task_type": {"type": "string", "description": "Task categorization", "default": "general"},
            },
            "required": ["workflow_run_id", "subject"],
        },
        "executor": "python",
        "function_name": "task_create",
        "is_builtin": True,
        "category": "task_graph",
    },
    {
        "name": "task_claim",
        "description": "Claim a task for execution. Marks a task as in_progress and assigns an owner.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "The task ID to claim"},
                "owner": {"type": "string", "description": "The agent/role claiming the task"},
            },
            "required": ["task_id", "owner"],
        },
        "executor": "python",
        "function_name": "task_claim",
        "is_builtin": True,
        "category": "task_graph",
    },
    {
        "name": "task_complete",
        "description": "Mark a task as completed. This will also unblock any dependent tasks.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "The task ID to complete"},
                "result": {"type": "string", "description": "Optional task result/output"},
            },
            "required": ["task_id"],
        },
        "executor": "python",
        "function_name": "task_complete",
        "is_builtin": True,
        "category": "task_graph",
    },
    {
        "name": "task_list",
        "description": "List all tasks in a workflow with their status and dependencies.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "workflow_run_id": {"type": "string", "description": "The workflow run ID"},
                "status": {"type": "string", "description": "Optional status filter (pending, in_progress, completed, failed)", "default": None},
            },
            "required": ["workflow_run_id"],
        },
        "executor": "python",
        "function_name": "task_list",
        "is_builtin": True,
        "category": "task_graph",
    },
    {
        "name": "task_graph_status",
        "description": "Get overall status of the task graph including counts, ready tasks, and cycle detection.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "workflow_run_id": {"type": "string", "description": "The workflow run ID"},
            },
            "required": ["workflow_run_id"],
        },
        "executor": "python",
        "function_name": "task_graph_status",
        "is_builtin": True,
        "category": "task_graph",
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
