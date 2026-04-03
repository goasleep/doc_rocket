import uuid
from datetime import datetime, timezone

from beanie import Document
from pydantic import BaseModel, ConfigDict, Field


def get_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


class RubricCriterion(BaseModel):
    """评分档位标准"""
    min_score: int = Field(..., ge=0, le=100)
    max_score: int = Field(..., ge=0, le=100)
    description: str = Field(..., description="档位描述")

    def matches_score(self, score: float) -> bool:
        """检查分数是否匹配此档位"""
        return self.min_score <= score <= self.max_score


class RubricDimension(BaseModel):
    """评分维度定义"""
    name: str = Field(..., description="维度名称 (content_depth, readability, originality, virality_potential)")
    description: str = Field(..., description="维度描述")
    weight: float = Field(..., ge=0, le=1, description="权重")
    criteria: list[RubricCriterion] = Field(default_factory=list, description="评分档位")

    def get_matching_criterion(self, score: float) -> RubricCriterion | None:
        """根据分数获取匹配的档位"""
        for criterion in self.criteria:
            if criterion.matches_score(score):
                return criterion
        return None


class QualityRubric(Document):
    """质量评分标准"""
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    version: str = Field(..., description="版本号 (如 v1, v2)")
    name: str = Field(..., description="标准名称")
    description: str = Field(default="", description="标准描述")
    dimensions: list[RubricDimension] = Field(default_factory=list, description="评分维度")
    is_active: bool = Field(default=False, description="是否激活")
    created_at: datetime = Field(default_factory=get_datetime_utc)
    updated_at: datetime = Field(default_factory=get_datetime_utc)

    class Settings:
        name = "quality_rubrics"

    def get_dimension(self, name: str) -> RubricDimension | None:
        """根据名称获取维度"""
        for dim in self.dimensions:
            if dim.name == name:
                return dim
        return None

    def calculate_weighted_score(self, scores: dict[str, float]) -> float:
        """计算加权总分

        Args:
            scores: 维度名称到分数的映射

        Returns:
            加权总分
        """
        total_weight = 0.0
        weighted_sum = 0.0
        for dim in self.dimensions:
            if dim.name in scores:
                weighted_sum += scores[dim.name] * dim.weight
                total_weight += dim.weight
        if total_weight == 0:
            return 0.0
        return round(weighted_sum / total_weight, 2)


class QualityRubricCreate(BaseModel):
    version: str
    name: str
    description: str = ""
    dimensions: list[RubricDimension]
    is_active: bool = False


class QualityRubricUpdate(BaseModel):
    version: str | None = None
    name: str | None = None
    description: str | None = None
    dimensions: list[RubricDimension] | None = None
    is_active: bool | None = None


class QualityRubricPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    version: str
    name: str
    description: str
    dimensions: list[RubricDimension]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class QualityRubricsPublic(BaseModel):
    data: list[QualityRubricPublic]
    count: int


# 默认评分标准 v1 数据
DEFAULT_RUBRIC_V1 = {
    "version": "v1",
    "name": "文章质量评分标准 v1",
    "description": "默认文章质量评分标准，包含内容深度、可读性、原创性、AI味道和传播潜力五个维度",
    "dimensions": [
        {
            "name": "content_depth",
            "description": "内容深度与信息密度",
            "weight": 0.25,
            "criteria": [
                {"min_score": 90, "max_score": 100, "description": "深度洞察，独家观点，数据支撑充分，有专业见解"},
                {"min_score": 80, "max_score": 89, "description": "内容充实，观点清晰，有一定数据/案例支撑"},
                {"min_score": 70, "max_score": 79, "description": "内容完整，观点明确，但缺乏深度挖掘"},
                {"min_score": 60, "max_score": 69, "description": "内容浅显，观点普通，信息密度低"},
                {"min_score": 0, "max_score": 59, "description": "内容空洞，缺乏实质信息"},
            ],
        },
        {
            "name": "readability",
            "description": "可读性与表达流畅度",
            "weight": 0.20,
            "criteria": [
                {"min_score": 90, "max_score": 100, "description": "结构清晰，语言精炼，阅读体验极佳"},
                {"min_score": 80, "max_score": 89, "description": "结构合理，表达流畅，易于理解"},
                {"min_score": 70, "max_score": 79, "description": "结构基本清晰，偶有表达不畅"},
                {"min_score": 60, "max_score": 69, "description": "结构混乱，阅读有困难"},
                {"min_score": 0, "max_score": 59, "description": "难以理解，表达糟糕"},
            ],
        },
        {
            "name": "originality",
            "description": "原创性与独特性",
            "weight": 0.20,
            "criteria": [
                {"min_score": 90, "max_score": 100, "description": "独特视角，原创研究，行业首发"},
                {"min_score": 80, "max_score": 89, "description": "观点新颖，有独立思考，非简单整合"},
                {"min_score": 70, "max_score": 79, "description": "有一定个人见解，但参考痕迹明显"},
                {"min_score": 60, "max_score": 69, "description": "主要是信息整合，缺乏原创"},
                {"min_score": 0, "max_score": 59, "description": "大量抄袭或简单搬运"},
            ],
        },
        {
            "name": "ai_flavor",
            "description": "AI味道与自然度（高分=自然人类写作，低分=明显的AI生成痕迹）",
            "weight": 0.15,
            "criteria": [
                {"min_score": 90, "max_score": 100, "description": "完全自然的人类写作风格，有个人特色，情感真挚，无AI痕迹"},
                {"min_score": 80, "max_score": 89, "description": " mostly自然，偶有规范表达，整体有个人风格"},
                {"min_score": 70, "max_score": 79, "description": "有一定AI辅助痕迹，但经人工润色，基本可读"},
                {"min_score": 60, "max_score": 69, "description": "明显的AI生成特征，套路化表达，缺乏个性"},
                {"min_score": 0, "max_score": 59, "description": "典型的AI生成文本，机械、空洞、公式化"},
            ],
        },
        {
            "name": "virality_potential",
            "description": "传播潜力与话题性",
            "weight": 0.20,
            "criteria": [
                {"min_score": 90, "max_score": 100, "description": "热点话题，情绪共鸣强，极易传播"},
                {"min_score": 80, "max_score": 89, "description": "话题性强，有分享价值"},
                {"min_score": 70, "max_score": 79, "description": "有一定话题性，传播潜力一般"},
                {"min_score": 60, "max_score": 69, "description": "话题性弱，传播潜力低"},
                {"min_score": 0, "max_score": 59, "description": "无传播价值"},
            ],
        },
    ],
}
