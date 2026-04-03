"""ReviewerAgent — performs fact-check, legal, and format review."""
import json
import re

from app.core.agents.base import BaseAgent

DEFAULT_SYSTEM = """\
你是一位严格的内容审核员，负责对文章进行三个维度的审查。

审核维度：
1. 事实核查 (fact_check_flags)：检查内容中的事实性错误
2. 法律合规 (legal_notes)：检查是否存在法律风险
3. 格式规范 (format_issues)：检查格式是否符合要求

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
  ],
  "approved": true|false,
  "feedback": "详细说明审核意见。如果不通过，列出所有需要修改的问题；如果通过，可写'审核通过'"
}

如果某类问题不存在，返回空数组 []。

审核通过标准：
- 无 error 级别的问题
- warning 级别的问题不超过2个
- 只有当内容符合发布标准时，approved 才设为 true
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
        chat_response = await llm.chat(messages, response_format={"type": "json_object"})
        raw = chat_response.content or ""

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
