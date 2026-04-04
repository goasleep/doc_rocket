"""Markdown to WeChat HTML converter.

This module provides functionality to convert Markdown content to HTML
with inline CSS styles optimized for WeChat MP (WeChat Official Account) articles.

Style Theme: "Qing Mo" (青墨) - A fusion of modern minimalism and Eastern aesthetics
Primary Color: Teal/Cyan (#0d9488) matching the project's design system
"""

import re
from xml.etree import ElementTree as ET

import markdown
from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor

# ============================================================================
# "Qing Mo" (青墨) Theme - WeChat MP Style Definitions
# ============================================================================
# Design Philosophy:
# - Primary: Teal/Cyan (#0d9488) - representing clarity and intelligence
# - Secondary: Warm Gray (#78716c) - for supporting elements
# - Accent: Amber (#f59e0b) - for highlights and emphasis
# - Background: Off-white (#fafaf9) - easy on the eyes
# - Text: Ink Black (#292524) - maximum readability
# ============================================================================

# Color Palette
COLORS = {
    "primary": "#0d9488",        # Teal 600 - main brand color
    "primary_light": "#14b8a6",  # Teal 500 - lighter variant
    "primary_dark": "#0f766e",   # Teal 700 - darker variant
    "secondary": "#78716c",      # Stone 500 - supporting text
    "accent": "#f59e0b",         # Amber 500 - highlights
    "text": "#292524",           # Stone 800 - main text
    "text_light": "#57534e",     # Stone 600 - secondary text
    "bg": "#fafaf9",             # Stone 50 - background
    "bg_code": "#f5f5f4",        # Stone 100 - code background
    "border": "#e7e5e4",         # Stone 200 - borders
    "code_inline": "#dc2626",    # Red 600 - inline code
    "code_block_bg": "#1c1917",  # Stone 900 - code block background
    "code_block_text": "#e7e5e4", # Stone 200 - code block text
}

