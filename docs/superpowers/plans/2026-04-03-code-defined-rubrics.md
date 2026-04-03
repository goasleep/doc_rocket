# Code-Defined Quality Rubrics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert QualityRubric from database model to pure code-defined constants, removing all database persistence and CRUD operations.

**Architecture:** 
- `QualityRubric` becomes a Pydantic BaseModel (not Document)
- Default rubric defined as a constant in `quality_rubric.py`
- API routes simplified to read-only endpoints returning the code-defined rubric
- Frontend adjusted to remove create/activate/delete functionality
- ReactAnalyzerAgent updated to use code-defined rubric directly

**Tech Stack:** FastAPI, Beanie ODM (removing QualityRubric from it), Pydantic, React, TypeScript

---

## File Structure

| File | Responsibility |
|------|----------------|
| `backend/app/models/quality_rubric.py` | Pure Pydantic models + DEFAULT_RUBRIC_V1 constant |
| `backend/app/core/db.py` | Remove QualityRubric seeding logic |
| `backend/app/api/routes/rubrics.py` | Simplified read-only API |
| `backend/app/api/main.py` | Keep rubrics router (no changes needed) |
| `backend/app/models/__init__.py` | Update exports |
| `backend/app/core/agents/react_analyzer.py` | Use code-defined rubric instead of DB query |
| `frontend/src/routes/_layout/rubrics.tsx` | Remove CRUD UI, keep display only |
| `frontend/src/client/` | Regenerate client after API changes |

---

## Task 1: Update QualityRubric Model

**Files:**
- Modify: `backend/app/models/quality_rubric.py`

- [ ] **Step 1: Remove Document base class and DB-related fields**

```python
import uuid
from datetime import datetime, timezone

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
    name: str = Field(..., description="维度名称 (content_depth, readability, originality, ai_flavor, virality_potential)")
    description: str = Field(..., description="维度描述")
    weight: float = Field(..., ge=0, le=1, description="权重")
    criteria: list[RubricCriterion] = Field(default_factory=list, description="评分档位")

    def get_matching_criterion(self, score: float) -> RubricCriterion | None:
        """根据分数获取匹配的档位"""
        for criterion in self.criteria:
            if criterion.matches_score(score):
                return criterion
        return None


class QualityRubric(BaseModel):
    """质量评分标准 - 纯代码定义，非数据库模型"""
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    version: str = Field(..., description="版本号 (如 v1, v2)")
    name: str = Field(..., description="标准名称")
    description: str = Field(default="", description="标准描述")
    dimensions: list[RubricDimension] = Field(default_factory=list, description="评分维度")
    is_active: bool = Field(default=True, description="是否激活 (代码定义始终为True)")
    created_at: datetime = Field(default_factory=get_datetime_utc)
    updated_at: datetime = Field(default_factory=get_datetime_utc)

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
    """创建请求 - 保留用于API兼容，但不再实际创建"""
    version: str
    name: str
    description: str = ""
    dimensions: list[RubricDimension]
    is_active: bool = False


class QualityRubricUpdate(BaseModel):
    """更新请求 - 保留用于API兼容，但不再实际更新"""
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
    """列表响应 - 现在只返回一个默认评分标准"""
    data: list[QualityRubricPublic]
    count: int


# 默认评分标准 v1 - 代码定义，唯一数据源
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


def get_default_rubric() -> QualityRubric:
    """获取默认评分标准实例"""
    from app.models.quality_rubric import RubricCriterion, RubricDimension

    dimensions = []
    for dim_data in DEFAULT_RUBRIC_V1["dimensions"]:
        criteria = [RubricCriterion(**c) for c in dim_data["criteria"]]
        dimensions.append(RubricDimension(
            name=dim_data["name"],
            description=dim_data["description"],
            weight=dim_data["weight"],
            criteria=criteria,
        ))

    return QualityRubric(
        id=uuid.UUID("12345678-1234-1234-1234-123456789abc"),  # 固定ID
        version=DEFAULT_RUBRIC_V1["version"],
        name=DEFAULT_RUBRIC_V1["name"],
        description=DEFAULT_RUBRIC_V1["description"],
        dimensions=dimensions,
        is_active=True,
    )
```

- [ ] **Step 2: Verify the model changes**

Run: `cd /home/smith/Project/full-stack-fastapi-template/backend && uv run python -c "from app.models.quality_rubric import get_default_rubric, QualityRubric; r = get_default_rubric(); print(f'Rubric: {r.name}, Dimensions: {len(r.dimensions)}')"`

Expected: `Rubric: 文章质量评分标准 v1, Dimensions: 5`

- [ ] **Step 3: Commit**

```bash
git add backend/app/models/quality_rubric.py
git commit -m "refactor: convert QualityRubric from Document to pure Pydantic model"
```

---

## Task 2: Remove QualityRubric from Database Initialization

**Files:**
- Modify: `backend/app/core/db.py`

- [ ] **Step 1: Remove QualityRubric from imports and init_beanie**

