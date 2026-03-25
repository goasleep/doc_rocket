"""Built-in tool implementations."""
import json
import re
import uuid
from typing import Any

from datetime import datetime, timezone


async def web_search(query: str, max_results: int = 5) -> str:
    """Search the web using Tavily API."""
    from app.models import SystemConfig
    config = await SystemConfig.find_one()
    tavily_key = config.search.tavily_api_key if config and config.search else ""

    if not tavily_key:
        return "web_search not configured: missing TAVILY_API_KEY"

    try:
        from tavily import AsyncTavilyClient
        client = AsyncTavilyClient(api_key=tavily_key)
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
    from app.models import Skill
    from app.core.executors.local import LocalExecutor

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
    from datetime import datetime, timezone
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
        existing.fetched_at = datetime.now(timezone.utc)
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
