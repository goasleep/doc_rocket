"""AnalyzerAgent — analyzes article content and returns structured ArticleAnalysis data."""
import json
from typing import Any

from app.core.agents.base import BaseAgent

# Max chars to send to LLM (approx 8000 tokens for moonshot-v1-32k)
MAX_CONTENT_CHARS = 12000

ANALYSIS_SCHEMA_PROMPT = """\
请分析以下文章，以JSON格式返回分析结果。JSON结构如下：
{
  "quality_score": 0-100,
  "quality_breakdown": {
    "content_depth": 0-100,
    "readability": 0-100,
    "originality": 0-100,
    "virality_potential": 0-100
  },
  "hook_type": "痛点型|好奇型|数字型|故事型|争议型|其他",
  "framework": "PAS|AIDA|故事型|清单型|问答型|其他",
  "emotional_triggers": ["情绪词1", "情绪词2"],
  "key_phrases": ["金句1", "金句2"],
  "keywords": ["关键词1", "关键词2"],
  "structure": {
    "intro": "开头描述",
    "body_sections": ["段落1主题", "段落2主题"],
    "cta": "结尾行动号召类型"
  },
  "style": {
    "tone": "犀利|温暖|幽默|严肃|口语化",
    "formality": "正式|半正式|口语化",
    "avg_sentence_length": 平均句子字数
  },
  "target_audience": "目标读者描述"
}"""


class AnalyzerAgent(BaseAgent):
    async def run(self, input_text: str) -> dict[str, Any]:  # type: ignore[override]
        """Analyze article content and return structured dict matching ArticleAnalysis fields."""
        # Truncate if too long
        content = input_text[:MAX_CONTENT_CHARS]
        if len(input_text) > MAX_CONTENT_CHARS:
            content += "\n[内容已截断...]"

        llm = await self._get_llm()
        messages = [
            {"role": "system", "content": self._system_prompt() + "\n\n" + ANALYSIS_SCHEMA_PROMPT},
            {"role": "user", "content": f"请分析以下文章：\n\n{content}"},
        ]

        raw = await llm.chat(
            messages,
            response_format={"type": "json_object"},
        )

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # Fallback: extract JSON block from response
            import re
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                data = json.loads(match.group())
            else:
                data = {}

        # Normalize to expected field names
        return {
            "quality_score": float(data.get("quality_score", 0)),
            "quality_breakdown": data.get("quality_breakdown", {}),
            "hook_type": data.get("hook_type", ""),
            "framework": data.get("framework", ""),
            "emotional_triggers": data.get("emotional_triggers", []),
            "key_phrases": data.get("key_phrases", []),
            "keywords": data.get("keywords", []),
            "structure": data.get("structure", {}),
            "style": data.get("style", {}),
            "target_audience": data.get("target_audience", ""),
        }