```python
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings
from app.models import (
    AgentConfig,
    Article,
    ArticleAnalysis,
    Draft,
    ExternalReference,
    InsightSnapshot,
    Item,
    LLMModelConfig,
    Skill,
    Source,
    SystemConfig,
    TaskNode,
    TaskRun,
    TokenUsage,
    TokenUsageDaily,
    Tool,
    Transcript,
    User,
    UserCreate,
    WorkflowRun,
)


async def init_db() -> AsyncIOMotorClient:  # type: ignore[type-arg]
    client: AsyncIOMotorClient = AsyncIOMotorClient(settings.MONGODB_URL)  # type: ignore
    await init_beanie(
        database=client[settings.MONGODB_DB],
        document_models=[
            User,
            Item,
            Source,
            Article,
            ArticleAnalysis,
            LLMModelConfig,
            AgentConfig,
            WorkflowRun,
            Draft,
            SystemConfig,
            Skill,
            Tool,
            TaskRun,
            # QualityRubric removed - now code-defined
            ExternalReference,
            Transcript,
            TaskNode,
            TokenUsage,
            TokenUsageDaily,
            InsightSnapshot,
        ],
    )

    # Seed first superuser
    existing = await User.find_one(User.email == settings.FIRST_SUPERUSER)
    if not existing:
        from fastapi_users.db import BeanieUserDatabase
        from app.core.users import UserManager, _password_helper

        user_db: BeanieUserDatabase = BeanieUserDatabase(User)  # type: ignore[type-arg,misc]
        manager = UserManager(user_db, _password_helper)  # type: ignore[arg-type]
        await manager.create(
            UserCreate(
                email=settings.FIRST_SUPERUSER,
                password=settings.FIRST_SUPERUSER_PASSWORD,
                is_superuser=True,
            ),
            safe=False,
        )

    # Initialize SystemConfig singleton
    config = await SystemConfig.find_one()
    if not config:
        config = SystemConfig()
        await config.insert()

    # Seed default AgentConfigs if none exist
    agent_count = await AgentConfig.count()
    if agent_count == 0:
        from app.core.agents.editor import DEFAULT_SYSTEM as EDITOR_DEFAULT
        from app.core.agents.orchestrator import DEFAULT_SYSTEM as ORCHESTRATOR_DEFAULT
        from app.core.agents.reviewer import DEFAULT_SYSTEM as REVIEWER_DEFAULT
        from app.core.agents.writer import DEFAULT_SYSTEM as WRITER_DEFAULT

        defaults = [
            AgentConfig(
                name="Writer",
                role="writer",
                responsibilities="根据参考文章的分析结果撰写初稿，融合多篇文章的风格与结构",
                system_prompt=WRITER_DEFAULT,
                workflow_order=1,
            ),
            AgentConfig(
                name="Editor",
                role="editor",
                responsibilities="对初稿进行润色、去AI味处理，并生成3个标题候选",
                system_prompt=EDITOR_DEFAULT,
                workflow_order=2,
            ),
            AgentConfig(
                name="Reviewer",
                role="reviewer",
                responsibilities="对终稿进行事实核查、法律风险和格式问题审查",
                system_prompt=REVIEWER_DEFAULT,
                workflow_order=3,
            ),
            AgentConfig(
                name="Orchestrator",
                role="orchestrator",
                responsibilities="协调 Writer、Editor、Reviewer 完成内容创作，根据反馈决定是否需要修改",
                system_prompt=ORCHESTRATOR_DEFAULT,
                workflow_order=0,
                max_iterations=10,
            ),
        ]
        for agent in defaults:
            await agent.insert()

    # QualityRubric seeding removed - now code-defined in quality_rubric.py

    # Register redbeat schedule for insight snapshot (daily at 2 AM)
    _register_insight_snapshot_schedule()

    return client


def _register_insight_snapshot_schedule() -> None:
    """Register the daily insight snapshot schedule with redbeat."""
    try:
        from redbeat import RedBeatSchedulerEntry
        from celery.schedules import crontab
        from app.celery_app import celery_app

        entry_name = "insight_snapshot_global"

        # Check if entry already exists
        try:
            key = RedBeatSchedulerEntry.create_key(entry_name, celery_app)
            existing = RedBeatSchedulerEntry.from_key(key, app=celery_app)
            if existing:
                return  # Already registered
        except Exception:
            pass  # Entry doesn't exist, create it

        entry = RedBeatSchedulerEntry(
            name=entry_name,
            task="scheduled_insight_snapshot_task",
            schedule=crontab(hour=2, minute=0),  # Daily at 2:00 AM
            enabled=True,
            app=celery_app,
        )
        entry.save()
    except Exception:
        pass  # Don't fail startup if redbeat isn't available
```

- [ ] **Step 2: Verify syntax**

Run: `cd /home/smith/Project/full-stack-fastapi-template/backend && uv run python -m py_compile app/core/db.py`

Expected: No output (success)

- [ ] **Step 3: Commit**

```bash
git add backend/app/core/db.py
git commit -m "refactor: remove QualityRubric from database initialization"
```

---

## Task 3: Simplify Rubrics API Routes

**Files:**
- Modify: `backend/app/api/routes/rubrics.py`

- [ ] **Step 1: Replace entire file with simplified read-only version**

