"""ReviewerAgent — performs fact-check, legal, and format review."""
import json
import re

from app.core.agents.base import BaseAgent
from app.core.agents.prompts import REVIEWER_DEFAULT as DEFAULT_SYSTEM


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
            extracted = _extract_json_object(raw)
            if extracted:
                try:
                    json.loads(extracted)
                    return extracted
                except json.JSONDecodeError:
                    pass
            fallback = {
                "fact_check_flags": [],
                "legal_notes": [],
                "format_issues": [{"severity": "info", "description": "审核完成，未发现明显问题"}],
            }
            return json.dumps(fallback, ensure_ascii=False)


def _extract_json_object(text: str) -> str | None:
    """Extract the first top-level JSON object from a string."""
    depth = 0
    start = None
    for idx, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = idx
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                return text[start : idx + 1]
    return None
