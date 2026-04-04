"""RefinerAgent — converts raw fetched article text into clean, structured Markdown."""
from typing import Any

from app.core.agents.base import AgentContext, BaseAgent

# Max chars to send to LLM for refinement
MAX_CONTENT_CHARS = 16000

REFINER_SYSTEM_PROMPT = """\
你是一位专业的中文科技文章整理助手。
你的任务是将原始抓取的文章内容整理为规范的 Markdown 格式。

## 工作原则

1. **保留核心内容**：仅整理格式，不增加、不删除任何实质性内容
2. **清除噪声**：删除导航栏文字、广告文本、版权声明、重复的页脚信息
3. **恢复文档结构**：
   - 根据内容层次使用 #、##、### 标题
   - 将连续段落正确分段
   - 恢复有序列表（1. 2. 3.）和无序列表（- 或 *）
   - 识别并格式化代码块（使用 ``` 包裹，标注语言）
4. **修复格式问题**：清理多余空白、修复编码残缺字符、统一标点
5. **保持语言比例**：中英文混合内容保持原有比例，不翻译

## 图片处理规则（非常重要）

- 原文中标记为 `[图片 N: 描述](URL)` 的内容是文章配图
- 必须将这些图片转换为 Markdown 格式嵌入正文：`![描述](URL)`
- 将图片放在与其内容相关的段落附近，保持原有顺序
- 不要删除任何图片，也不要只在文末列出

## 输出要求

- 直接输出整理后的 Markdown 文本
- 不添加任何解释说明
- 不在开头或结尾添加额外文字
- 保持原文语言（中文文章输出中文，英文文章输出英文）
- 所有图片必须使用 Markdown 格式 `![描述](图片URL)` 嵌入正文
"""


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