```python
"""Quality rubric routes - code-defined, read-only."""
from typing import Any

from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser
from app.models.quality_rubric import (
    QualityRubricPublic,
    QualityRubricsPublic,
    get_default_rubric,
)

router = APIRouter(prefix="/rubrics", tags=["rubrics"])

# Singleton instance of the code-defined rubric
_DEFAULT_RUBRIC = get_default_rubric()


@router.get("/", response_model=QualityRubricsPublic)
async def list_rubrics(current_user: CurrentUser) -> Any:
    """List all quality rubrics - returns only the code-defined default rubric."""
    return QualityRubricsPublic(data=[QualityRubricPublic.model_validate(_DEFAULT_RUBRIC)], count=1)


@router.get("/active", response_model=QualityRubricPublic)
async def get_active_rubric(current_user: CurrentUser) -> Any:
    """Get the currently active quality rubric - returns the code-defined default."""
    return QualityRubricPublic.model_validate(_DEFAULT_RUBRIC)


@router.get("/{rubric_id}", response_model=QualityRubricPublic)
async def get_rubric(current_user: CurrentUser, rubric_id: str) -> Any:
    """Get a specific quality rubric - only the default rubric is available."""
    # Only accept the fixed ID of the default rubric
    if rubric_id != str(_DEFAULT_RUBRIC.id):
        raise HTTPException(status_code=404, detail="Rubric not found - only default rubric available")
    return QualityRubricPublic.model_validate(_DEFAULT_RUBRIC)


# Create, Update, Activate, Delete endpoints removed
# Rubrics are now code-defined - modify backend/app/models/quality_rubric.py to change
```

- [ ] **Step 2: Verify syntax**

Run: `cd /home/smith/Project/full-stack-fastapi-template/backend && uv run python -m py_compile app/api/routes/rubrics.py`

Expected: No output (success)

- [ ] **Step 3: Run backend tests to verify API works**

Run: `cd /home/smith/Project/full-stack-fastapi-template/backend && uv run pytest tests/ -k rubric -v 2>&1 | head -50`

Expected: Tests pass or no rubric-specific tests found

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/routes/rubrics.py
git commit -m "refactor: simplify rubrics API to read-only code-defined rubric"
```

---

## Task 4: Update ReactAnalyzerAgent

**Files:**
- Modify: `backend/app/core/agents/react_analyzer.py`

- [ ] **Step 1: Update imports and _get_active_rubric method**

```python
"""ReactAnalyzerAgent — multi-step article analysis with ReAct pattern."""
import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from app.core.agents.base import BaseAgent
from app.core.tools.registry import dispatch_tool
from app.models import (
    AnalysisTraceStep,
    ComparisonReferenceEmbedded,
    QualityScoreDetail,
    ScoreEvidence,
    ToolCallDetail,
)
from app.models.quality_rubric import QualityRubric, get_default_rubric

# Max chars to send to LLM
MAX_CONTENT_CHARS = 12000


