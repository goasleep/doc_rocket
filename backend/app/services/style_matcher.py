"""Style matching service for automatic style reference selection."""
import uuid
from dataclasses import dataclass

from app.models import ArticleAnalysis


@dataclass
class StyleMatchResult:
    """Result of style matching."""

    article_ids: list[uuid.UUID]
    primary_id: uuid.UUID | None
    secondary_ids: list[uuid.UUID]
    style_guide: str


class StyleMatcher:
    """Match articles based on topic and style hints.

    This service automatically selects reference articles from the article library
    based on semantic similarity to the topic and optional style preferences.
    """

    # Style hint to keyword mapping for matching
    STYLE_HINT_KEYWORDS = {
        "story": ["故事", "叙述", "案例", "经历", "场景"],
        "data": ["数据", "统计", "研究", "报告", "数字"],
        "sharp": ["犀利", "点评", "评论", "观点", "批判"],
        "casual": ["口语", "轻松", "闲聊", "通俗", "易懂"],
        "suspense": ["悬念", "反转", "揭秘", "震惊", "意外"],
        "contrast": ["对比", "比较", "差异", "差距", " versus"],
        "emotional": ["情绪", "共鸣", "感动", "励志", "焦虑"],
        "practical": ["干货", "实用", "技巧", "方法", "指南"],
    }

    async def match_articles(
        self,
        topic: str,
        style_hints: list[str],
        limit: int = 5,
    ) -> StyleMatchResult:
        """Match articles based on topic and style hints.

        Args:
            topic: The writing topic
            style_hints: Optional style preferences (e.g., ["story", "data"])
            limit: Maximum number of articles to return

        Returns:
            StyleMatchResult with matched articles and style guide
        """
        # Get all analyzed articles
        analyses = await ArticleAnalysis.find_all().to_list()

        if not analyses:
            return StyleMatchResult(
                article_ids=[],
                primary_id=None,
                secondary_ids=[],
                style_guide="",
            )

        # Calculate scores for each article
        scored_analyses = []
        for analysis in analyses:
            score = self._calculate_match_score(topic, style_hints, analysis)
            scored_analyses.append((analysis, score))

        # Sort by score descending
        scored_analyses.sort(key=lambda x: x[1], reverse=True)

        # Select top articles
        top_analyses = scored_analyses[:limit]

        # Classify into primary and secondary
        article_ids = []
        primary_id = None
        secondary_ids = []

        for i, (analysis, score) in enumerate(top_analyses):
            article_ids.append(analysis.article_id)
            if i == 0 and score > 0.3:  # Highest score becomes primary
                primary_id = analysis.article_id
            elif i < 3 and score > 0.15:  # Next 2 become secondary
                secondary_ids.append(analysis.article_id)

        # Generate style guide
        style_guide = self._generate_style_guide(top_analyses, style_hints)

        return StyleMatchResult(
            article_ids=article_ids,
            primary_id=primary_id,
            secondary_ids=secondary_ids,
            style_guide=style_guide,
        )

    def _calculate_match_score(
        self,
        topic: str,
        style_hints: list[str],
        analysis: ArticleAnalysis,
    ) -> float:
        """Calculate how well an article matches the topic and style hints."""
        score = 0.0

        # Topic similarity based on keywords overlap
        topic_keywords = set(topic.lower().split())
        analysis_keywords = set(
            (analysis.keywords or [])
            + (analysis.key_phrases or [])
        )
        analysis_keywords = {k.lower() for k in analysis_keywords}

        if topic_keywords and analysis_keywords:
            overlap = len(topic_keywords & analysis_keywords)
            topic_score = overlap / max(len(topic_keywords), 3)
            score += topic_score * 0.5  # Topic similarity weight: 50%

        # Target audience match
        if analysis.target_audience:
            # Simple heuristic: if topic contains audience-related words
            audience_keywords = ["程序员", "产品经理", "运营", "设计师", "职场"]
            for kw in audience_keywords:
                if kw in topic and kw in analysis.target_audience:
                    score += 0.1
                    break

        # Style hint matching
        if style_hints:
            style_score = self._calculate_style_score(style_hints, analysis)
            score += style_score * 0.4  # Style hint weight: 40%

        # Quality bonus (higher quality articles preferred)
        quality_bonus = (analysis.quality_score or 0) / 1000  # 0-0.1 bonus
        score += quality_bonus

        return min(score, 1.0)

    def _calculate_style_score(
        self,
        style_hints: list[str],
        analysis: ArticleAnalysis,
    ) -> float:
        """Calculate style matching score based on hints."""
        if not style_hints:
            return 0.0

        score = 0.0
        analysis_text = " ".join(
            [
                analysis.hook_type or "",
                analysis.framework or "",
                analysis.style.tone if analysis.style else "",
                " ".join(analysis.emotional_triggers or []),
            ]
        ).lower()

        for hint in style_hints:
            keywords = self.STYLE_HINT_KEYWORDS.get(hint, [hint])
            for kw in keywords:
                if kw.lower() in analysis_text:
                    score += 0.25
                    break

        return min(score / max(len(style_hints), 1), 1.0)

    def _generate_style_guide(
        self,
        scored_analyses: list[tuple[ArticleAnalysis, float]],
        style_hints: list[str],
    ) -> str:
        """Generate a style guide from matched analyses."""
        if not scored_analyses:
            return ""

        parts = []

        # Primary style (highest scored)
        primary, primary_score = scored_analyses[0]
        parts.append(f"【主风格参考】(匹配度: {primary_score:.0%})")
        parts.append(f"- Hook类型: {primary.hook_type or '未指定'}")
        parts.append(f"- 写作框架: {primary.framework or '未指定'}")
        parts.append(f"- 语气风格: {primary.style.tone if primary.style else '未指定'}")
        parts.append(f"- 情绪触发: {', '.join(primary.emotional_triggers[:3]) if primary.emotional_triggers else '未指定'}")

        # Secondary styles
        if len(scored_analyses) > 1:
            parts.append("\n【辅助风格参考】")
            for analysis, score in scored_analyses[1:3]:
                parts.append(f"- 文章: Hook={analysis.hook_type}, 框架={analysis.framework} (匹配度: {score:.0%})")

        # Style hints guidance
        if style_hints:
            parts.append(f"\n【风格偏好要求】")
            hint_labels = {
                "story": "故事化叙述",
                "data": "数据驱动论证",
                "sharp": "犀利点评风格",
                "casual": "口语化表达",
                "suspense": "悬念式开头",
                "contrast": "对比结构",
                "emotional": "情绪共鸣",
                "practical": "实用干货",
            }
            labels = [hint_labels.get(h, h) for h in style_hints]
            parts.append(f"用户偏好: {', '.join(labels)}")
            parts.append("请在创作中优先体现以上风格特点。")

        return "\n".join(parts)
