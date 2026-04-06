"""EditorAgent — polishes draft, removes AI patterns, generates 3 title candidates."""
import json
import re

from app.core.agents.base import BaseAgent
from app.core.agents.prompts import EDITOR_DEFAULT as DEFAULT_SYSTEM


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
            # Extract JSON object block if wrapped in markdown
            extracted = _extract_json_object(raw)
            if extracted:
                try:
                    data = json.loads(extracted)
                    candidates = data.get("title_candidates", [])
                    while len(candidates) < 3:
                        candidates.append(f"候选标题{len(candidates) + 1}")
                    data["title_candidates"] = candidates[:3]
                    return json.dumps(data, ensure_ascii=False)
                except json.JSONDecodeError:
                    pass
            # Fallback: wrap raw content
            fallback = {
                "content": raw,
                "title_candidates": ["候选标题1", "候选标题2", "候选标题3"],
                "changed_sections": [],
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
