"""FetcherAgent — fetches articles from API sources, RSS feeds, or URLs."""
import asyncio
import re
from datetime import datetime
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx


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
        4. Extract images from HTML, download and upload to Qiniu OSS.
        5. Return content with Qiniu image URLs.
        """
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
        http_raw_html: str = ""
        images: list[dict[str, Any]] = []

        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                html_text = response.text
            http_content = self._extract_text(html_text)
            http_title = self._extract_title(html_text)
            http_raw_html = self._extract_main_html(html_text, url)
            images = await self._extract_and_upload_images(http_raw_html, url)
        except Exception:
            pass

        # Agent validity check
        if http_content and await self._is_content_valid(http_content[:1500], url):
            return {
                "title": http_title,
                "content": http_content,
                "url": url,
                "images": images,
                "raw_html": http_raw_html,
            }

        # Fall back to Playwright
        pw_result = await self._fetch_url_with_playwright(url)
        return pw_result

    async def _extract_and_upload_images(
        self, html: str, base_url: str
    ) -> list[dict[str, Any]]:
        """Extract images from HTML, download and upload to Qiniu OSS.

        Returns list of dicts with:
        - original_url: original image URL
        - qiniu_url: uploaded Qiniu URL (or original if upload failed)
        - alt: image alt text
        """
        from app.core.qiniu_oss import QiniuOSSClient, QiniuOSError

        # Extract all img tags
        img_pattern = r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>'
        img_tags = re.findall(img_pattern, html, re.IGNORECASE)

        # Also extract srcset if present
        srcset_pattern = r'<img[^>]+srcset=["\']([^"\']+)["\'][^>]*>'
        srcset_matches = re.findall(srcset_pattern, html, re.IGNORECASE)

        # Parse srcset to get largest image
        for srcset in srcset_matches:
            # srcset format: "url1 1x, url2 2x" or "url1 100w, url2 200w"
            urls = re.findall(r'([^\s,]+)\s+(?:\d+w|\d+x)', srcset)
            if urls:
                # Take the last one (usually largest)
                img_tags.append(urls[-1])

        # Deduplicate and filter
        seen_urls = set()
        unique_images = []

        for img_url in img_tags:
            # Skip data URIs
            if img_url.startswith("data:"):
                continue

            # Resolve relative URLs
            absolute_url = urljoin(base_url, img_url)

            # Skip if already processed
            if absolute_url in seen_urls:
                continue
            seen_urls.add(absolute_url)

            # Skip common non-content images (icons, logos, ads)
            skip_patterns = [
                r"favicon",
                r"logo",
                r"icon",
                r"avatar",
                r"banner",
                r"ad\.",
                r"tracking",
                r"pixel",
                r"spacer",
                r"blank",
                r"\.svg$",
                r"1x1",
                r"beacon",
            ]
            if any(re.search(p, absolute_url, re.I) for p in skip_patterns):
                continue

            unique_images.append(absolute_url)

        # Limit to first 10 images to avoid too many uploads
        unique_images = unique_images[:10]

        # Try to initialize Qiniu client
        try:
            qiniu_client = QiniuOSSClient.from_settings()
        except QiniuOSError:
            # Qiniu not configured, return original URLs
            return [
                {"original_url": url, "qiniu_url": url, "alt": ""}
                for url in unique_images
            ]

        async def _download_and_upload(client: httpx.AsyncClient, img_url: str) -> dict[str, Any]:
            try:
                response = await client.get(img_url, headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"
                    ),
                    "Referer": base_url,
                })
                response.raise_for_status()
                image_data = response.content

                # Skip if too small (likely icon) or too large
                if len(image_data) < 1024 or len(image_data) > 10 * 1024 * 1024:
                    return {
                        "original_url": img_url,
                        "qiniu_url": img_url,
                        "alt": "",
                    }

                content_type = response.headers.get("content-type", "")
                ext = self._get_image_extension(img_url, content_type)
                filename = qiniu_client.generate_key(image_data, "articles", ext)

                qiniu_url = await qiniu_client.upload_file(image_data, filename)

                return {
                    "original_url": img_url,
                    "qiniu_url": qiniu_url,
                    "alt": "",
                }

            except Exception:
                return {
                    "original_url": img_url,
                    "qiniu_url": img_url,
                    "alt": "",
                }

        # Download and upload images concurrently
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            tasks = [_download_and_upload(client, img_url) for img_url in unique_images]
            results = await asyncio.gather(*tasks)

        return results

    def _get_image_extension(self, url: str, content_type: str) -> str:
        """Get file extension from URL or content-type."""
        # Map content-type to extension
        mime_map = {
            "image/jpeg": ".jpg",
            "image/jpg": ".jpg",
            "image/png": ".png",
            "image/gif": ".gif",
            "image/webp": ".webp",
        }

        if content_type:
            for mime, ext in mime_map.items():
                if mime in content_type:
                    return ext

        # Try to get from URL
        parsed = urlparse(url)
        path = parsed.path.lower()
        for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
            if path.endswith(ext):
                return ".jpg" if ext == ".jpeg" else ext

        # Default to .jpg
        return ".jpg"

    async def _is_content_valid(self, content: str, url: str) -> bool:
        """Ask the LLM whether the extracted text looks like real article content."""
        # Quick heuristic: if content is shorter than 200 chars
        # it's almost certainly invalid
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
                try:
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
                finally:
                    await browser.close()
        except Exception:
            pass

        content = self._extract_text(html_text) if html_text else ""
        title = self._extract_title(html_text) if html_text else "Untitled"
        raw_html = self._extract_main_html(html_text, final_url) if html_text else ""

        # Extract and upload images
        images = []
        if raw_html:
            images = await self._extract_and_upload_images(raw_html, final_url)

        return {
            "title": title,
            "content": content,
            "url": final_url,
            "images": images,
            "raw_html": raw_html,
        }

    async def _fetch_api(self, source: Any) -> list[dict[str, Any]]:
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
                "published_at": (
                    self._parse_dt(item.get(cfg.published_at_field))
                    if cfg.published_at_field
                    else None
                ),
            })
        return results

    async def _fetch_rss(self, source: Any) -> list[dict[str, Any]]:
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
        text = re.sub(
            r"<(script|style)[^>]*>.*?</\1>",
            "",
            html,
            flags=re.DOTALL | re.IGNORECASE,
        )
        # Remove HTML tags
        text = re.sub(r"<[^>]+>", " ", text)
        # Collapse whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text[:50000]  # cap at 50k chars

    def _extract_main_html(self, html: str, base_url: str) -> str:
        """Extract main content HTML using readability-lxml.

        Returns cleaned HTML with only the article content, removing
        navigation bars, sidebars, ads, etc.
        """
        try:
            from readability import Document

            doc = Document(html)
            # Get the main content HTML
            content_html = doc.summary()

            # Resolve relative URLs in the HTML
            content_html = self._resolve_relative_urls(content_html, base_url)

            # Wrap with basic styling for better display
            styled_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{doc.title()}</title>
<style>
body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    line-height: 1.8;
    max-width: 800px;
    margin: 0 auto;
    padding: 20px;
    color: #333;
}}
h1, h2, h3, h4, h5, h6 {{
    margin-top: 1.5em;
    margin-bottom: 0.5em;
    line-height: 1.3;
}}
p {{
    margin: 1em 0;
}}
img {{
    max-width: 100%;
    height: auto;
    display: block;
    margin: 1em auto;
}}
pre, code {{
    background: #f5f5f5;
    padding: 0.2em 0.4em;
    border-radius: 3px;
    font-family: Consolas, Monaco, "Courier New", monospace;
}}
pre {{
    padding: 1em;
    overflow-x: auto;
}}
blockquote {{
    border-left: 4px solid #ddd;
    margin: 1em 0;
    padding-left: 1em;
    color: #666;
}}
table {{
    width: 100%;
    border-collapse: collapse;
    margin: 1em 0;
}}
th, td {{
    border: 1px solid #ddd;
    padding: 8px;
    text-align: left;
}}
th {{
    background: #f5f5f5;
}}
a {{
    color: #0066cc;
    text-decoration: none;
}}
a:hover {{
    text-decoration: underline;
}}
</style>
</head>
<body>
{content_html}
</body>
</html>"""
            return styled_html
        except Exception:
            # Fallback: return original HTML with basic cleanup
            return self._basic_html_cleanup(html, base_url)

    def _resolve_relative_urls(self, html: str, base_url: str) -> str:
        """Resolve relative URLs in HTML to absolute URLs."""
        from urllib.parse import urljoin

        # Resolve src attributes
        def resolve_src(match: re.Match) -> str:
            attr = match.group(1)
            url = match.group(2)
            if url.startswith(("http://", "https://", "data:")):
                return match.group(0)
            absolute = urljoin(base_url, url)
            return f'{attr}="{absolute}"'

        html = re.sub(r'(src=["\'])([^"\']+)(["\'])', resolve_src, html)
        html = re.sub(r'(href=["\'])([^"\']+)(["\'])', resolve_src, html)
        return html

    def _basic_html_cleanup(self, html: str, base_url: str) -> str:
        """Basic HTML cleanup when readability fails."""
        # Remove script/style blocks
        html = re.sub(
            r"<(script|style|nav|header|footer|aside)[^>]*>.*?</\1>",
            "",
            html,
            flags=re.DOTALL | re.IGNORECASE,
        )
        # Resolve relative URLs
        html = self._resolve_relative_urls(html, base_url)
        return html

    def _parse_dt(self, value: Any) -> datetime | None:
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        try:
            # Try ISO format
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None
