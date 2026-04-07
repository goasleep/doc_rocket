"""Tool registry and dispatcher."""
import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Import all built-in tool functions (populated below)
TOOL_REGISTRY: dict[str, Callable[..., Any]] = {}


async def dispatch_tool(name: str, arguments: dict[str, Any], context: dict[str, Any] | None = None) -> str:
    """Dispatch a tool call by name. Returns result string.

    Args:
        name: Tool name to dispatch
        arguments: Tool arguments from LLM
        context: Optional runtime context (messages, workflow_run_id, etc.)

    Unknown tools return an error string (do not raise exceptions).
    """
    fn = TOOL_REGISTRY.get(name)
    if fn is None:
        return f"Tool '{name}' is not available"
    try:
        # Inject context into arguments for tools that need it
        if context:
            if "messages" in context:
                arguments["messages"] = context["messages"]
            if "workflow_run_id" in context:
                arguments["workflow_run_id"] = context["workflow_run_id"]
        result = await fn(**arguments)
        return str(result)
    except Exception as e:
        logger.exception("Tool '%s' dispatch failed", name)
        return f"Tool '{name}' error: {e}"


# Register built-ins after import to avoid circular deps
def _register_builtins() -> None:
    from app.core.tools.builtin import (
        web_search,
        fetch_url,
        activate_skill,
        run_skill_script,
        query_articles,
        save_draft,
        search_similar_articles,
        get_article_analysis,
        save_external_reference,
        compare_with_reference,
        compress_context,
        spawn_subagent,
        load_skill,
        background_run,
        check_background,
    )
    from app.core.tools.task_graph import (
        task_create,
        task_update,
        task_claim,
        task_complete,
        task_fail,
        task_list,
        task_get_ready,
        task_graph_status,
    )
    TOOL_REGISTRY["web_search"] = web_search
    TOOL_REGISTRY["fetch_url"] = fetch_url
    TOOL_REGISTRY["activate_skill"] = activate_skill
    TOOL_REGISTRY["run_skill_script"] = run_skill_script
    TOOL_REGISTRY["query_articles"] = query_articles
    TOOL_REGISTRY["save_draft"] = save_draft
    # Analysis tools for ReactAnalyzerAgent
    TOOL_REGISTRY["search_similar_articles"] = search_similar_articles
    TOOL_REGISTRY["get_article_analysis"] = get_article_analysis
    TOOL_REGISTRY["save_external_reference"] = save_external_reference
    TOOL_REGISTRY["compare_with_reference"] = compare_with_reference
    # Context compression tool
    TOOL_REGISTRY["compress_context"] = compress_context
    # Subagent isolation tool
    TOOL_REGISTRY["spawn_subagent"] = spawn_subagent
    # Skill on-demand loading
    TOOL_REGISTRY["load_skill"] = load_skill
    # Background task tools
    TOOL_REGISTRY["background_run"] = background_run
    TOOL_REGISTRY["check_background"] = check_background
    # Task graph tools
    TOOL_REGISTRY["task_create"] = task_create
    TOOL_REGISTRY["task_update"] = task_update
    TOOL_REGISTRY["task_claim"] = task_claim
    TOOL_REGISTRY["task_complete"] = task_complete
    TOOL_REGISTRY["task_fail"] = task_fail
    TOOL_REGISTRY["task_list"] = task_list
    TOOL_REGISTRY["task_get_ready"] = task_get_ready
    TOOL_REGISTRY["task_graph_status"] = task_graph_status


_register_builtins()
