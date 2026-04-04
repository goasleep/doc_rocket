"""Built-in tool implementations."""
import json
import re
import uuid
from datetime import UTC, datetime
from typing import Any


async def web_search(query: str, max_results: int = 5) -> str:
    """Search the web using Tavily API."""
    from app.core.config import settings

    if not settings.TAVILY_API_KEY:
        return "web_search not configured: missing TAVILY_API_KEY"

    try:
        from tavily import AsyncTavilyClient
        client = AsyncTavilyClient(api_key=settings.TAVILY_API_KEY)
        response = await client.search(query, max_results=max_results)
        results = response.get("results", [])
        lines = []
        for r in results:
            lines.append(f"- [{r.get('title', '')}]({r.get('url', '')}): {r.get('content', '')[:200]}")
        return "\n".join(lines) if lines else "No results found"
    except Exception as e:
        return f"web_search error: {e}"


async def fetch_url(url: str, max_chars: int = 8000) -> str:
    """Fetch text content from a URL."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            html = resp.text
    except httpx.HTTPError as e:
        return f"fetch_url error: {e}"

    # Extract body text, strip HTML tags
    body_match = re.search(r"<body[^>]*>(.*?)</body>", html, re.DOTALL | re.IGNORECASE)
    text = body_match.group(1) if body_match else html
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    if len(text) > max_chars:
        return text[:max_chars] + "[内容已截断]"
    return text


async def activate_skill(name: str) -> str:
    """Load a skill's body content into context."""
    from app.models import Skill
    skill = await Skill.find_one(Skill.name == name)
    if not skill:
        return f"Skill '{name}' not found"
    return f'<skill_content name="{name}">{skill.body}</skill_content>'


async def run_skill_script(skill_name: str, script: str, args: str = "") -> str:
    """Execute a script bundled with a skill."""
    from app.core.executors.local import LocalExecutor
    from app.models import Skill

    skill = await Skill.find_one(Skill.name == skill_name)
    if not skill:
        return f"Skill '{skill_name}' not found"

    script_files = {s.filename: s.content for s in skill.scripts}
    if script not in script_files:
        available = ", ".join(script_files.keys()) or "none"
        return f"Script '{script}' not found in skill '{skill_name}'. Available: {available}"

    command = f"python {script}"
    if args:
        command += f" {args}"

    executor = LocalExecutor()
    result = await executor.run(command=command, scripts=script_files)
    return f"exit_code={result.exit_code}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"


async def query_articles(keywords: str, limit: int = 5) -> str:
    """Search articles in the knowledge base by keywords."""
    from app.models import Article
    # Simple text search by matching keywords in title or content
    articles = await Article.find(
        {"$or": [
            {"title": {"$regex": keywords, "$options": "i"}},
            {"content": {"$regex": keywords, "$options": "i"}},
        ]}
    ).limit(limit).to_list()

    results = [
        {"id": str(a.id), "title": a.title, "source_url": getattr(a, "url", "")}
        for a in articles
    ]
    return json.dumps(results, ensure_ascii=False)


async def save_draft(content: str, workflow_run_id: str) -> str:
    """Save content as a draft document."""
    import uuid

    from app.models.draft import Draft

    draft = Draft(
        source_article_ids=[],
        workflow_run_id=uuid.UUID(workflow_run_id) if workflow_run_id else None,
        title="Draft",
        content=content,
        status="draft",
    )
    await draft.insert()
    return f"Draft saved: {draft.id}"


# =============================================================================
# Analysis Tools for ReactAnalyzerAgent
# =============================================================================

