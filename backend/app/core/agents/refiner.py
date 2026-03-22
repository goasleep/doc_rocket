"""RefinerAgent — converts raw fetched article text into clean, structured Markdown."""
from app.core.agents.base import BaseAgent

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

## 输出要求

- 直接输出整理后的 Markdown 文本
- 不添加任何解释说明
- 不在开头或结尾添加额外文字
- 保持原文语言（中文文章输出中文，英文文章输出英文）
"""


class RefinerAgent(BaseAgent):
    async def run(self, input_text: str) -> str:  # type: ignore[override]
        """Refine raw article text into clean Markdown. Returns the refined Markdown string."""
        content = input_text[:MAX_CONTENT_CHARS]
        if len(input_text) > MAX_CONTENT_CHARS:
            content += "\n[内容已截断...]"

        llm = await self._get_llm()
        messages = [
            {"role": "system", "content": REFINER_SYSTEM_PROMPT},
            {"role": "user", "content": f"请整理以下文章内容：\n\n{content}"},
        ]

        chat_response = await llm.chat(messages)
        return chat_response.content or input_text