WECHAT_STYLES = {
    # =========================================================================
    # Headings - With left border accent for visual hierarchy
    # =========================================================================
    "h1": (
        f"font-size: 22px; "
        f"font-weight: 700; "
        f"margin: 32px 0 20px 0; "
        f"color: {COLORS['text']}; "
        f"border-left: 4px solid {COLORS['primary']}; "
        f"padding-left: 14px; "
        f"line-height: 1.4;"
    ),
    "h2": (
        f"font-size: 19px; "
        f"font-weight: 600; "
        f"margin: 28px 0 16px 0; "
        f"color: {COLORS['text']}; "
        f"border-left: 3px solid {COLORS['primary_light']}; "
        f"padding-left: 12px; "
        f"line-height: 1.4;"
    ),
    "h3": (
        f"font-size: 17px; "
        f"font-weight: 600; "
        f"margin: 24px 0 14px 0; "
        f"color: {COLORS['text']}; "
        f"line-height: 1.4;"
    ),
    "h4": (
        f"font-size: 16px; "
        f"font-weight: 600; "
        f"margin: 20px 0 12px 0; "
        f"color: {COLORS['text_light']}; "
        f"line-height: 1.4;"
    ),

    # =========================================================================
    # Paragraphs - Optimized for reading comfort
    # =========================================================================
    "p": (
        f"font-size: 16px; "
        f"line-height: 1.85; "
        f"margin: 16px 0; "
        f"color: {COLORS['text']}; "
        f"text-align: justify; "
        f"letter-spacing: 0.02em;"
    ),

    # =========================================================================
    # Blockquote - Elegant left border with soft background
    # =========================================================================
    "blockquote": (
        f"background: linear-gradient(135deg, {COLORS['bg']} 0%, #ffffff 100%); "
        f"border-left: 4px solid {COLORS['primary']}; "
        f"padding: 16px 20px; "
        f"margin: 20px 0; "
        f"color: {COLORS['text_light']}; "
        f"font-size: 15px; "
        f"line-height: 1.75; "
        f"border-radius: 0 8px 8px 0; "
        f"box-shadow: 0 1px 3px rgba(0,0,0,0.05);"
    ),

    # =========================================================================
    # Inline Code - Subtle highlight
    # =========================================================================
    "code": (
        f"background-color: {COLORS['bg_code']}; "
        f"padding: 2px 6px; "
        f"border-radius: 4px; "
        f"font-family: 'SF Mono', Monaco, 'Courier New', monospace; "
        f"font-size: 14px; "
        f"color: {COLORS['code_inline']}; "
        f"border: 1px solid {COLORS['border']};"
    ),

    # =========================================================================
    # Code Blocks - Dark theme with macOS-style window
    # =========================================================================
    "pre": (
        f"background-color: {COLORS['code_block_bg']}; "
        f"color: {COLORS['code_block_text']}; "
        f"padding: 20px; "
        f"border-radius: 10px; "
        f"overflow-x: auto; "
        f"margin: 20px 0; "
        f"font-size: 14px; "
        f"line-height: 1.6; "
        f"box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);"
    ),

    # =========================================================================
    # Links - Brand-colored with subtle hover effect hint
    # =========================================================================
    "a": (
        f"color: {COLORS['primary']}; "
        f"text-decoration: none; "
        f"border-bottom: 1px solid {COLORS['primary_light']}; "
        f"padding-bottom: 1px;"
    ),

    # =========================================================================
    # Lists - Clean and well-spaced
    # =========================================================================
    "ul": (
        "margin: 16px 0; "
        "padding-left: 28px; "
        "list-style-type: disc;"
    ),
    "ol": (
        "margin: 16px 0; "
        "padding-left: 28px; "
        "list-style-type: decimal;"
    ),
    "li": (
        f"font-size: 16px; "
        f"line-height: 1.85; "
        f"margin: 10px 0; "
        f"color: {COLORS['text']}; "
        f"padding-left: 4px;"
    ),

    # =========================================================================
    # Emphasis
    # =========================================================================
    "strong": (
        f"font-weight: 700; "
        f"color: {COLORS['text']};"
    ),
    "em": (
        f"font-style: italic; "
        f"color: {COLORS['text_light']};"
    ),

    # =========================================================================
    # Images - Centered with subtle shadow
    # =========================================================================
    "img": (
        "max-width: 100%; "
        "height: auto; "
        "display: block; "
        "margin: 20px auto; "
        "border-radius: 8px; "
        "box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);"
    ),

    # =========================================================================
    # Horizontal Rule - Elegant separator
    # =========================================================================
    "hr": (
        f"border: none; "
        f"border-top: 1px solid {COLORS['border']}; "
        f"margin: 32px 0; "
        f"position: relative;"
    ),

    # =========================================================================
    # Tables - Clean and readable
    # =========================================================================
    "table": (
        "width: 100%; "
        "border-collapse: collapse; "
        "margin: 20px 0; "
        "font-size: 15px; "
        "box-shadow: 0 1px 3px rgba(0,0,0,0.05); "
        "border-radius: 8px; "
        "overflow: hidden;"
    ),
    "th": (
        f"background-color: {COLORS['bg_code']}; "
        f"color: {COLORS['text']}; "
        f"font-weight: 600; "
        f"padding: 12px 16px; "
        f"text-align: left; "
        f"border-bottom: 2px solid {COLORS['border']};"
    ),
    "td": (
        f"padding: 12px 16px; "
        f"border-bottom: 1px solid {COLORS['border']}; "
        f"color: {COLORS['text']};"
    ),
    "tr:last-child td": (
        "border-bottom: none;"
    ),
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

            # Skip styling for code inside pre (code blocks get special handling)
            parent = self._get_parent(element, root)
            is_code_in_pre = tag == "code" and parent is not None and parent.tag.lower() == "pre"

            if tag in WECHAT_STYLES and not is_code_in_pre:
                # Get existing style if any
                existing_style = element.get("style", "")
                new_style = WECHAT_STYLES[tag]

                # Combine styles, with new styles taking precedence
                if existing_style:
                    element.set("style", f"{existing_style}; {new_style}")
                else:
                    element.set("style", new_style)

            # Special handling for code inside pre (code blocks)
            if is_code_in_pre:
                element.set(
                    "style",
                    f"font-family: 'SF Mono', Monaco, 'Courier New', monospace; "
                    f"font-size: 14px; "
                    f"color: {COLORS['code_block_text']}; "
                    f"background: transparent; "
                    f"border: none; "
                    f"padding: 0;"
                )

    def _get_parent(self, element: ET.Element, root: ET.Element) -> ET.Element | None:
        """Find the parent element of a given element.

        Args:
            element: The element to find parent for.
            root: The root element to search from.

        Returns:
            The parent element or None if not found.
        """
        for parent in root.iter():
            for child in parent:
                if child is element:
                    return parent
        return None


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


def _apply_inline_styles(html: str) -> str:
    """Apply inline styles to HTML elements using regex replacement.

    This is a post-processing step to ensure all elements have proper styles,
    especially those that may have been missed by the Treeprocessor.

    Args:
        html: The HTML content to process.

    Returns:
        HTML with inline styles applied.
    """
    import re

    # First, handle code blocks (code inside pre) with special styling
    # Replace code inside pre with proper code block styling
    code_block_style = (
        f"font-family: 'SF Mono', Monaco, 'Courier New', monospace; "
        f"font-size: 14px; "
        f"color: {COLORS['code_block_text']}; "
        f"background: transparent; "
        f"border: none; "
        f"padding: 0;"
    )
    # Match <pre><code>...</code></pre> and fix the code style
    html = re.sub(
        r'(<pre[^>]*>\s*<code[^>]*)(style="[^"]*")([^>]*)>',
        rf'\1 style="{code_block_style}"\3>',
        html,
        flags=re.DOTALL
    )
    # Also handle code inside pre that has no style
    html = re.sub(
        r'(<pre[^>]*>\s*<code)(?![^>]*style=)([^>]*)>',
        rf'\1 style="{code_block_style}"\2>',
        html,
        flags=re.DOTALL
    )

    # Apply styles to tags that don't already have style attributes
    for tag, style in WECHAT_STYLES.items():
        # Skip code tag as it's handled specially above
        if tag == "code":
            continue
        # Match tags without style attribute
        pattern = rf'<{tag}\b(?![^>]*\bstyle=)([^>]*)>'
        replacement = rf'<{tag}\1 style="{style}">'
        html = re.sub(pattern, replacement, html, flags=re.IGNORECASE)

    return html


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
    import re

    # Create Markdown converter with extensions
    # Note: nl2br is disabled to prevent code blocks being wrapped in <p> tags
    md = markdown.Markdown(
        extensions=[
            "fenced_code",
            "tables",
            WeChatExtension(),
        ]
    )

    # Convert markdown to HTML
    content_html = md.convert(markdown_text)

    # Post-process: remove <p> tags that wrap <pre> blocks (caused by markdown parsing)
    content_html = re.sub(
        r'<p[^>]*>\s*(<pre[^>]*>.*?</pre>)\s*</p>',
        r'\1',
        content_html,
        flags=re.DOTALL
    )

    # Post-process: remove empty list items (caused by newlines in markdown lists)
    # Matches <li> tags that contain only whitespace or <p> tags with whitespace
    content_html = re.sub(
        r'<li[^>]*>\s*(?:<p[^>]*>\s*</p>)?\s*</li>',
        '',
        content_html,
        flags=re.DOTALL
    )

    # Apply inline styles to any elements that were missed
    content_html = _apply_inline_styles(content_html)

    # Wrap in container div with "Qing Mo" theme optimized styles
    container_style = (
        "max-width: 100%; "
        "padding: 24px; "
        f"background-color: {COLORS['bg']}; "
        "font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif; "
        "-webkit-font-smoothing: antialiased; "
        "-moz-osx-font-smoothing: grayscale;"
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
