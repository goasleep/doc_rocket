"""Built-in tool implementations."""
import json
import re
from typing import Any


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
