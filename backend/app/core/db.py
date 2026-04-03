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
    PublishHistory,
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
            PublishHistory,
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
