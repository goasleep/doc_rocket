from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings
from app.models import (
    AgentConfig,
    Article,
    ArticleAnalysis,
    DEFAULT_RUBRIC_V1,
    Draft,
    ExternalReference,
    Item,
    LLMModelConfig,
    QualityRubric,
    Skill,
    Source,
    SystemConfig,
    TaskNode,
    TaskRun,
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
            QualityRubric,
            ExternalReference,
            Transcript,
            TaskNode,
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

    # Seed default QualityRubric v1 if none exist
    rubric_count = await QualityRubric.count()
    if rubric_count == 0:
        from app.models.quality_rubric import RubricCriterion, RubricDimension

        dimensions = []
        for dim_data in DEFAULT_RUBRIC_V1["dimensions"]:
            criteria = [
                RubricCriterion(**c) for c in dim_data["criteria"]
            ]
            dimensions.append(RubricDimension(
                name=dim_data["name"],
                description=dim_data["description"],
                weight=dim_data["weight"],
                criteria=criteria,
            ))

        default_rubric = QualityRubric(
            version=DEFAULT_RUBRIC_V1["version"],
            name=DEFAULT_RUBRIC_V1["name"],
            description=DEFAULT_RUBRIC_V1["description"],
            dimensions=dimensions,
            is_active=True,
        )
        await default_rubric.insert()

    return client
