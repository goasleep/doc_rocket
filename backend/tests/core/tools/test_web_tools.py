"""Unit tests for web_search and fetch_url tools."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


async def test_web_search_no_api_key() -> None:
    from app.core.tools.builtin import web_search

    # SystemConfig is imported inside the function body via `from app.models import
    # SystemConfig`, so we patch the class method on the canonical module location.
    mock_config = MagicMock()
    mock_config.search.tavily_api_key = ""

    with patch("app.models.SystemConfig.find_one", new_callable=AsyncMock) as mock_find:
        mock_find.return_value = mock_config
        result = await web_search("test query")

    assert "not configured" in result or "missing" in result.lower()


async def test_fetch_url_truncation() -> None:
    from app.core.tools.builtin import fetch_url

    long_text = "a" * 20000
    html = f"<html><body>{long_text}</body></html>"

    mock_response = MagicMock()
    mock_response.text = html
    mock_response.raise_for_status = MagicMock()

    # httpx is imported inside the function body; patch at the httpx package level.
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await fetch_url("http://example.com", max_chars=1000)

    # Result must respect max_chars plus the truncation marker overhead
    assert len(result) <= 1100
    # builtin.py appends "[内容已截断]" — "截断" is present in both that marker
    # and any English fallback a future implementation might use.
    assert "截断" in result or "truncat" in result.lower()


async def test_fetch_url_http_error() -> None:
    from app.core.tools.builtin import fetch_url
    import httpx

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        # ConnectError is a subclass of HTTPError, which fetch_url catches.
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("connection refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await fetch_url("http://example.com")

    assert "error" in result.lower()
