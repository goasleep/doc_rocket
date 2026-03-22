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
        """Fetch and extract content from a single URL.

        Strategy:
        1. Try plain HTTP fetch.
        2. Let an LLM agent judge whether the extracted content is valid.
        3. If invalid, fall back to Playwright (headless Chromium).
        4. Return Playwright result regardless of its validity.
        """
        import httpx

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        }

        html_text: str = ""
        http_content: str = ""
        http_title: str = "Untitled"

        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                html_text = response.text
            http_content = self._extract_text(html_text)
            http_title = self._extract_title(html_text)
        except Exception:
            pass

        # Agent validity check
        if http_content and await self._is_content_valid(http_content, url):
            return {"title": http_title, "content": http_content, "url": url}

        # Fall back to Playwright
        pw_result = await self._fetch_url_with_playwright(url)
        return pw_result

    async def _is_content_valid(self, content: str, url: str) -> bool:
        """Ask the LLM whether the extracted text looks like real article content."""
        # Quick heuristic: if content is shorter than 200 chars it's almost certainly invalid
        if len(content.strip()) < 200:
            return False

        try:
            from app.models import LLMModelConfig
            from app.core.llm.factory import get_llm_client_by_config_name

            first = await LLMModelConfig.find_one(LLMModelConfig.is_active == True)  # noqa: E712
            if not first:
                # No LLM configured — fall back to length heuristic only
                return len(content.strip()) >= 500

            llm = await get_llm_client_by_config_name(first.name)
            snippet = content[:1500]
            messages = [
                {
                    "role": "system",
                    "content": (
                        "你是一个内容质量判断助手。"
                        "判断以下文本是否包含真实的文章正文内容（而非导航栏、广告、登录提示、空白骨架页等无效内容）。"
                        "只回复 YES 或 NO，不要解释。"
                    ),
                },
                {
                    "role": "user",
                    "content": f"URL: {url}\n\n文本片段:\n{snippet}",
                },
            ]
            resp = await llm.chat(messages)
            answer = (resp.content or "").strip().upper()
            return answer.startswith("YES")
        except Exception:
            # LLM unavailable — treat long content as valid
            return len(content.strip()) >= 500

    async def _fetch_url_with_playwright(self, url: str) -> dict[str, Any]:
        """Render the page with headless Chromium and extract content."""
        from playwright.async_api import async_playwright

        html_text = ""
        final_url = url
        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(
                    headless=True,
                    executable_path="/usr/bin/chromium",
                    args=["--no-sandbox", "--disable-setuid-sandbox"],
                )
                page = await browser.new_page(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"
                    )
                )
                await page.goto(url, wait_until="networkidle", timeout=30000)
                # Give JS-heavy pages a moment to finish rendering
                await page.wait_for_timeout(2000)
                html_text = await page.content()
                final_url = page.url
                await browser.close()
        except Exception:
            pass

        content = self._extract_text(html_text) if html_text else ""
        title = self._extract_title(html_text) if html_text else "Untitled"
        return {"title": title, "content": content, "url": final_url}

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
