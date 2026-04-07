"""RefinerAgent — converts raw article content into clean Markdown without LLM."""
from typing import Any


def _markdownify_html(html: str) -> str:
    """Convert HTML to Markdown using markdownify."""
    from markdownify import markdownify as md

    return md(html, heading_style="ATX")


def _trafilatura_extract(html: str) -> str:
    """Extract Markdown from HTML using trafilatura."""
    import trafilatura

    result = trafilatura.extract(html, output_format="markdown", url=None)
    return result or ""


def _is_meaningful_md(text: str) -> bool:
    """Heuristic to check if extracted markdown looks like real content."""
    if not text:
        return False
    stripped = text.strip()
    # Should have enough substance
    if len(stripped) < 100:
        return False
    return True


class RefinerAgent:
    """Refines raw article content into clean Markdown without LLM.

    Uses trafilatura for HTML->Markdown extraction, fallback to markdownify.
    For non-HTML content, applies light normalization.
    """

    def build_content_with_images(
        self, content: str, images: list[Any]
    ) -> str:
        """Build content string with image references for refinement.

        Inserts image placeholders throughout the content at regular intervals
        so they can be included in the refined output at appropriate positions.
        """
        if not images:
            return content

        paragraphs = content.split("\n\n")
        if len(paragraphs) <= 1:
            paragraphs = content.split("\n")

        total_images = len(images)
        if total_images == 0:
            return content

        result_lines = []
        image_idx = 0
        interval = max(1, len(paragraphs) // (total_images + 1))

        for i, para in enumerate(paragraphs):
            result_lines.append(para)

            if image_idx < total_images and (i + 1) % interval == 0:
                img = images[image_idx]
                if hasattr(img, "qiniu_url") and img.qiniu_url:
                    url = img.qiniu_url
                elif hasattr(img, "original_url") and img.original_url:
                    url = img.original_url
                else:
                    continue

                alt = getattr(img, "alt", "") or "文章配图"
                result_lines.append(f"\n[图片 {image_idx + 1}: {alt}]({url})\n")
                image_idx += 1

        while image_idx < total_images:
            img = images[image_idx]
            if hasattr(img, "qiniu_url") and img.qiniu_url:
                url = img.qiniu_url
            elif hasattr(img, "original_url") and img.original_url:
                url = img.original_url
            else:
                image_idx += 1
                continue

            alt = getattr(img, "alt", "") or "文章配图"
            result_lines.append(f"\n[图片 {image_idx + 1}: {alt}]({url})\n")
            image_idx += 1

        return "\n\n".join(result_lines)

    def run(self, input_text: str, raw_html: str | None = None, images: list[Any] | None = None) -> str:
        """Refine raw article text into clean Markdown.

        Args:
            input_text: The extracted plain text content (fallback if no HTML).
            raw_html: Original HTML content if available.
            images: Article images to embed in the output.
        """
        if raw_html and raw_html.strip():
            refined = _trafilatura_extract(raw_html)
            if not _is_meaningful_md(refined):
                refined = _markdownify_html(raw_html)
            if not _is_meaningful_md(refined):
                refined = input_text
        else:
            refined = input_text

        if images:
            refined = self._insert_images_into_markdown(refined, images)

        return refined

    def _insert_images_into_markdown(
        self, markdown: str, images: list[Any]
    ) -> str:
        """Insert images into markdown at appropriate positions.

        Distributes images evenly throughout the document.
        """
        if not images:
            return markdown

        lines = markdown.split("\n")
        if len(lines) <= 1:
            image_md = "\n\n".join(
                f"![{getattr(img, 'alt', '') or '文章配图'}]({img.qiniu_url if hasattr(img, 'qiniu_url') and img.qiniu_url else getattr(img, 'original_url', '')})"
                for img in images
            )
            return markdown + "\n\n" + image_md

        total_lines = len(lines)
        num_images = len(images)
        positions = [
            int((i + 1) * total_lines / (num_images + 1)) for i in range(num_images)
        ]

        result_lines = []
        img_idx = 0
        for i, line in enumerate(lines):
            result_lines.append(line)
            if img_idx < num_images and i == positions[img_idx]:
                img = images[img_idx]
                url = (
                    img.qiniu_url
                    if hasattr(img, "qiniu_url") and img.qiniu_url
                    else getattr(img, "original_url", "")
                )
                alt = getattr(img, "alt", "") or "文章配图"
                result_lines.append(f"\n![{alt}]({url})\n")
                img_idx += 1

        while img_idx < num_images:
            img = images[img_idx]
            url = (
                img.qiniu_url
                if hasattr(img, "qiniu_url") and img.qiniu_url
                else getattr(img, "original_url", "")
            )
            alt = getattr(img, "alt", "") or "文章配图"
            result_lines.append(f"\n![{alt}]({url})\n")
            img_idx += 1

        return "\n".join(result_lines)
