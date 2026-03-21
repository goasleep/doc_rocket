"""Unit tests for dispatch_tool."""
from unittest.mock import AsyncMock

import pytest


async def test_dispatch_unknown_tool() -> None:
    from app.core.tools.registry import dispatch_tool

    result = await dispatch_tool("nonexistent_tool_xyz", {})
    assert "not available" in result or "not found" in result.lower()


async def test_dispatch_known_tool() -> None:
    from app.core.tools.registry import TOOL_REGISTRY, dispatch_tool

    mock_fn = AsyncMock(return_value="mock result")
    original = TOOL_REGISTRY.get("fetch_url")
    TOOL_REGISTRY["fetch_url"] = mock_fn
    try:
        result = await dispatch_tool("fetch_url", {"url": "http://example.com"})
        assert result == "mock result"
        mock_fn.assert_called_once_with(url="http://example.com")
    finally:
        if original:
            TOOL_REGISTRY["fetch_url"] = original
        else:
            del TOOL_REGISTRY["fetch_url"]
