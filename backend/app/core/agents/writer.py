"""WriterAgent — generates initial draft from article analyses."""
from app.core.agents.base import BaseAgent
from app.core.agents.prompts import WRITER_DEFAULT as DEFAULT_SYSTEM


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
