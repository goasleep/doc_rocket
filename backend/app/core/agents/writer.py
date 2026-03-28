"""WriterAgent — generates initial draft from article analyses."""
from app.core.agents.base import BaseAgent

DEFAULT_SYSTEM = """\
你是一位专业的内容创作者，擅长分析爆款文章的写作框架并进行仿写创作。

任务：根据提供的主题，创作一篇结构清晰、引人入胜的文章。

要求：
1. 基于主题自行规划文章大纲和结构（不要依赖参考文章的具体内容）
2. 融合参考文章的优秀写作手法（Hook类型、框架结构）
3. 使用参考文章中的hook类型和写作框架
4. 加入情绪触发元素
5. 语言风格贴近参考文章
6. 内容必须围绕用户指定的主题展开，不要偏离主题

直接输出文章内容，使用Markdown格式。
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
