"""Unit tests for FetcherAgent using respx to mock HTTP."""
import json

import pytest
import respx
from httpx import Response

from app.core.agents.fetcher import FetcherAgent
from app.models.source import ApiConfig, FetchConfig


def _make_api_source(url: str = "https://api.example.com/articles"):
    """Build a minimal mock Source object for API type."""
    from unittest.mock import MagicMock
    source = MagicMock()
    source.type = "api"
    source.url = url
    source.api_key = None
    source.headers = {}
    source.api_config = ApiConfig(
        items_path="data",
        title_field="title",
        content_field="body",
        url_field="link",
        author_field="author",
    )
    source.fetch_config = FetchConfig(interval_minutes=60, max_items_per_fetch=5)
    return source


def _make_rss_source(url: str = "https://rss.example.com/feed.xml"):
    from unittest.mock import MagicMock
    source = MagicMock()
    source.type = "rss"
    source.url = url
    source.fetch_config = FetchConfig(interval_minutes=60, max_items_per_fetch=5)
    return source


@pytest.mark.anyio
@respx.mock
async def test_api_source_field_mapping():
    """FetcherAgent correctly extracts title/content/url via api_config field mapping."""
    api_response = {
        "data": [
            {"title": "文章一", "body": "正文内容一", "link": "https://example.com/1", "author": "作者A"},
            {"title": "文章二", "body": "正文内容二", "link": "https://example.com/2", "author": "作者B"},
        ]
    }
    respx.get("https://api.example.com/articles").mock(
        return_value=Response(200, json=api_response)
    )

    agent = FetcherAgent()
    source = _make_api_source()
    results = await agent.fetch_source(source)

    assert len(results) == 2
    assert results[0]["title"] == "文章一"
    assert results[0]["content"] == "正文内容一"
    assert results[0]["url"] == "https://example.com/1"
    assert results[0]["author"] == "作者A"


@pytest.mark.anyio
@respx.mock
async def test_api_source_respects_max_items():
    """FetcherAgent truncates results to max_items_per_fetch."""
    api_response = {
        "data": [
            {"title": f"文章{i}", "body": f"内容{i}", "link": f"https://ex.com/{i}"}
            for i in range(10)
        ]
    }
    respx.get("https://api.example.com/articles").mock(
        return_value=Response(200, json=api_response)
    )

    agent = FetcherAgent()
    source = _make_api_source()
    source.fetch_config = FetchConfig(interval_minutes=60, max_items_per_fetch=3)
    results = await agent.fetch_source(source)

    assert len(results) == 3


@pytest.mark.anyio
@respx.mock
async def test_api_source_nested_items_path():
    """FetcherAgent handles dot-separated nested path like 'result.articles'."""
    api_response = {
        "result": {
            "articles": [
                {"title": "嵌套文章", "body": "嵌套内容", "link": "https://ex.com/nested"}
            ]
        }
    }
    respx.get("https://api.example.com/nested").mock(
        return_value=Response(200, json=api_response)
    )

    from unittest.mock import MagicMock
    source = _make_api_source("https://api.example.com/nested")
    source.api_config = ApiConfig(
        items_path="result.articles",
        title_field="title",
        content_field="body",
        url_field="link",
    )
    source.fetch_config = FetchConfig(interval_minutes=60, max_items_per_fetch=5)

    agent = FetcherAgent()
    results = await agent.fetch_source(source)

    assert len(results) == 1
    assert results[0]["title"] == "嵌套文章"


@pytest.mark.anyio
@respx.mock
async def test_rss_source_field_mapping():
    """FetcherAgent correctly parses RSS feed entries."""
    rss_xml = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <item>
      <title>RSS文章标题</title>
      <link>https://rss.example.com/article/1</link>
      <description>RSS文章摘要内容</description>
      <author>rss.author@example.com</author>
    </item>
  </channel>
</rss>"""
    respx.get("https://rss.example.com/feed.xml").mock(
        return_value=Response(200, text=rss_xml)
    )

    agent = FetcherAgent()
    source = _make_rss_source()
    results = await agent.fetch_source(source)

    assert len(results) == 1
    assert results[0]["title"] == "RSS文章标题"
    assert results[0]["url"] == "https://rss.example.com/article/1"
    assert len(results[0]["content"]) > 0


@pytest.mark.anyio
@respx.mock
async def test_fetch_url_extracts_content():
    """fetch_url returns title and content extracted from HTML."""
    html = """<html>
    <head><title>测试页面标题</title></head>
    <body>
      <p>这是页面的主要正文内容，包含有意义的文章文字。</p>
      <script>alert('skip me');</script>
    </body>
    </html>"""
    respx.get("https://example.com/page").mock(
        return_value=Response(200, text=html)
    )

    agent = FetcherAgent()
    result = await agent.fetch_url("https://example.com/page")

    assert result["title"] == "测试页面标题"
    assert "正文内容" in result["content"]
    assert "skip me" not in result["content"]
    assert result["url"] == "https://example.com/page"
