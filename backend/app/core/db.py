from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings
from app.models import (
    AgentConfig,
    Article,
    ArticleAnalysis,
    Draft,
    Item,
    Source,
    SystemConfig,
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
            AgentConfig,
            WorkflowRun,
            Draft,
            SystemConfig,
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
        from app.core.encryption import encrypt_value

        config = SystemConfig()

        # Import API keys from environment on first start
        if settings.KIMI_API_KEY:
            config.llm_providers.kimi.api_key_encrypted = encrypt_value(settings.KIMI_API_KEY)
        if settings.ANTHROPIC_API_KEY:
            config.llm_providers.claude.api_key_encrypted = encrypt_value(settings.ANTHROPIC_API_KEY)
        if settings.OPENAI_API_KEY:
            config.llm_providers.openai.api_key_encrypted = encrypt_value(settings.OPENAI_API_KEY)

        await config.insert()

    # Seed default AgentConfigs if none exist
    agent_count = await AgentConfig.count()
    if agent_count == 0:
        default_provider = config.writing.default_model_provider
        default_model = config.writing.default_model_id

        defaults = [
            AgentConfig(
                name="Writer",
                role="writer",
                responsibilities="根据参考文章的分析结果撰写初稿，融合多篇文章的风格与结构",
                system_prompt=(
                    "你是一位专业的内容创作者，擅长分析爆款文章的写作框架并进行仿写创作。"
                    "请根据提供的参考素材，创作一篇结构清晰、引人入胜的文章。"
                ),
                model_provider=default_provider,
                model_id=default_model,
                workflow_order=1,
            ),
            AgentConfig(
                name="Editor",
                role="editor",
                responsibilities="对初稿进行润色、去AI味处理，并生成3个标题候选",
                system_prompt=(
                    "你是一位资深编辑，负责优化文章质量。请：\n"
                    "1. 对文章进行去AI味处理，使语言更自然、口语化\n"
                    "2. 优化句式结构，避免重复表达\n"
                    "3. 生成3个吸引人的标题候选\n"
                    '以JSON格式返回：{"content": "...", "title_candidates": ["...", "...", "..."], "changed_sections": [...]}'
                ),
                model_provider=default_provider,
                model_id=default_model,
                workflow_order=2,
            ),
            AgentConfig(
                name="Reviewer",
                role="reviewer",
                responsibilities="对终稿进行事实核查、法律风险和格式问题审查",
                system_prompt=(
                    "你是一位严格的内容审核员。请对文章进行全面审查，以JSON格式返回：\n"
                    '{"fact_check_flags": [{"severity": "warning", "description": "..."}], '
                    '"legal_notes": [{"severity": "info", "description": "..."}], '
                    '"format_issues": [{"severity": "info", "description": "..."}]}'
                ),
                model_provider=default_provider,
                model_id=default_model,
                workflow_order=3,
            ),
        ]
        for agent in defaults:
            await agent.insert()

    return client
