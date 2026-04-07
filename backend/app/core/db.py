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


async def init_db(db_name: str | None = None) -> AsyncIOMotorClient:  # type: ignore[type-arg]
    client: AsyncIOMotorClient = AsyncIOMotorClient(settings.MONGODB_URL)  # type: ignore
    database_name = db_name or settings.MONGODB_DB
    await init_beanie(
        database=client[database_name],
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

    # Force-sync code-defined AgentConfig prompts/responsibilities to DB on every startup
    from app.core.agents.prompts import AGENT_PROMPTS

    for role, cfg in AGENT_PROMPTS.items():
        existing = await AgentConfig.find_one(AgentConfig.role == role)
        if existing:
            changed = False
            if existing.system_prompt != cfg["system_prompt"]:
                existing.system_prompt = cfg["system_prompt"]
                changed = True
            if existing.responsibilities != cfg["responsibilities"]:
                existing.responsibilities = cfg["responsibilities"]
                changed = True
            if existing.max_iterations != cfg.get("max_iterations", 5):
                existing.max_iterations = cfg.get("max_iterations", 5)
                changed = True
            if changed:
                await existing.save()
        else:
            await AgentConfig(
                name=role.capitalize(),
                role=role,
                responsibilities=cfg["responsibilities"],
                system_prompt=cfg["system_prompt"],
                max_iterations=cfg.get("max_iterations", 5),
            ).insert()

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