async def search_similar_articles(article_content: str, keywords: str | None = None, limit: int = 5) -> str:
    """Search similar articles in the knowledge base.

    Args:
        article_content: The article content to find similar articles for
        keywords: Optional keywords to search (if not provided, will extract from content)
        limit: Maximum number of results

    Returns:
        JSON string with similar articles and their analysis data
    """
    from app.models import Article, ArticleAnalysis

    # If no keywords provided, extract key phrases from content (first 500 chars)
    search_text = keywords or article_content[:500]

    # Simple keyword search by matching in title or content
    articles = await Article.find(
        {"$or": [
            {"title": {"$regex": search_text[:50], "$options": "i"}},
            {"content": {"$regex": search_text[:100], "$options": "i"}},
        ]}
    ).limit(limit * 2).to_list()  # Get more to filter

    results = []
    for article in articles:
        # Get analysis if exists
        analysis = await ArticleAnalysis.find_one(ArticleAnalysis.article_id == article.id)

        # Calculate simple relevance score based on keyword overlap
        content_lower = article_content.lower()
        article_lower = article.content.lower()
        overlap_score = sum(1 for word in search_text.lower().split() if word in article_lower) / max(len(search_text.split()), 1)

        results.append({
            "article_id": str(article.id),
            "title": article.title,
            "url": getattr(article, "url", ""),
            "relevance_score": round(overlap_score * 100, 2),
            "quality_score": analysis.quality_score if analysis else None,
            "quality_breakdown": analysis.quality_breakdown.model_dump() if analysis else None,
        })

    # Sort by relevance and limit
    results.sort(key=lambda x: x["relevance_score"], reverse=True)
    return json.dumps(results[:limit], ensure_ascii=False)


async def get_article_analysis(article_id: str) -> str:
    """Get analysis data for a specific article.

    Args:
        article_id: The article ID (UUID string)

    Returns:
        JSON string with article analysis data
    """
    from app.models import ArticleAnalysis

    try:
        article_uuid = uuid.UUID(article_id)
    except ValueError:
        return json.dumps({"error": "Invalid article_id format"}, ensure_ascii=False)

    analysis = await ArticleAnalysis.find_one(ArticleAnalysis.article_id == article_uuid)

    if not analysis:
        return json.dumps({"error": "Analysis not found"}, ensure_ascii=False)

    result = {
        "article_id": str(analysis.article_id),
        "quality_score": analysis.quality_score,
        "quality_breakdown": analysis.quality_breakdown.model_dump(),
        "hook_type": analysis.hook_type,
        "framework": analysis.framework,
        "emotional_triggers": analysis.emotional_triggers,
        "key_phrases": analysis.key_phrases,
        "keywords": analysis.keywords,
        "structure": analysis.structure.model_dump(),
        "style": analysis.style.model_dump(),
        "target_audience": analysis.target_audience,
    }
    return json.dumps(result, ensure_ascii=False)


async def save_external_reference(
    url: str,
    title: str,
    content: str,
    content_snippet: str,
    source: str = "web_search",
    search_query: str = "",
    metadata: dict | None = None,
    referencer_article_id: str | None = None,
) -> str:
    """Save an external reference article with deduplication.

    Args:
        url: The article URL (unique identifier)
        title: Article title
        content: Full article content (max 10000 chars)
        content_snippet: Content summary/snippet
        source: Source type (web_search | manual)
        search_query: The search query that found this article
        metadata: Additional metadata from search
        referencer_article_id: ID of the article referencing this external reference

    Returns:
        JSON string with the saved/updated external reference ID
    """
    from app.models import ExternalReference

    # Truncate content if too long
    max_content_len = 10000
    if len(content) > max_content_len:
        content = content[:max_content_len] + "...[truncated]"

    # Check for existing reference by URL
    existing = await ExternalReference.find_one(ExternalReference.url == url)

    if existing:
        # Update existing reference
        existing.title = title
        existing.content = content
        existing.content_snippet = content_snippet
        existing.fetched_at = datetime.now(UTC)
        existing.metadata = metadata or {}

        # Add referencer if not already in list
        if referencer_article_id:
            try:
                ref_uuid = uuid.UUID(referencer_article_id)
                if ref_uuid not in existing.referencer_article_ids:
                    existing.referencer_article_ids.append(ref_uuid)
            except ValueError:
                pass

        await existing.save()
        return json.dumps({
            "id": str(existing.id),
            "action": "updated",
            "url": url,
        }, ensure_ascii=False)
    else:
        # Create new reference
        referencer_ids = []
        if referencer_article_id:
            try:
                referencer_ids = [uuid.UUID(referencer_article_id)]
            except ValueError:
                pass

        ref = ExternalReference(
            url=url,
            title=title,
            source=source,
            content=content,
            content_snippet=content_snippet,
            search_query=search_query,
            metadata=metadata or {},
            referencer_article_ids=referencer_ids,
        )
        await ref.insert()
        return json.dumps({
            "id": str(ref.id),
            "action": "created",
            "url": url,
        }, ensure_ascii=False)


