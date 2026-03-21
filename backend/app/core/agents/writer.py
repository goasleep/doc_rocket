"""WriterAgent — generates initial draft from article analyses."""
from app.core.agents.base import BaseAgent

DEFAULT_SYSTEM = """\
你是一位专业的内容创作者，擅长分析爆款文章的写作框架并进行仿写创作。
请根据提供的参考素材分析，创作一篇结构清晰、引人入胜的文章。
- 融合参考文章的优秀写作手法
- 使用参考文章中的hook类型和写作框架
- 加入情绪触发元素
- 语言风格贴近参考文章
"""


class WriterAgent(BaseAgent):
    def _system_prompt(self) -> str:
        if self.agent_config and self.agent_config.system_prompt:
            return self.agent_config.system_prompt
        return DEFAULT_SYSTEM

    async def run(self, input_text: str) -> str:
        llm = await self._get_llm()
        messages = [
            {"role": "system", "content": self._system_prompt()},
            {
                "role": "user",
                "content": (
                    f"以下是参考素材的分析结果，请基于这些素材创作一篇新文章：\n\n"
                    f"{input_text}\n\n"
                    f"请直接输出文章内容，使用Markdown格式。"
                ),
            },
        ]
        response = await llm.chat(messages)
        return response.content or ""
