"""InsightSnapshotService — pre-aggregated knowledge base analytics."""
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

from app.models import (
    Article,
    ArticleAnalysis,
    DistributionItem,
    InsightSnapshot,
    InsightSnapshotOverview,
    QualityScoreBucket,
    SuggestionDimensionItem,
    WordCloudItem,
)


# 中文停用词列表（简化版）
CHINESE_STOPWORDS = {
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个", "上", "也",
    "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好", "自己", "这", "那",
    "这些", "那些", "这个", "那个", "之", "与", "及", "等", "或", "但", "而", "如果", "因为",
    "所以", "虽然", "但是", "可以", "需要", "进行", "通过", "对", "将", "并", "且", "为", "以",
    "及", "其", "它", "他", "她", "们", "个", "种", "类", "些", "者", "家", "员", "性",
    "学", "中", "大", "小", "多", "少", "高", "低", "长", "短", "来", "过", "下", "前",
    "后", "内", "外", "里", "间", "边", "面", "头", "部", "身", "体", "地", "得", "着",
    "过", "给", "让", "向", "往", "从", "把", "被", "叫", "让", "请", "使", "得", "等",
}


class InsightSnapshotService:
    """Service for generating insight snapshots."""

    BATCH_SIZE = 500  # 每批处理的文章数

    @classmethod
    async def generate(cls) -> InsightSnapshot:
        """Generate a new insight snapshot by aggregating all article analyses.

        Uses batch pagination to handle large datasets efficiently.
        Returns the created InsightSnapshot document.
        """
        # 获取文章统计
        total_articles = await Article.count()

        # 收集所有分析数据
        keyword_counter: Counter = Counter()
        keyword_score_sum: dict[str, float] = defaultdict(float)
        emotional_trigger_counter: Counter = Counter()
        emotional_trigger_score_sum: dict[str, float] = defaultdict(float)
        framework_counter: Counter = Counter()
        hook_type_counter: Counter = Counter()
        topic_counter: Counter = Counter()
        quality_scores: list[float] = []
        suggestions_by_dimension: dict[str, Counter] = defaultdict(Counter)

        analyzed_count = 0
        skip = 0

        while True:
            # 分批获取 ArticleAnalysis
            analyses = await ArticleAnalysis.find_all().skip(skip).limit(cls.BATCH_SIZE).to_list()

            if not analyses:
                break

            for analysis in analyses:
                analyzed_count += 1
                quality_score = analysis.quality_score
                quality_scores.append(quality_score)

                # 聚合关键词
                for keyword in analysis.keywords:
                    if keyword and len(keyword) > 1:  # 过滤单字符
                        keyword_counter[keyword] += 1
                        keyword_score_sum[keyword] += quality_score

                # 聚合情绪触发词
                for trigger in analysis.emotional_triggers:
                    if trigger and len(trigger) > 1:
                        emotional_trigger_counter[trigger] += 1
                        emotional_trigger_score_sum[trigger] += quality_score

                # 聚合框架
                if analysis.framework:
                    framework_counter[analysis.framework] += 1

                # 聚合钩子类型
                if analysis.hook_type:
                    hook_type_counter[analysis.hook_type] += 1

                # 聚合主题
                if analysis.topic:
                    topic_counter[analysis.topic] += 1

                # 聚合改进建议
                for detail in analysis.quality_score_details:
                    dimension = detail.dimension
                    for suggestion in detail.improvement_suggestions:
                        # 提取关键词
                        keywords = cls._extract_keywords(suggestion)
                        for kw in keywords:
                            suggestions_by_dimension[dimension][kw] += 1

            skip += cls.BATCH_SIZE

        # 计算概览指标
        avg_quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        coverage_rate = analyzed_count / total_articles if total_articles > 0 else 0.0

        overview = InsightSnapshotOverview(
            total_articles=total_articles,
            analyzed_count=analyzed_count,
            avg_quality_score=round(avg_quality_score, 2),
            coverage_rate=round(coverage_rate, 4),
        )

        # 构建词云数据
        keyword_cloud = cls._build_word_cloud(keyword_counter, keyword_score_sum)
        emotional_trigger_cloud = cls._build_word_cloud(
            emotional_trigger_counter, emotional_trigger_score_sum
        )

        # 构建分布数据
        framework_distribution = cls._build_distribution(framework_counter)
        hook_type_distribution = cls._build_distribution(hook_type_counter)
        topic_distribution = cls._build_distribution(topic_counter)

        # 构建改进建议聚合
        suggestion_aggregation = cls._build_suggestion_aggregation(suggestions_by_dimension)

        # 构建质量分数分布
        quality_score_distribution = cls._build_quality_distribution(quality_scores)

        # 创建快照
        snapshot = InsightSnapshot(
            scope="global",
            overview=overview,
            keyword_cloud=keyword_cloud,
            emotional_trigger_cloud=emotional_trigger_cloud,
            framework_distribution=framework_distribution,
            hook_type_distribution=hook_type_distribution,
            topic_distribution=topic_distribution,
            suggestion_aggregation=suggestion_aggregation,
            quality_score_distribution=quality_score_distribution,
            article_count=analyzed_count,
        )

        await snapshot.insert()
        return snapshot

    @staticmethod
    def _extract_keywords(text: str) -> list[str]:
        """从文本中提取关键词（简单分词，去除停用词）."""
        if not text:
            return []

        # 移除非中文字符，保留中文
        chinese_chars = re.findall(r'[\u4e00-\u9fff]+', text)
        if not chinese_chars:
            return []

        # 简单分词：2-4字词组
        keywords = []
        for segment in chinese_chars:
            for length in range(2, min(5, len(segment) + 1)):
                for i in range(len(segment) - length + 1):
                    word = segment[i:i + length]
                    if word not in CHINESE_STOPWORDS:
                        keywords.append(word)

        return keywords

    @staticmethod
    def _build_word_cloud(counter: Counter, score_sum: dict[str, float]) -> list[WordCloudItem]:
        """构建词云数据，包含平均质量分."""
        # 取频次前100的词
        most_common = counter.most_common(100)
        return [
            WordCloudItem(
                name=word,
                value=count,
                avg_score=round(score_sum[word] / count, 2) if count > 0 else 0.0,
            )
            for word, count in most_common
        ]

    @staticmethod
    def _build_distribution(counter: Counter) -> list[DistributionItem]:
        """构建分布数据."""
        return [
            DistributionItem(name=name, value=count)
            for name, count in counter.most_common(20)  # 取前20
        ]

    @staticmethod
    def _build_suggestion_aggregation(
        suggestions_by_dimension: dict[str, Counter],
    ) -> list[SuggestionDimensionItem]:
        """构建改进建议聚合数据."""
        result = []
        for dimension, counter in suggestions_by_dimension.items():
            # 取每个维度前20个高频关键词
            keywords = [
                WordCloudItem(name=word, value=count, avg_score=0.0)
                for word, count in counter.most_common(20)
            ]
            result.append(
                SuggestionDimensionItem(dimension=dimension, keywords=keywords)
            )
        return result

    @staticmethod
    def _build_quality_distribution(quality_scores: list[float]) -> list[QualityScoreBucket]:
        """构建质量分数分布（直方图桶）."""
        buckets = [
            (0, 20, "0-20"),
            (21, 40, "21-40"),
            (41, 60, "41-60"),
            (61, 80, "61-80"),
            (81, 100, "81-100"),
        ]

        bucket_counts = {label: 0 for _, _, label in buckets}

        for score in quality_scores:
            for min_score, max_score, label in buckets:
                if min_score <= score <= max_score:
                    bucket_counts[label] += 1
                    break

        return [
            QualityScoreBucket(range=label, count=bucket_counts[label])
            for _, _, label in buckets
        ]

    @classmethod
    async def get_latest(cls) -> InsightSnapshot | None:
        """Get the most recent snapshot."""
        return await InsightSnapshot.find_one(
            {"scope": "global"},
            sort=[("created_at", -1)],
        )

    @classmethod
    async def list_history(cls, skip: int = 0, limit: int = 20) -> tuple[list[InsightSnapshot], int]:
        """List snapshot history with pagination."""
        count = await InsightSnapshot.count()
        snapshots = await (
            InsightSnapshot.find({"scope": "global"})
            .sort("-created_at")
            .skip(skip)
            .limit(limit)
            .to_list()
        )
        return snapshots, count