async def compare_with_reference(
    article_content: str,
    reference_content: str,
    reference_title: str = "",
    reference_source: str = "external",
) -> str:
    """Compare article with a reference and generate comparison analysis.

    Args:
        article_content: The main article content
        reference_content: The reference article content
        reference_title: Title of the reference article
        reference_source: Source type (knowledge_base | external)

    Returns:
        JSON string with comparison results
    """
    # Simple comparison logic (can be enhanced with LLM)
    article_words = set(article_content.lower().split())
    ref_words = set(reference_content.lower().split())

    # Calculate similarity
    common_words = article_words & ref_words
    all_words = article_words | ref_words
    similarity_score = len(common_words) / max(len(all_words), 1) * 100

    # Extract key differences (words unique to each)
    article_unique = list(article_words - ref_words)[:20]
    ref_unique = list(ref_words - article_words)[:20]

    result = {
        "similarity_score": round(similarity_score, 2),
        "reference_title": reference_title,
        "reference_source": reference_source,
        "key_differences": {
            "article_unique_terms": article_unique,
            "reference_unique_terms": ref_unique,
        },
        "common_topics": list(common_words)[:10],
        "comparison_notes": f"Similarity score: {round(similarity_score, 2)}%",
    }

    return json.dumps(result, ensure_ascii=False)


# =============================================================================
# Context Compression Tools
# =============================================================================

async def compress_context(
    reason: str = "",
    messages: list[dict[str, Any]] | None = None,
    workflow_run_id: str | None = None,
) -> str:
    """Manually trigger context compression to reduce token usage.

    This tool compresses the conversation history by generating a summary
    and saving the full transcript to persistent storage.

    Args:
        reason: Optional reason for compression (e.g., "preparing for complex analysis")
        messages: Current message context (auto-injected by dispatcher)
        workflow_run_id: Current workflow run ID (auto-injected by dispatcher)

    Returns:
        Confirmation message with compression statistics
    """
    from app.core.agents.compression import ContextCompressor
    from app.core.llm.factory import get_llm_client_by_config_name
    from app.models import LLMModelConfig

    if messages is None:
        return "Error: No messages context available"

    compressor = ContextCompressor()

    # Get LLM client for summarization
    first = await LLMModelConfig.find_one(LLMModelConfig.is_active == True)  # noqa: E712
    if not first:
        return "Error: No LLM model config found"

    llm = await get_llm_client_by_config_name(first.name)

    # Perform full compression
    original_count = len(messages)
    original_tokens = compressor.estimate_tokens(messages)

    compressed, transcript_id = await compressor.compact(messages, llm, workflow_run_id)

    new_tokens = compressor.estimate_tokens(compressed)

    # Update the messages list in place
    messages.clear()
    messages.extend(compressed)

    return (
        f"Context compressed successfully.\n"
        f"Reason: {reason or 'manual trigger'}\n"
        f"Transcript ID: {transcript_id}\n"
        f"Original: {original_count} messages (~{original_tokens} tokens)\n"
        f"Compressed: {len(compressed)} messages (~{new_tokens} tokens)\n"
        f"Reduction: ~{original_tokens - new_tokens} tokens ({int((1 - new_tokens/max(original_tokens, 1)) * 100)}%)"
    )


# =============================================================================
# Subagent Isolation Tools
# =============================================================================

