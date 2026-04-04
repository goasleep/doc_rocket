"""Markdown theme management for WeChat MP.

This module provides theme loading and CSS inlining functionality
using github-markdown-css and other theme sources.
"""

import re
from pathlib import Path
from typing import ClassVar


class MarkdownThemeError(Exception):
    """Exception raised for theme-related errors."""


class MarkdownThemeManager:
    """Manager for markdown themes.

    Provides loading and application of CSS themes for markdown content,
    with automatic CSS inlining for WeChat MP compatibility.
    """

    # Available themes from github-markdown-css
    AVAILABLE_THEMES: ClassVar[list[str]] = [
        "github-markdown",  # Default, auto light/dark
        "github-markdown-light",
        "github-markdown-dark",
        "github-markdown-dark-dimmed",
        "github-markdown-dark-high-contrast",
        "github-markdown-dark-colorblind",
        "github-markdown-light-colorblind",
    ]

    # Custom themes (Qing Mo and others)
    CUSTOM_THEMES: ClassVar[dict[str, str]] = {
        "qing-mo": "青墨主题 - 青绿色系，东方美学",
    }

    def __init__(self) -> None:
        """Initialize the theme manager."""
        self._css_cache: dict[str, str] = {}
        self._package_path = self._find_package_path()

    def _find_package_path(self) -> Path:
        """Find the github-markdown-css package path.

        Returns:
            Path to the node_modules/github-markdown-css directory.

        Raises:
            MarkdownThemeError: If the package is not found.
        """
        # Try multiple possible paths
        backend_dir = Path(__file__).parent.parent
        project_root = backend_dir.parent

        possible_paths = [
            # From backend/app/core/ -> project root -> frontend
            project_root / "frontend" / "node_modules" / "github-markdown-css",
            # From backend/app/core/ -> project root
            project_root / "node_modules" / "github-markdown-css",
            # Current working directory
            Path.cwd() / "frontend" / "node_modules" / "github-markdown-css",
            Path.cwd() / "node_modules" / "github-markdown-css",
            # Parent of current working directory
            Path.cwd().parent / "frontend" / "node_modules" / "github-markdown-css",
            # Absolute path from home
            Path.home() / "Project" / "full-stack-fastapi-template" / "frontend" / "node_modules" / "github-markdown-css",
        ]

        for path in possible_paths:
            if path.exists():
                # Found package at this path
                return path

        raise MarkdownThemeError(
            "github-markdown-css not found. Please run: "
            "cd frontend && pnpm add github-markdown-css"
        )

    def load_theme_css(self, theme_name: str) -> str:
        """Load CSS content for a theme.

        Args:
            theme_name: Name of the theme to load.

        Returns:
            CSS content as string.

        Raises:
            MarkdownThemeError: If theme is not found.
        """
        # Check cache first
        if theme_name in self._css_cache:
            return self._css_cache[theme_name]

        # Handle custom themes
        if theme_name == "qing-mo":
            from app.core.markdown import COLORS

            css = self._generate_qing_mo_css(COLORS)
            self._css_cache[theme_name] = css
            return css

        # Load from github-markdown-css
        css_file = self._package_path / f"{theme_name}.css"
        if not css_file.exists():
            available = ", ".join(self.AVAILABLE_THEMES + list(self.CUSTOM_THEMES.keys()))
            raise MarkdownThemeError(
                f"Theme '{theme_name}' not found. Available: {available}"
            )

        css = css_file.read_text(encoding="utf-8")

        # Modify CSS for WeChat MP compatibility
        css = self._adapt_css_for_wechat(css)

        self._css_cache[theme_name] = css
        return css

    def _adapt_css_for_wechat(self, css: str) -> str:
        """Adapt CSS for WeChat MP compatibility.

        WeChat MP has limitations on CSS selectors and properties.
        This method adapts the CSS to work within those constraints.

        Args:
            css: Original CSS content.

        Returns:
            Adapted CSS content.
        """
        # Remove CSS variables definitions
        css = re.sub(r"--[\w-]+:\s*[^;]+;", "", css)
        # Convert var() to fallback values or reasonable defaults
        css = re.sub(r"var\(--[\w-]+\s*,\s*([^)]+)\)", r"\1", css)
        css = re.sub(r"var\(--[\w-]+\)", "inherit", css)

        # Remove unsupported at-rules
        css = re.sub(r"@media\s+\([^)]+\)\s*\{[^}]*\}", "", css, flags=re.DOTALL)
        css = re.sub(r"@supports\s+\([^)]+\)\s*\{[^}]*\}", "", css, flags=re.DOTALL)
        css = re.sub(r"@keyframes\s+\w+\s*\{[^}]*\}", "", css, flags=re.DOTALL)

        # Remove complex selectors that WeChat doesn't support
        # :has() selector
        css = re.sub(r"[^{};]*:has\([^)]*\)[^{;]*\{[^}]*\}", "", css, flags=re.DOTALL)
        # :not() with complex selectors
        css = re.sub(r"[^{};]*:not\([^)]*\)[^{;]*\{[^}]*\}", "", css, flags=re.DOTALL)
        # :focus-visible
        css = re.sub(r"[^{};]*:focus-visible[^{;]*\{[^}]*\}", "", css, flags=re.DOTALL)

        # Remove unsupported properties (keep only safe ones)
        supported_props = {
            'color', 'background', 'background-color', 'font-family', 'font-size',
            'font-weight', 'font-style', 'line-height', 'text-align', 'text-decoration',
            'margin', 'margin-top', 'margin-bottom', 'margin-left', 'margin-right',
            'padding', 'padding-top', 'padding-bottom', 'padding-left', 'padding-right',
            'border', 'border-top', 'border-bottom', 'border-left', 'border-right',
            'border-radius', 'border-collapse', 'border-spacing', 'border-color',
            'width', 'height', 'max-width', 'min-width', 'max-height', 'min-height',
            'display', 'overflow', 'overflow-x', 'overflow-y', 'white-space',
            'list-style', 'list-style-type', 'list-style-position',
            'box-shadow', 'vertical-align',
        }

        # Parse and filter CSS rules
        adapted_css = []
        for rule in re.finditer(r'([^{]+)\{([^}]+)\}', css):
            selector = rule.group(1).strip()
            properties = rule.group(2).strip()

            # Skip complex selectors
            if any(c in selector for c in [':has', ':not', ':focus-visible', '~', '+', '>']):
                continue

            # Filter properties
            filtered_props = []
            for prop in re.finditer(r'([\w-]+)\s*:\s*([^;]+);?', properties):
                prop_name = prop.group(1).strip()
                if prop_name in supported_props:
                    filtered_props.append(f"{prop_name}: {prop.group(2).strip()}")

            if filtered_props:
                adapted_css.append(f"{selector} {{ {'; '.join(filtered_props)} }}")

        return '\n'.join(adapted_css)

    def _generate_qing_mo_css(self, colors: dict[str, str]) -> str:
        """Generate Qing Mo theme CSS.

        Args:
            colors: Color palette dictionary.

        Returns:
            CSS content as string.
        """
        return f"""
        .markdown-body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
            font-size: 16px;
            line-height: 1.85;
            color: {colors['text']};
            background-color: {colors['bg']};
            padding: 24px;
        }}
        .markdown-body h1 {{
            font-size: 22px;
            font-weight: 700;
            margin: 32px 0 20px 0;
            color: {colors['text']};
            border-left: 4px solid {colors['primary']};
            padding-left: 14px;
            line-height: 1.4;
        }}
        .markdown-body h2 {{
            font-size: 19px;
            font-weight: 600;
            margin: 28px 0 16px 0;
            color: {colors['text']};
            border-left: 3px solid {colors['primary_light']};
            padding-left: 12px;
            line-height: 1.4;
        }}
        .markdown-body h3 {{
            font-size: 17px;
            font-weight: 600;
            margin: 24px 0 14px 0;
            color: {colors['text']};
            line-height: 1.4;
        }}
        .markdown-body p {{
            font-size: 16px;
            line-height: 1.85;
            margin: 16px 0;
            color: {colors['text']};
            text-align: justify;
            letter-spacing: 0.02em;
        }}
        .markdown-body blockquote {{
            background: linear-gradient(135deg, {colors['bg']} 0%, #ffffff 100%);
            border-left: 4px solid {colors['primary']};
            padding: 16px 20px;
            margin: 20px 0;
            color: {colors['text_light']};
            font-size: 15px;
            line-height: 1.75;
            border-radius: 0 8px 8px 0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}
        .markdown-body code {{
            background-color: {colors['bg_code']};
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'SF Mono', Monaco, 'Courier New', monospace;
            font-size: 14px;
            color: {colors['code_inline']};
            border: 1px solid {colors['border']};
        }}
        .markdown-body pre {{
            background-color: {colors['code_block_bg']};
            color: {colors['code_block_text']};
            padding: 20px;
            border-radius: 10px;
            overflow-x: auto;
            margin: 20px 0;
            font-size: 14px;
            line-height: 1.6;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
        }}
        .markdown-body pre code {{
            background: transparent;
            border: none;
            padding: 0;
            color: {colors['code_block_text']};
        }}
        .markdown-body a {{
            color: {colors['primary']};
            text-decoration: none;
            border-bottom: 1px solid {colors['primary_light']};
            padding-bottom: 1px;
        }}
        .markdown-body ul, .markdown-body ol {{
            margin: 16px 0;
            padding-left: 28px;
        }}
        .markdown-body li {{
            font-size: 16px;
            line-height: 1.85;
            margin: 10px 0;
            color: {colors['text']};
        }}
        .markdown-body img {{
            max-width: 100%;
            height: auto;
            display: block;
            margin: 20px auto;
            border-radius: 8px;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
        }}
        .markdown-body table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 15px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            border-radius: 8px;
            overflow: hidden;
        }}
        .markdown-body th {{
            background-color: {colors['bg_code']};
            color: {colors['text']};
            font-weight: 600;
            padding: 12px 16px;
            text-align: left;
            border-bottom: 2px solid {colors['border']};
        }}
        .markdown-body td {{
            padding: 12px 16px;
            border-bottom: 1px solid {colors['border']};
            color: {colors['text']};
        }}
        """

    def apply_theme(
        self,
        html_content: str,
        theme_name: str = "github-markdown",
        base_url: str = "",
    ) -> str:
        """Apply a theme to HTML content.

        Args:
            html_content: HTML content to style.
            theme_name: Name of the theme to apply.
            base_url: Base URL for resolving relative URLs.

        Returns:
            HTML with inlined CSS styles.
        """
        css = self.load_theme_css(theme_name)

        # Wrap content in markdown-body container with style tag
        # WeChat MP supports <style> tags in the content
        wrapped_html = f"""<div class="markdown-body">{html_content}</div>"""

        # For WeChat MP, we need to inline the styles
        # Use premailer with more lenient settings
        try:
            from premailer import Premailer

            # Create a minimal HTML document
            full_html = f"""<!DOCTYPE html>
<html>
<head>
<style>{css}</style>
</head>
<body>
{wrapped_html}
</body>
</html>"""

            premailer = Premailer(
                full_html,
                base_url=base_url,
                remove_classes=False,  # Keep classes for debugging
                strip_important=False,
                keep_style_tags=False,
                exclude_queries=True,  # Don't process media queries
            )
            result = premailer.transform()

            # Extract just the body content
            body_match = re.search(r'<body[^>]*>(.*?)</body>', result, re.DOTALL)
            if body_match:
                return body_match.group(1).strip()
            return wrapped_html

        except Exception:
            # Fallback: embed CSS in style tag (WeChat MP supports this)
            return f"""<style>{css}</style>{wrapped_html}"""

    def get_available_themes(self) -> dict[str, str]:
        """Get list of available themes with descriptions.

        Returns:
            Dictionary mapping theme names to descriptions.
        """
        themes = {}

        # GitHub themes
        for theme in self.AVAILABLE_THEMES:
            if theme == "github-markdown":
                themes[theme] = "GitHub (Auto light/dark)"
            elif theme == "github-markdown-light":
                themes[theme] = "GitHub Light"
            elif theme == "github-markdown-dark":
                themes[theme] = "GitHub Dark"
            elif theme == "github-markdown-dark-dimmed":
                themes[theme] = "GitHub Dark Dimmed"
            elif theme == "github-markdown-dark-high-contrast":
                themes[theme] = "GitHub Dark High Contrast"
            elif theme == "github-markdown-dark-colorblind":
                themes[theme] = "GitHub Dark Colorblind"
            elif theme == "github-markdown-light-colorblind":
                themes[theme] = "GitHub Light Colorblind"

        # Custom themes
        themes.update(self.CUSTOM_THEMES)

        return themes


# Global theme manager instance
theme_manager = MarkdownThemeManager()


def apply_markdown_theme(
    html_content: str,
    theme_name: str = "github-markdown",
    base_url: str = "",
) -> str:
    """Convenience function to apply a theme to HTML content.

    Args:
        html_content: HTML content to style.
        theme_name: Name of the theme to apply.
        base_url: Base URL for resolving relative URLs.

    Returns:
        HTML with inlined CSS styles.
    """
    return theme_manager.apply_theme(html_content, theme_name, base_url)


def get_available_themes() -> dict[str, str]:
    """Get list of available themes.

    Returns:
        Dictionary mapping theme names to descriptions.
    """
    return theme_manager.get_available_themes()
