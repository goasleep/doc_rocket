"""RefinerAgent — converts raw fetched article text into clean, structured Markdown."""
from typing import Any

from app.core.agents.base import AgentContext, BaseAgent
from app.core.agents.prompts import REFINER_SYSTEM_PROMPT

# Max chars to send to LLM for refinement
MAX_CONTENT_CHARS = 16000


class RefinerAgent(BaseAgent):
    def build_content_with_images(
        self, content: str, images: list[Any]
    ) -> str:
        """Build content string with image references for refinement.

        Inserts image placeholders throughout the content at regular intervals
        so the LLM can include them in the refined output at appropriate positions.
        """
        if not images:
            return content

        # Split content into paragraphs
        paragraphs = content.split('\n\n')
        if len(paragraphs) <= 1:
            paragraphs = content.split('\n')

        # Calculate how often to insert images (distribute evenly)
        total_images = len(images)
        if total_images == 0:
            return content

        result_lines = []
        image_idx = 0

        # Insert an image every N paragraphs
        interval = max(1, len(paragraphs) // (total_images + 1))

        for i, para in enumerate(paragraphs):
            result_lines.append(para)

            # Insert image at interval
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

        # Add any remaining images at the end
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

    async def run(
        self, input_text: str, context: AgentContext | None = None, images: list[Any] | None = None
    ) -> str:
        """Refine raw article text into clean Markdown."""
        content = input_text[:MAX_CONTENT_CHARS]
        if len(input_text) > MAX_CONTENT_CHARS:
            content += "\n[内容已截断...]"

        llm = await self._get_llm()
        self._last_llm = llm  # Store for token usage recording

        # Use agent_config system_prompt if available, fallback to default
        system_prompt = self._base_system_prompt()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"请整理以下文章内容：\n\n{content}"},
        ]

        chat_response = await llm.chat(messages)

        # Record token usage if context is provided
        if context:
            await self._record_token_usage(chat_response, context)

        refined = chat_response.content or input_text

        # Post-process: insert images into the refined markdown
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

        # Split markdown into lines
        lines = markdown.split("\n")
        if len(lines) <= 1:
            # If single line, just append images at the end
            image_md = "\n\n".join(
                f"![{getattr(img, 'alt', '') or '文章配图'}]({img.qiniu_url if hasattr(img, 'qiniu_url') and img.qiniu_url else getattr(img, 'original_url', '')})"
                for img in images
            )
            return markdown + "\n\n" + image_md

        # Calculate positions to insert images (distribute evenly)
        total_lines = len(lines)
        num_images = len(images)
        positions = [
            int((i + 1) * total_lines / (num_images + 1)) for i in range(num_images)
        ]

        # Insert images at calculated positions
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

        # Add any remaining images at the end
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
