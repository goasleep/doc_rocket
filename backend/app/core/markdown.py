"""Markdown to WeChat HTML converter.

This module provides functionality to convert Markdown content to HTML
with inline CSS styles optimized for WeChat MP (WeChat Official Account) articles.
"""

import re
from typing import Any

import markdown
from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor
from xml.etree import ElementTree as ET


# WeChat MP style definitions
WECHAT_STYLES = {
    "h1": "font-size: 24px; font-weight: bold; margin: 20px 0 16px 0; color: #333333;",
    "h2": "font-size: 20px; font-weight: bold; margin: 18px 0 14px 0; color: #333333;",
    "h3": "font-size: 18px; font-weight: bold; margin: 16px 0 12px 0; color: #333333;",
    "h4": "font-size: 16px; font-weight: bold; margin: 14px 0 10px 0; color: #333333;",
    "p": "font-size: 16px; line-height: 1.75; margin: 12px 0; color: #333333;",
    "blockquote": (
        "border-left: 4px solid #999999; "
        "padding-left: 16px; "
        "margin: 16px 0; "
        "color: #666666; "
        "font-style: italic;"
    ),
    "code": (
        "background-color: #f5f5f5; "
        "padding: 2px 6px; "
        "border-radius: 3px; "
        "font-family: 'Courier New', monospace; "
        "font-size: 14px; "
        "color: #d63384;"
    ),
    "pre": (
        "background-color: #f8f9fa; "
        "padding: 16px; "
        "border-radius: 6px; "
        "overflow-x: auto; "
        "margin: 16px 0;"
    ),
    "a": "color: #576b95; text-decoration: none;",
    "ul": "margin: 12px 0; padding-left: 24px;",
    "ol": "margin: 12px 0; padding-left: 24px;",
    "li": "font-size: 16px; line-height: 1.75; margin: 6px 0; color: #333333;",
    "strong": "font-weight: bold;",
    "em": "font-style: italic;",
    "img": "max-width: 100%; height: auto; display: block; margin: 16px 0;",
}


class WeChatStyleProcessor(Treeprocessor):
    """Treeprocessor that adds inline CSS styles for WeChat MP compatibility.

    This processor traverses the HTML element tree and adds inline style
    attributes based on the tag type, ensuring proper rendering in WeChat MP.
    """

    def run(self, root: ET.Element) -> None:
        """Process the element tree and add inline styles.

        Args:
            root: The root element of the HTML tree.
        """
        for element in root.iter():
            tag = element.tag.lower()
            if tag in WECHAT_STYLES:
                # Get existing style if any
                existing_style = element.get("style", "")
                new_style = WECHAT_STYLES[tag]

                # Combine styles, with new styles taking precedence
                if existing_style:
                    element.set("style", f"{existing_style}; {new_style}")
                else:
                    element.set("style", new_style)

            # Special handling for code inside pre (code blocks)
            if tag == "pre":
                for child in element.iter():
                    if child.tag.lower() == "code":
                        # Code blocks should not have inline code styling
                        child.set("style", "font-family: 'Courier New', monospace; font-size: 14px;")


class WeChatExtension(Extension):
    """Markdown extension for WeChat MP style processing.

    This extension registers the WeChatStyleProcessor to add inline CSS styles
    to the generated HTML for optimal WeChat MP rendering.
    """

    def extendMarkdown(self, md: markdown.Markdown) -> None:
        """Register the WeChat style processor.

        Args:
            md: The Markdown instance to extend.
        """
        md.treeprocessors.register(
            WeChatStyleProcessor(md), "wechat_style", 15
        )


def markdown_to_wechat_html(markdown_text: str, title: str = "") -> str:
    """Convert Markdown text to WeChat MP compatible HTML.

    This function converts Markdown content to HTML with inline CSS styles
    that are optimized for WeChat Official Account articles.

    Args:
        markdown_text: The Markdown content to convert.
        title: Optional title to include as an h1 at the top.

    Returns:
        HTML string with inline styles for WeChat MP compatibility.

    Example:
        >>> md = "# Hello\\n\\nThis is **bold** text."
        >>> html = markdown_to_wechat_html(md, "My Article")
        >>> print(html)
    """
    # Create Markdown converter with extensions
    md = markdown.Markdown(
        extensions=[
            "fenced_code",
            "tables",
            "nl2br",
            WeChatExtension(),
        ]
    )

    # Convert markdown to HTML
    content_html = md.convert(markdown_text)

    # Wrap in container div with WeChat-optimized styles
    container_style = (
        "max-width: 100%; "
        "padding: 20px; "
        "background-color: #ffffff; "
        "font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;"
    )

    # Add title if provided
    if title:
        title_style = WECHAT_STYLES["h1"]
        title_html = f'<h1 style="{title_style}">{title}</h1>'
        content_html = title_html + content_html

    html_output = f'<div style="{container_style}">{content_html}</div>'

    return html_output


def extract_images_from_markdown(markdown_text: str) -> list[str]:
    """Extract image URLs from Markdown text.

    This function uses regex to find all image references in the format
    ![alt](url) and returns a list of the image URLs.

    Args:
        markdown_text: The Markdown content to parse.

    Returns:
        List of image URLs found in the markdown.

    Example:
        >>> md = "![Alt text](https://example.com/image.png)"
        >>> urls = extract_images_from_markdown(md)
        >>> print(urls)
        ['https://example.com/image.png']
    """
    # Pattern to match ![alt](url) or ![alt](url "title")
    pattern = r'!\[([^\]]*)\]\(([^\s")]+)(?:\s+"[^"]*")?\)'

    matches = re.findall(pattern, markdown_text)

    # Extract just the URLs (second capture group)
    image_urls = [match[1] for match in matches]

    return image_urls
