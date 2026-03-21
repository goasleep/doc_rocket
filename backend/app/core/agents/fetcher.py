"""FetcherAgent — fetches articles from API sources, RSS feeds, or URLs."""
import re
from datetime import datetime
from typing import Any


class FetcherAgent:
    """Fetches raw article data from various source types."""

    async def fetch_source(self, source: Any) -> list[dict[str, Any]]:
        """Fetch articles from a Source document."""
        if source.type == "rss":
            return await self._fetch_rss(source)
        else:
            return await self._fetch_api(source)

    async def fetch_url(self, url: str) -> dict[str, Any]:
        """Fetch and extract content from a single URL."""
        import httpx

        headers = {"User-Agent": "Mozilla/5.0 (compatible; ContentBot/1.0)"}
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            content = self._extract_text(response.text)

        return {
            "title": self._extract_title(response.text),
            "content": content,
            "url": url,
        }

    async def _fetch_api(self, source: Any) -> list[dict[str, Any]]:
        import httpx

        headers: dict[str, str] = source.headers or {}
        if source.api_key:
            headers["Authorization"] = f"Bearer {source.api_key}"

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(source.url, headers=headers)
            response.raise_for_status()
            data = response.json()

        cfg = source.api_config
        if not cfg:
            return []

        items = self._get_nested(data, cfg.items_path)
        if not isinstance(items, list):
            return []

        max_items = source.fetch_config.max_items_per_fetch
        results = []
        for item in items[:max_items]:
            results.append({
                "title": item.get(cfg.title_field, ""),
                "content": item.get(cfg.content_field, ""),
                "url": item.get(cfg.url_field),
                "author": item.get(cfg.author_field) if cfg.author_field else None,
                "published_at": self._parse_dt(item.get(cfg.published_at_field)) if cfg.published_at_field else None,
            })
        return results

    async def _fetch_rss(self, source: Any) -> list[dict[str, Any]]:
        import httpx
        import feedparser

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(source.url)
            response.raise_for_status()
            feed_text = response.text

        feed = feedparser.parse(feed_text)
        max_items = source.fetch_config.max_items_per_fetch
        results = []
        for entry in feed.entries[:max_items]:
            content = ""
            if hasattr(entry, "content") and entry.content:
                content = entry.content[0].value
            elif hasattr(entry, "summary"):
                content = entry.summary

            published_at = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                import time
                published_at = datetime(*entry.published_parsed[:6])

            results.append({
                "title": getattr(entry, "title", ""),
                "content": content,
                "url": getattr(entry, "link", None),
                "author": getattr(entry, "author", None),
                "published_at": published_at,
            })
        return results

    def _get_nested(self, data: Any, path: str) -> Any:
        """Traverse nested dict/list using dot-separated path e.g. 'data.items'."""
        parts = path.split(".")
        current = data
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list) and part.isdigit():
                current = current[int(part)]
            else:
                return None
        return current

    def _extract_title(self, html: str) -> str:
        match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return "Untitled"

    def _extract_text(self, html: str) -> str:
        """Simple HTML → plain text extraction."""
        # Remove script/style blocks
        text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
        # Remove HTML tags
        text = re.sub(r"<[^>]+>", " ", text)
        # Collapse whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text[:50000]  # cap at 50k chars

    def _parse_dt(self, value: Any) -> datetime | None:
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        try:
            from datetime import timezone
            # Try ISO format
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None
