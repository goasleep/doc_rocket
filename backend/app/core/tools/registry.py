"""Tool registry and dispatcher."""
from typing import Any, Callable

# Import all built-in tool functions (populated below)
TOOL_REGISTRY: dict[str, Callable[..., Any]] = {}


async def dispatch_tool(name: str, arguments: dict[str, Any]) -> str:
    """Dispatch a tool call by name. Returns result string.

    Unknown tools return an error string (do not raise exceptions).
    """
    fn = TOOL_REGISTRY.get(name)
    if fn is None:
        return f"Tool '{name}' is not available"
    try:
        result = await fn(**arguments)
        return str(result)
    except Exception as e:
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


_register_builtins()
