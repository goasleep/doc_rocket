"""Unit tests for RefinerAgent without LLM."""
import pytest


@pytest.mark.anyio
async def test_refiner_extracts_markdown_from_html():
    """RefinerAgent converts HTML to Markdown using trafilatura/markdownify."""
    from app.core.agents.refiner import RefinerAgent

    agent = RefinerAgent()
    html = (
        "<html><head><title>Test Page</title></head>"
        "<body><main><h1>Title</h1>"
        "<p>Paragraph one has enough text to be considered real content and not just navigation noise.</p>"
        "<p>Paragraph two also needs to be long enough for trafilatura to extract it properly.</p>"
        "</main></body></html>"
    )

    result = agent.run(input_text="fallback text", raw_html=html)

    assert isinstance(result, str)
    assert "Title" in result
    assert "Paragraph one" in result


@pytest.mark.anyio
async def test_refiner_falls_back_to_input_text():
    """RefinerAgent falls back to input_text when raw_html is empty or invalid."""
    from app.core.agents.refiner import RefinerAgent

    agent = RefinerAgent()
    fallback = "fallback text content"

    result = agent.run(input_text=fallback, raw_html="<html></html>")
    assert fallback in result

    result_no_html = agent.run(input_text=fallback, raw_html=None)
    assert result_no_html == fallback


@pytest.mark.anyio
async def test_refiner_inserts_images():
    """RefinerAgent distributes images into Markdown output."""
    from app.core.agents.refiner import RefinerAgent

    class FakeImage:
        def __init__(self, url):
            self.qiniu_url = url
            self.original_url = url
            self.alt = "test image"

    agent = RefinerAgent()
    markdown = "# Title\n\nLine 1\n\nLine 2\n\nLine 3\n\nLine 4"
    images = [FakeImage("http://example.com/img1.png")]

    result = agent.run(input_text=markdown, raw_html=None, images=images)

    assert "![test image](http://example.com/img1.png)" in result


@pytest.mark.anyio
async def test_refiner_no_images_returns_unchanged():
    """RefinerAgent returns Markdown unchanged when no images are provided."""
    from app.core.agents.refiner import RefinerAgent

    agent = RefinerAgent()
    markdown = "# Title\n\nSome content."

    result = agent.run(input_text=markdown, raw_html=None, images=[])
    assert result == markdown
