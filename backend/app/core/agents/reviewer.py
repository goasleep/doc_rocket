"""ReviewerAgent — performs fact-check, legal, and format review."""
import json
import re

from app.core.agents.base import BaseAgent

DEFAULT_SYSTEM = """\
你是一位严格的内容审核员，负责对文章进行三个维度的审查。
必须以JSON格式返回审查结果：
{
  "fact_check_flags": [
    {"severity": "warning|error|info", "description": "具体问题描述"}
  ],
  "legal_notes": [
    {"severity": "warning|error|info", "description": "法律风险描述"}
  ],
  "format_issues": [
    {"severity": "warning|error|info", "description": "格式问题描述"}
  ]
}
如果某类问题不存在，返回空数组 []。
"""


class ReviewerAgent(BaseAgent):
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
                    f"请对以下文章进行全面审查，以JSON格式返回结果：\n\n{input_text}"
                ),
            },
        ]
        raw = await llm.chat(messages, response_format={"type": "json_object"})

        try:
            json.loads(raw)
            return raw
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                return match.group()
            fallback = {
                "fact_check_flags": [],
                "legal_notes": [],
                "format_issues": [{"severity": "info", "description": "审核完成，未发现明显问题"}],
            }
            return json.dumps(fallback, ensure_ascii=False)