class ReactAnalyzerAgent(BaseAgent):
    """React Agent for multi-step article analysis.

    Steps:
    1. Understand: Extract topic, core ideas, audience, type
    2. KB Comparison: Search similar articles in knowledge base
    3. Web Search: Search external similar articles
    4. Multidimensional Analysis: Parallel analysis of dimensions
    5. Scoring: Score each dimension with reasoning
    6. Reflection: Validate and generate final report
    """

    def __init__(self, agent_config: Any | None = None) -> None:
        super().__init__(agent_config)
        self.trace: list[AnalysisTraceStep] = []
        self.step_index = 0
        self.parallel_group = 0

    def _add_trace_step(
        self,
        step_name: str,
        step_type: str,
        input_summary: str,
        output_summary: str,
        tool_calls: list[ToolCallDetail] | None = None,
        duration_ms: int = 0,
        raw_response: str = "",
        parsed_ok: bool = True,
        parallel_group: str | None = None,
        parallel_index: int | None = None,
    ) -> AnalysisTraceStep:
        """Add a trace step and return it."""
        step = AnalysisTraceStep(
            step_index=self.step_index,
            step_name=step_name,
            step_type=step_type,
            input_summary=input_summary[:500],
            output_summary=output_summary[:1000],
            tool_calls=tool_calls or [],
            duration_ms=duration_ms,
            timestamp=datetime.now(timezone.utc),
            raw_response=raw_response[:2000],
            parsed_ok=parsed_ok,
            parallel_group=parallel_group,
            parallel_index=parallel_index,
        )
        self.trace.append(step)
        self.step_index += 1
        return step

    async def _get_llm(self) -> Any:
        """Get LLM client."""
        from app.core.llm.factory import get_llm_client_by_config_name

        config_name = getattr(self.agent_config, "model_config_name", "") if self.agent_config else ""
        if config_name:
            return await get_llm_client_by_config_name(config_name)

        from app.models import LLMModelConfig
        first = await LLMModelConfig.find_one(LLMModelConfig.is_active == True)  # noqa: E712
        if first:
            return await get_llm_client_by_config_name(first.name)

        raise RuntimeError("No LLM model config found.")

    def _get_active_rubric(self) -> QualityRubric:
        """Get the active quality rubric - now code-defined."""
        return get_default_rubric()

    async def _call_llm(
        self,
        messages: list[dict[str, Any]],
        response_format: dict[str, str] | None = None,
        temperature: float = 0.3,
    ) -> tuple[str, bool]:
        """Call LLM and return (content, success)."""
        try:
            llm = await self._get_llm()
            # Some models (e.g., o3-mini, kimi moonshot-v1-32k) only support temperature=1
            # Check if the model requires fixed temperature
            model_name = getattr(llm, '_default_model', '').lower()
            print(f"[DEBUG] LLM model name: {model_name}, original temperature: {temperature}")
            if 'o3' in model_name or 'o1' in model_name or 'moonshot-v1-32k' in model_name:
                temperature = 1.0
                print(f"[DEBUG] Adjusted temperature to 1.0 for model {model_name}")
            print(f"[DEBUG] Calling llm.chat with temperature={temperature}")
            response = await llm.chat(messages, response_format=response_format, temperature=temperature)
            return response.content or "", True
        except Exception as e:
            print(f"[DEBUG] LLM call failed: {e}")
            return f"Error: {e}", False

    async def _step_understand(
        self,
        article_content: str,
        article_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Step 1: Understand the article."""
        t_start = datetime.now(timezone.utc)

        content = article_content[:MAX_CONTENT_CHARS]
        if len(article_content) > MAX_CONTENT_CHARS:
            content += "\n[内容已截断...]"

        system_prompt = """你是一位专业的文章分析专家。请分析以下文章，提取关键信息。
请以JSON格式返回：
{
  "topic": "文章主题",
  "core_ideas": ["核心观点1", "核心观点2"],
  "target_audience": "目标受众描述",
  "article_type": "文章类型 (news/opinion/tutorial/story/review/other)",
  "key_entities": ["关键实体1", "关键实体2"],
  "estimated_read_time": "预估阅读时间",
  "hook_type": "开头钩子类型 (痛点型|好奇型|数字型|故事型|争议型|权威型|其他)",
  "framework": "文章框架 (AIDA|PAS|故事型|清单型|问答型|倒金字塔|其他)",
  "emotional_triggers": ["情绪触发词1", "情绪触发词2", "情绪触发词3"],
  "structure": {
    "intro": "开头/引言部分的主要内容描述",
    "body_sections": ["正文段落1主题", "正文段落2主题", "正文段落3主题"],
    "cta": "结尾/行动号召部分的内容描述"
  },
  "style": {
    "tone": "语气语调 (犀利|温暖|幽默|严肃|客观|口语化|专业|亲切)",
    "formality": "正式程度 (正式|半正式|口语化)",
    "avg_sentence_length": 25
  }
}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"请分析以下文章：\n\n{content}"},
        ]

        raw_response, success = await self._call_llm(messages, response_format={"type": "json_object"})
        t_end = datetime.now(timezone.utc)
        duration_ms = int((t_end - t_start).total_seconds() * 1000)

        result = {}
        if success:
            try:
                result = json.loads(raw_response)
            except json.JSONDecodeError:
                success = False

        self._add_trace_step(
            step_name="理解文章",
            step_type="thought",
            input_summary=f"文章ID: {article_id}, 内容长度: {len(article_content)}",
            output_summary=json.dumps(result, ensure_ascii=False)[:500],
            duration_ms=duration_ms,
            raw_response=raw_response,
            parsed_ok=success,
        )

        return result

    async def _step_kb_comparison(
        self,
        article_content: str,
        article_id: uuid.UUID | None = None,
    ) -> list[dict[str, Any]]:
        """Step 2: Compare with knowledge base articles."""
        t_start = datetime.now(timezone.utc)

        # Check if KB comparison is enabled
        analysis_config = getattr(self.agent_config, "analysis_config", None)
        if analysis_config and not getattr(analysis_config, "enable_kb_comparison", True):
            self._add_trace_step(
                step_name="知识库对比",
                step_type="observation",
                input_summary="KB comparison disabled",
                output_summary="Skipped",
                duration_ms=0,
            )
            return []

        # Call tool
        tool_result = await dispatch_tool(
            "search_similar_articles",
            {"article_content": article_content, "limit": 3},
        )

        t_end = datetime.now(timezone.utc)
        duration_ms = int((t_end - t_start).total_seconds() * 1000)

        results = []
        tool_calls = [ToolCallDetail(
            tool_name="search_similar_articles",
            input_params={"limit": 3},
            output_summary=tool_result[:200],
            success=not tool_result.startswith("Tool"),
        )]

        try:
            results = json.loads(tool_result)
            if not isinstance(results, list):
                results = []
        except json.JSONDecodeError:
            pass

        self._add_trace_step(
            step_name="知识库对比",
            step_type="tool_call",
            input_summary=f"搜索相似文章",
            output_summary=f"找到 {len(results)} 篇相似文章",
            tool_calls=tool_calls,
            duration_ms=duration_ms,
        )

        return results

    async def _step_web_search(
        self,
        article_content: str,
        topic: str,
        article_id: uuid.UUID | None = None,
    ) -> list[dict[str, Any]]:
        """Step 3: Search external similar articles."""
        t_start = datetime.now(timezone.utc)

        # Check if web search is enabled
        analysis_config = getattr(self.agent_config, "analysis_config", None)
        enable_web_search = getattr(analysis_config, "enable_web_search", True)

        # Also check if Tavily key is configured
        from app.models import SystemConfig
        config = await SystemConfig.find_one()
        has_tavily = config and config.search and config.search.tavily_api_key

        if not enable_web_search or not has_tavily:
            self._add_trace_step(
                step_name="外部搜索",
                step_type="observation",
                input_summary="Web search disabled or not configured",
                output_summary="Skipped",
                duration_ms=0,
            )
            return []

        # Generate search query from topic
        search_query = f"{topic} 文章"

        # Call web_search tool
        tool_result = await dispatch_tool(
            "web_search",
            {"query": search_query, "max_results": 5},
        )

        t_end = datetime.now(timezone.utc)
        duration_ms = int((t_end - t_start).total_seconds() * 1000)

        # Parse and save external references
        external_refs = []
        if not tool_result.startswith("web_search"):
            lines = tool_result.split("\n")
            for line in lines:
                if line.startswith("- ["):
                    # Parse: - [title](url): content
                    match = line.split("](", 1)
                    if len(match) == 2:
                        title_part = match[0][3:]  # Remove "- ["
                        url_content = match[1].split("):", 1)
                        if len(url_content) == 2:
                            url = url_content[0]
                            content_snippet = url_content[1].strip()

                            # Fetch full content
                            fetch_result = await dispatch_tool("fetch_url", {"url": url, "max_chars": 5000})
                            full_content = fetch_result if not fetch_result.startswith("fetch_url") else content_snippet

                            # Save external reference
                            save_result = await dispatch_tool(
                                "save_external_reference",
                                {
                                    "url": url,
                                    "title": title_part,
                                    "content": full_content[:10000],
                                    "content_snippet": content_snippet[:500],
                                    "source": "web_search",
                                    "search_query": search_query,
                                    "referencer_article_id": str(article_id) if article_id else None,
                                },
                            )

                            try:
                                save_data = json.loads(save_result)
                                external_refs.append({
                                    "id": save_data.get("id"),
                                    "url": url,
                                    "title": title_part,
                                    "content_snippet": content_snippet,
                                })
                            except json.JSONDecodeError:
                                pass

        tool_calls = [ToolCallDetail(
            tool_name="web_search",
            input_params={"query": search_query, "max_results": 5},
            output_summary=f"Found {len(external_refs)} external references",
            success=len(external_refs) > 0,
        )]

        self._add_trace_step(
            step_name="外部搜索",
            step_type="tool_call",
            input_summary=f"搜索查询: {search_query}",
            output_summary=f"找到 {len(external_refs)} 篇外部参考",
            tool_calls=tool_calls,
            duration_ms=duration_ms,
        )

        return external_refs

    async def _analyze_dimension(
        self,
        dimension: str,
        dimension_config: dict[str, Any],
        article_content: str,
        kb_articles: list[dict[str, Any]],
        external_refs: list[dict[str, Any]],
        understanding: dict[str, Any],
        parallel_index: int,
    ) -> dict[str, Any]:
        """Analyze a single dimension (for parallel execution)."""
        t_start = datetime.now(timezone.utc)

        content = article_content[:8000]  # Shorter for dimension analysis

        criteria_text = "\n".join([
            f"- {c['min_score']}-{c['max_score']}: {c['description']}"
            for c in dimension_config.get("criteria", [])
        ])

        kb_context = ""
        if kb_articles:
            kb_context = "\n\n知识库参考文章:\n" + "\n".join([
                f"- {a.get('title', '')}: 质量分{a.get('quality_score', 'N/A')}"
                for a in kb_articles[:2]
            ])

        external_context = ""
        if external_refs:
            external_context = "\n\n外部参考文章:\n" + "\n".join([
                f"- {r.get('title', '')}: {r.get('content_snippet', '')[:100]}..."
                for r in external_refs[:2]
            ])

        system_prompt = f"""你是一位专业的文章分析专家，负责评估文章的{dimension_config.get('description', dimension)}维度。

评分标准：
{criteria_text}

请以JSON格式返回分析结果：
{{
  "score": 0-100,
  "reasoning": "详细的评分依据说明",
  "standard_matched": "符合的评分档位描述",
  "evidences": [{{"quote": "原文引用", "context": "上下文说明"}}],
  "improvement_suggestions": ["改进建议1", "改进建议2"]
}}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"请分析以下文章的{dimension_config.get('description', dimension)}维度：\n\n{content}{kb_context}{external_context}"},
        ]

        raw_response, success = await self._call_llm(messages, response_format={"type": "json_object"})
        if success:
            try:
                result = json.loads(raw_response)
            except json.JSONDecodeError:
                result = {
                    "score": 50,
                    "reasoning": f"解析失败: 无效的JSON响应",
                    "standard_matched": "",
                    "evidences": [],
                    "improvement_suggestions": [],
                }
        else:
            result = {
                "score": 50,
                "reasoning": f"分析失败: {raw_response}",
                "standard_matched": "",
                "evidences": [],
                "improvement_suggestions": [],
            }

        t_end = datetime.now(timezone.utc)
        duration_ms = int((t_end - t_start).total_seconds() * 1000)

        # Add trace step with parallel group
        self._add_trace_step(
            step_name=f"维度分析: {dimension}",
            step_type="conclusion",
            input_summary=f"分析维度: {dimension}",
            output_summary=f"得分: {result.get('score', 0)}",
            duration_ms=duration_ms,
            raw_response=raw_response[:1000],
            parsed_ok="score" in result,
            parallel_group="dimension_analysis",
            parallel_index=parallel_index,
        )

        return {
            "dimension": dimension,
            **result,
        }

    async def _step_multidimensional_analysis(
        self,
        article_content: str,
        kb_articles: list[dict[str, Any]],
        external_refs: list[dict[str, Any]],
        understanding: dict[str, Any],
        rubric: QualityRubric,
    ) -> list[dict[str, Any]]:
        """Step 4: Parallel multidimensional analysis."""
        t_start = datetime.now(timezone.utc)

        dimensions = [
            {"name": d.name, "description": d.description, "weight": d.weight, "criteria": [
                {"min_score": c.min_score, "max_score": c.max_score, "description": c.description}
                for c in d.criteria
            ]}
            for d in rubric.dimensions
        ]

        # Check if parallel analysis is enabled
        react_config = getattr(self.agent_config, "react_config", None)
        parallel_enabled = getattr(react_config, "parallel_analysis", True)

        if parallel_enabled:
            # Run all dimensions in parallel
            tasks = [
                self._analyze_dimension(
                    dim["name"],
                    dim,
                    article_content,
                    kb_articles,
                    external_refs,
                    understanding,
                    i,
                )
                for i, dim in enumerate(dimensions)
            ]
            results = await asyncio.gather(*tasks)
        else:
            # Run sequentially
            results = []
            for i, dim in enumerate(dimensions):
                result = await self._analyze_dimension(
                    dim["name"],
                    dim,
                    article_content,
                    kb_articles,
                    external_refs,
                    understanding,
                    i,
                )
                results.append(result)

        t_end = datetime.now(timezone.utc)
        duration_ms = int((t_end - t_start).total_seconds() * 1000)

        return list(results)

    async def _step_scoring_with_reasoning(
        self,
        dimension_results: list[dict[str, Any]],
        rubric: QualityRubric,
    ) -> tuple[list[QualityScoreDetail], dict[str, float]]:
        """Step 5: Calculate final scores with detailed reasoning."""
        t_start = datetime.now(timezone.utc)

        score_details = []
        scores = {}

        for result in dimension_results:
            dim_name = result.get("dimension", "")
            score = float(result.get("score", 0))
            weight = 0.25  # Default weight

            # Get weight from rubric
            dim = rubric.get_dimension(dim_name)
            if dim:
                weight = dim.weight

            weighted_score = score * weight
            scores[dim_name] = score

            # Build evidences
            evidences = []
            for e in result.get("evidences", []):
                if isinstance(e, dict):
                    evidences.append(ScoreEvidence(
                        quote=e.get("quote", ""),
                        context=e.get("context", ""),
                    ))

            score_details.append(QualityScoreDetail(
                dimension=dim_name,
                score=score,
                weight=weight,
                weighted_score=weighted_score,
                reasoning=result.get("reasoning", ""),
                standard_matched=result.get("standard_matched", ""),
                evidences=evidences,
                improvement_suggestions=result.get("improvement_suggestions", []),
            ))

        t_end = datetime.now(timezone.utc)
        duration_ms = int((t_end - t_start).total_seconds() * 1000)

        self._add_trace_step(
            step_name="综合评分",
            step_type="conclusion",
            input_summary=f"维度分析结果: {len(dimension_results)} 个维度",
            output_summary=f"总分: {sum(s.weighted_score for s in score_details):.2f}",
            duration_ms=duration_ms,
        )

        return score_details, scores

    async def _step_reflection(
        self,
        score_details: list[QualityScoreDetail],
        understanding: dict[str, Any],
    ) -> tuple[str, list[str]]:
        """Step 6: Reflection and final summary."""
        t_start = datetime.now(timezone.utc)

        # Check if reflection is enabled
        react_config = getattr(self.agent_config, "react_config", None)
        if react_config and not getattr(react_config, "reflection_enabled", True):
            # Generate simple summary without LLM
            summary = f"文章主题: {understanding.get('topic', '')}。"
            suggestions = []
            for sd in score_details:
                suggestions.extend(sd.improvement_suggestions)

            t_end = datetime.now(timezone.utc)
            duration_ms = int((t_end - t_start).total_seconds() * 1000)

            self._add_trace_step(
                step_name="反思验证",
                step_type="reflection",
                input_summary="Reflection disabled",
                output_summary="Generated simple summary",
                duration_ms=duration_ms,
            )

            return summary, suggestions[:5]

        # Build scores summary
        scores_text = "\n".join([
            f"- {sd.dimension}: {sd.score}/100 (权重{sd.weight}, 加权{sd.weighted_score:.2f})\n  依据: {sd.reasoning[:100]}..."
            for sd in score_details
        ])

        system_prompt = """你是一位专业的文章分析总结专家。请根据各维度评分结果，生成整体分析总结和改进建议。

