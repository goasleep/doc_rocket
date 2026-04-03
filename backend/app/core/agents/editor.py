"""EditorAgent — polishes draft, removes AI patterns, generates 3 title candidates."""
import json
import re

from app.core.agents.base import BaseAgent

DEFAULT_SYSTEM = """\
你是一位资深内容编辑，负责：
1. 去除AI味：用更自然、口语化的表达替换AI常见句式
2. 优化段落节奏和可读性
3. 生成3个吸引眼球的标题候选
4. 评估内容质量，决定是否通过审核

必须以JSON格式返回：
{
  "content": "优化后的文章内容（Markdown格式）",
  "title_candidates": ["标题一", "标题二", "标题三"],
  "changed_sections": ["修改了第X段", "..."],
  "approved": true|false,
  "feedback": "如果不通过，详细说明需要修改的问题和具体建议；如果通过，可留空或写'审核通过'"
}

审核标准：
- 内容是否自然流畅，无明显AI痕迹
- 结构是否清晰，逻辑是否通顺
- 标题是否吸引人
- 只有当内容质量达到发布标准时，approved 才设为 true
"""


class EditorAgent(BaseAgent):
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
                    f"请对以下文章进行编辑优化，并以JSON格式返回结果：\n\n{input_text}"
                ),
            },
        ]
        chat_response = await llm.chat(messages, response_format={"type": "json_object"})
        raw = chat_response.content or ""

        # Validate and ensure title_candidates has exactly 3 entries
        try:
            data = json.loads(raw)
            candidates = data.get("title_candidates", [])
            # Ensure exactly 3
            while len(candidates) < 3:
                candidates.append(f"候选标题{len(candidates) + 1}")
            data["title_candidates"] = candidates[:3]
            return json.dumps(data, ensure_ascii=False)
        except json.JSONDecodeError:
            # Extract JSON block if wrapped in markdown
            match = re.search(r"\{.*\}", raw, re.DOTALL)  # type: ignore[arg-type]
            if match:
                return match.group()
            # Fallback: wrap raw content
            fallback = {
                "content": raw,
                "title_candidates": ["候选标题1", "候选标题2", "候选标题3"],
                "changed_sections": [],
            }
            return json.dumps(fallback, ensure_ascii=False)