async def spawn_subagent(
    task: str,
    agent_role: str = "general-purpose",
    agent_type: str = "general-purpose",
    max_iterations: int = 5,
    model_config_name: str = "",
) -> str:
    """Spawn an isolated subagent to complete a task independently.

    This tool creates a fresh agent context that runs independently
    and returns only the final result, preventing parent context bloat.

    Args:
        task: The task description for the subagent
        agent_role: The role of agent to spawn (writer, editor, reviewer, analyzer, etc.)
        agent_type: Type of subagent - "Explore" (read-only tools only) or "general-purpose" (full tools)
        max_iterations: Maximum iterations for the subagent (default: 5)
        model_config_name: Optional specific LLM model config name to use

    Returns:
        Final output from the subagent

    Example:
        spawn_subagent(
            task="Research the latest AI trends and summarize key findings",
            agent_role="analyzer",
            agent_type="Explore"
        )
    """
    from app.core.agents.subagent import SubagentRunner

    runner = SubagentRunner()

    # Build the prompt with context about isolation
    full_prompt = f"""You are an isolated subagent. Complete the following task and provide your final answer.

Task: {task}

Important: You are running in an isolated context. Your final response will be returned directly to the parent agent.
Be thorough but concise in your response.
"""

    result = await runner.run(
        agent_role=agent_role,
        prompt=full_prompt,
        max_iterations=max_iterations,
        agent_type=agent_type,
        model_config_name=model_config_name or None,
    )

    return f"[Subagent ({agent_role}/{agent_type}) result]:\n{result}"


# =============================================================================
# Skill On-Demand Loading
# =============================================================================

async def load_skill(name: str) -> str:
    """Load a skill's full content into context.

    Call this when you need to use a specific skill's knowledge.
    The skill content will be injected into the conversation.

    Args:
        name: The skill name to load

    Returns:
        Formatted skill content or error message
    """
    from app.core.agents.skill_cache import get_skill_cache
    from app.models import Skill

    cache = get_skill_cache()

    # Check cache first
    cached = cache.get(name)
    if cached:
        return f"""<skill name="{cached.name}">
{cached.body}
</skill>

Skill '{cached.name}' loaded (from cache). Follow its instructions when applicable."""

    # Fetch from database
    skill = await Skill.find_one(Skill.name == name)
    if not skill:
        available = await Skill.find(Skill.is_active == True).to_list()  # noqa: E712
        return (
            f"Skill '{name}' not found. "
            f"Available: {', '.join(s.name for s in available[:10])}"
        )

    # Cache the skill content
    cache.set(
        name=skill.name,
        body=skill.body,
        description=skill.description,
    )

    return f"""<skill name="{skill.name}">
{skill.body}
</skill>

Skill '{skill.name}' loaded. Follow its instructions when applicable."""


# =============================================================================
# Background Task Tools (Celery-based)
# =============================================================================

async def background_run(
    command: str,
    timeout: int = 120,
    workflow_run_id: str | None = None,
) -> str:
    """Run a command in the background using Celery.

    This creates a Celery task that executes independently and returns
    a task ID immediately. Use check_background to poll for results.

    Args:
        command: The command to execute
        timeout: Maximum execution time in seconds (default: 120)
        workflow_run_id: Optional workflow run ID for tracking

    Returns:
        Task ID for status checking
    """

    from app.tasks.background import execute_background_command

    # Submit the task to Celery
    task = execute_background_command.delay(
        command=command,
        timeout=timeout,
        workflow_run_id=workflow_run_id,
    )

    return (
        f"Background task started.\n"
        f"Task ID: {task.id}\n"
        f"Command: {command}\n"
        f"Use check_background(task_id='{task.id}') to check status."
    )


async def check_background(task_id: str | None = None) -> str:
    """Check the status of a background task.

    Args:
        task_id: The task ID to check. If None, checks all recent tasks.

    Returns:
        Task status and result if complete
    """
    from celery.result import AsyncResult

    from app.core.celery import celery_app

    if task_id:
        result = AsyncResult(task_id, app=celery_app)

        status = result.status
        if status == "PENDING":
            return f"Task {task_id}: Pending (not yet started)"
        elif status == "STARTED":
            return f"Task {task_id}: Running..."
        elif status == "SUCCESS":
            task_result = result.get()
            return (
                f"Task {task_id}: Completed successfully\n"
                f"Result: {task_result}"
            )
        elif status == "FAILURE":
            error = result.get(propagate=False)
            return f"Task {task_id}: Failed\nError: {error}"
        else:
            return f"Task {task_id}: Status = {status}"

    # No task_id provided - list recent tasks from Celery backend
    # Note: This requires the Celery result backend to be configured
    return "Please provide a task_id to check status."