请以JSON格式返回：
{
  "analysis_summary": "整体分析总结（200字内）",
  "improvement_suggestions": ["最重要的改进建议1", "建议2", "建议3"]
}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"各维度评分结果:\n{scores_text}"},
        ]

        raw_response, success = await self._call_llm(messages, response_format={"type": "json_object"})

        result = {}
        if success:
            try:
                result = json.loads(raw_response)
            except json.JSONDecodeError:
                success = False

        summary = result.get("analysis_summary", "")
        suggestions = result.get("improvement_suggestions", [])

        # If LLM failed, fallback to simple aggregation
        if not summary:
            summary = f"文章主题: {understanding.get('topic', '')}。"
            avg_score = sum(sd.score for sd in score_details) / max(len(score_details), 1)
            summary += f"整体质量评分: {avg_score:.1f}/100。"

        if not suggestions:
            for sd in score_details:
                suggestions.extend(sd.improvement_suggestions)
            suggestions = suggestions[:5]

        t_end = datetime.now(timezone.utc)
        duration_ms = int((t_end - t_start).total_seconds() * 1000)

        self._add_trace_step(
            step_name="反思验证",
            step_type="reflection",
            input_summary=f"维度评分: {len(score_details)} 个",
            output_summary=summary[:200],
            duration_ms=duration_ms,
            raw_response=raw_response[:500],
            parsed_ok=success,
        )

        return summary, suggestions

    async def run(
        self,
        article_content: str,
        article_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Run the complete React analysis workflow.

        Args:
            article_content: The article content to analyze
            article_id: Optional article ID for tracking

        Returns:
            Dict with analysis results matching ArticleAnalysis fields
        """
        t_start_total = datetime.now(timezone.utc)

        # Reset trace
        self.trace = []
        self.step_index = 0

        # Get active rubric (code-defined)
        rubric = self._get_active_rubric()

        # Step 1: Understand
        understanding = await self._step_understand(article_content, article_id)

        # Step 2: KB Comparison
        kb_articles = await self._step_kb_comparison(article_content, article_id)

        # Step 3: Web Search
        topic = understanding.get("topic", "")
        external_refs = await self._step_web_search(article_content, topic, article_id)

        # Step 4: Multidimensional Analysis (parallel)
        dimension_results = await self._step_multidimensional_analysis(
            article_content, kb_articles, external_refs, understanding, rubric
        )

        # Step 5: Scoring
        score_details, scores = await self._step_scoring_with_reasoning(dimension_results, rubric)

        # Step 6: Reflection
        summary, suggestions = await self._step_reflection(score_details, understanding)

        # Calculate final score
        final_score = sum(sd.weighted_score for sd in score_details)

        # Build comparison references
        comparison_refs = []
        for kb in kb_articles[:2]:
            comparison_refs.append(ComparisonReferenceEmbedded(
                source="knowledge_base",
                kb_article_id=uuid.UUID(kb["article_id"]) if kb.get("article_id") else None,
                kb_article_title=kb.get("title"),
                quality_score=kb.get("quality_score"),
                similarity_score=kb.get("relevance_score", 0),
            ))
        for ext in external_refs[:2]:
            comparison_refs.append(ComparisonReferenceEmbedded(
                source="external",
                external_ref_id=uuid.UUID(ext["id"]) if ext.get("id") else None,
                external_url=ext.get("url"),
                external_title=ext.get("title"),
                similarity_score=50,  # Default for external refs
            ))

        t_end_total = datetime.now(timezone.utc)
        total_duration_ms = int((t_end_total - t_start_total).total_seconds() * 1000)

        # Build quality breakdown
        quality_breakdown = {
            "content_depth": scores.get("content_depth", 0),
            "readability": scores.get("readability", 0),
            "originality": scores.get("originality", 0),
            "ai_flavor": scores.get("ai_flavor", 0),
            "virality_potential": scores.get("virality_potential", 0),
        }

        # Extract legacy fields from understanding with defaults
        structure_data = understanding.get("structure", {})
        style_data = understanding.get("style", {})

        return {
            "quality_score": round(final_score, 2),
            "quality_breakdown": quality_breakdown,
            "quality_score_details": [sd.model_dump() for sd in score_details],
            "comparison_references": [cr.model_dump() for cr in comparison_refs],
            "analysis_summary": summary,
            "improvement_suggestions": suggestions,
            "rubric_version": rubric.version,
            "analysis_duration_ms": total_duration_ms,
            "trace": [t.model_dump() for t in self.trace],
            # Legacy fields - now populated from analysis
            "hook_type": understanding.get("hook_type", ""),
            "framework": understanding.get("framework", ""),
            "emotional_triggers": understanding.get("emotional_triggers", []),
            "key_phrases": understanding.get("core_ideas", []),
            "keywords": understanding.get("key_entities", []),
            "structure": {
                "intro": structure_data.get("intro", "") if isinstance(structure_data, dict) else "",
                "body_sections": structure_data.get("body_sections", []) if isinstance(structure_data, dict) else [],
                "cta": structure_data.get("cta", "") if isinstance(structure_data, dict) else "",
            },
            "style": {
                "tone": style_data.get("tone", "") if isinstance(style_data, dict) else "",
                "formality": style_data.get("formality", "") if isinstance(style_data, dict) else "",
                "avg_sentence_length": style_data.get("avg_sentence_length", 0) if isinstance(style_data, dict) else 0,
            },
            "target_audience": understanding.get("target_audience", ""),
            "topic": understanding.get("topic", ""),
            "article_type": understanding.get("article_type", ""),
        }
```

- [ ] **Step 2: Verify syntax**

Run: `cd /home/smith/Project/full-stack-fastapi-template/backend && uv run python -m py_compile app/core/agents/react_analyzer.py`

Expected: No output (success)

- [ ] **Step 3: Commit**

```bash
git add backend/app/core/agents/react_analyzer.py
git commit -m "refactor: update ReactAnalyzerAgent to use code-defined rubric"
```

---

## Task 5: Update Frontend Rubrics Page

**Files:**
- Modify: `frontend/src/routes/_layout/rubrics.tsx`

- [ ] **Step 1: Replace with simplified read-only version**

```tsx
import { useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/router"
import { Check, Scale } from "lucide-react"
import { Suspense } from "react"

import { type RubricDimension, RubricsService } from "@client"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"

export const Route = createFileRoute("/_layout/rubrics")({
  component: RubricsPage,
})

const dimensionLabels: Record<string, string> = {
  content_depth: "内容深度",
  readability: "可读性",
  originality: "原创性",
  ai_flavor: "AI味道",
  virality_potential: "传播潜力",
}

function DimensionCard({ dimension }: { dimension: RubricDimension }) {
  return (
    <Card className="overflow-hidden">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">
            {dimensionLabels[dimension.name] || dimension.name}
          </CardTitle>
          <Badge variant="outline">
            权重 {Math.round(dimension.weight * 100)}%
          </Badge>
        </div>
        <p className="text-sm text-muted-foreground">{dimension.description}</p>
      </CardHeader>
      <CardContent className="pt-0">
        {dimension.criteria && dimension.criteria.length > 0 && (
          <div className="space-y-2">
            <div className="text-xs font-medium text-muted-foreground">
              评分档位
            </div>
            <div className="space-y-1">
              {dimension.criteria.map((criterion, idx) => (
                <div key={idx} className="flex items-center gap-2 text-sm">
                  <div className="flex items-center gap-1 text-xs text-muted-foreground w-20">
                    <span>{criterion.min_score}</span>
                    <span>-</span>
                    <span>{criterion.max_score}</span>
                  </div>
                  <span className="flex-1">{criterion.description}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function RubricsContent() {
  const { data: activeRubric } = useSuspenseQuery({
    queryKey: ["rubrics", "active"],
    queryFn: () => RubricsService.getActiveRubric(),
  })

  if (!activeRubric) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        暂无评分标准
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Active Rubric Info */}
      <Card className="bg-primary/5 border-primary/20">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Scale className="h-5 w-5 text-primary" />
            <CardTitle className="text-base">当前评分标准</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div>
              <div className="font-medium">{activeRubric.name}</div>
              <div className="text-sm text-muted-foreground">
                版本 {activeRubric.version} · {activeRubric.dimensions.length}{" "}
                个维度
              </div>
            </div>
            <Badge className="bg-primary text-primary-foreground">
              <Check className="h-3 w-3 mr-1" />
              启用中
            </Badge>
          </div>
        </CardContent>
      </Card>

      <Separator />

      {/* Dimensions Grid */}
      <div>
        <h2 className="text-lg font-semibold mb-4">评分维度</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {activeRubric.dimensions.map((dimension, idx) => (
            <DimensionCard key={idx} dimension={dimension} />
          ))}
        </div>
      </div>

      {/* Note */}
      <div className="text-sm text-muted-foreground bg-muted p-4 rounded-lg">
        <p>
          评分标准由代码定义，如需修改请更新后端代码中的{" "}
          <code>DEFAULT_RUBRIC_V1</code> 配置。
        </p>
      </div>
    </div>
  )
}

function RubricsPage() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">评分标准</h1>
        <p className="text-muted-foreground">
          文章质量评分的评分标准（Rubrics）- 代码定义
        </p>
      </div>
      <Suspense
        fallback={
          <div className="flex justify-center py-12 text-muted-foreground">
            加载中...
          </div>
        }
      >
        <RubricsContent />
      </Suspense>
    </div>
  )
}
```

- [ ] **Step 2: Verify TypeScript compilation**

Run: `cd /home/smith/Project/full-stack-fastapi-template/frontend && pnpm exec tsc --noEmit --skipLibCheck 2>&1 | head -30`

Expected: No errors related to rubrics.tsx

- [ ] **Step 3: Commit**

```bash
git add frontend/src/routes/_layout/rubrics.tsx
git commit -m "refactor: simplify rubrics page to read-only display"
```

---

## Task 6: Regenerate OpenAPI Client

**Files:**
- Regenerate: `frontend/src/client/`

- [ ] **Step 1: Start backend server to get fresh OpenAPI spec**

Run:
```bash
cd /home/smith/Project/full-stack-fastapi-template
docker compose up -d backend
sleep 5
curl -s http://localhost:8000/api/v1/openapi.json > openapi.json
```

- [ ] **Step 2: Regenerate client**

Run:
```bash
cd /home/smith/Project/full-stack-fastapi-template/frontend
pnpm run generate-client
```

Expected: Client generated successfully

- [ ] **Step 3: Verify rubrics service is simplified**

Check that `RubricsService` in `frontend/src/client/sdk.gen.ts` only has `listRubrics` and `getActiveRubric` methods.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/client/ openapi.json
git commit -m "chore: regenerate OpenAPI client with simplified rubrics API"
```

---

## Task 7: Run Tests and Verify

**Files:**
- Test: Backend and frontend

- [ ] **Step 1: Run backend tests**

Run:
```bash
cd /home/smith/Project/full-stack-fastapi-template/backend
uv run pytest tests/ -v --tb=short 2>&1 | tail -50
```

Expected: All tests pass

- [ ] **Step 2: Run backend linting**

Run:
```bash
cd /home/smith/Project/full-stack-fastapi-template/backend
bash scripts/lint.sh
```

Expected: No lint errors

- [ ] **Step 3: Run frontend build**

Run:
```bash
cd /home/smith/Project/full-stack-fastapi-template/frontend
pnpm run build
```

Expected: Build succeeds

- [ ] **Step 4: Run frontend linting**

Run:
```bash
cd /home/smith/Project/full-stack-fastapi-template/frontend
pnpm run lint
```

Expected: No lint errors

- [ ] **Step 5: Verify deployment**

Run:
```bash
cd /home/smith/Project/full-stack-fastapi-template
docker compose build --no-cache backend
docker compose build --no-cache frontend
docker compose up -d
sleep 10
curl -s http://localhost:8000/api/v1/rubrics/active | head -100
```

Expected: Returns the code-defined rubric JSON

- [ ] **Step 6: Final commit**

```bash
git add .
git commit -m "feat: convert QualityRubric to code-defined, remove database persistence

- QualityRubric now pure Pydantic model (not Document)
- Default rubric defined in code as DEFAULT_RUBRIC_V1 constant
- API simplified to read-only endpoints
- Frontend rubrics page shows code-defined rubric only
- ReactAnalyzerAgent uses get_default_rubric() directly
- Database seeding for rubrics removed"
```

---

## Summary

After completing this plan:

1. **QualityRubric** is a pure Pydantic model defined in code
2. **API** only has read endpoints (`/rubrics/`, `/rubrics/active`, `/rubrics/{id}`)
3. **Frontend** displays the code-defined rubric without CRUD operations
4. **Database** no longer has a `quality_rubrics` collection
5. **Analysis** uses the code-defined rubric directly

To modify rubrics in the future, edit `backend/app/models/quality_rubric.py` and redeploy.
