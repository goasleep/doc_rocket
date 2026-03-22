"""Content model fixtures for tests."""
import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.models import (
    AgentConfig,
    Article,
    ArticleAnalysis,
    Draft,
    Source,
    SystemConfig,
    WorkflowRun,
)
from app.models.analysis import QualityBreakdown, ArticleStructure, ArticleStyle
from app.models.source import ApiConfig, FetchConfig
from app.models.workflow import WorkflowInput


@pytest.fixture
async def sample_source(db: None) -> Source:
    source = Source(
        name="Test API Source",
        type="api",
        url="https://api.example.com/articles",
        api_config=ApiConfig(
            items_path="data",
            title_field="title",
            content_field="content",
            url_field="url",
        ),
        fetch_config=FetchConfig(interval_minutes=60, max_items_per_fetch=10),
        is_active=True,
    )
    await source.insert()
    return source


@pytest.fixture
async def sample_article(db: None, sample_source: Source) -> Article:
    article = Article(
        source_id=sample_source.id,
        title="爆款文章测试标题",
        content="这是一篇用于测试的文章正文内容，包含足够的文字来进行AI分析。" * 10,
        input_type="fetched",
        status="raw",
    )
    await article.insert()
    return article


@pytest.fixture
async def analyzed_article(db: None, sample_source: Source) -> tuple[Article, ArticleAnalysis]:
    article = Article(
        source_id=sample_source.id,
        title="已分析文章",
        content="这是一篇已完成分析的文章正文内容。" * 10,
        input_type="fetched",
        status="analyzed",
    )
    await article.insert()

    analysis = ArticleAnalysis(
        article_id=article.id,
        quality_score=82.0,
        quality_breakdown=QualityBreakdown(
            content_depth=80,
            readability=85,
            originality=78,
            virality_potential=83,
        ),
        hook_type="问题式",
        framework="AIDA",
        emotional_triggers=["焦虑", "好奇"],
        key_phrases=["爆款内容", "流量密码"],
        keywords=["内容营销", "AI"],
        structure=ArticleStructure(
            intro="开篇提问",
            body_sections=["分析", "方案"],
            cta="立即尝试",
        ),
        style=ArticleStyle(tone="专业", formality="中等", avg_sentence_length=15),
        target_audience="内容创作者",
    )
    await analysis.insert()
    article.status = "analyzed"
    await article.save()

    return article, analysis


@pytest.fixture
async def sample_agent_configs(db: None) -> list[AgentConfig]:
    # Clear any agents seeded by init_db so we have exactly 3 known configs
    await AgentConfig.delete_all()
    agents = [
        AgentConfig(
            name="Writer",
            role="writer",
            responsibilities="负责仿写创作",
            system_prompt="你是一名专业内容创作者，请根据素材进行仿写。",
            model_config_name="test-model",
            workflow_order=0,
            is_active=True,
        ),
        AgentConfig(
            name="Editor",
            role="editor",
            responsibilities="负责去AI味改写",
            system_prompt="你是一名专业编辑，请对文章进行去AI味改写，并提供3个标题候选。",
            model_config_name="test-model",
            workflow_order=1,
            is_active=True,
        ),
        AgentConfig(
            name="Reviewer",
            role="reviewer",
            responsibilities="负责事实核查和格式审核",
            system_prompt="你是一名专业审核员，请对文章进行事实核查和格式审核。",
            model_config_name="test-model",
            workflow_order=2,
            is_active=True,
        ),
    ]
    for agent in agents:
        await agent.insert()
    return agents


@pytest.fixture
async def sample_workflow_run(
    db: None, analyzed_article: tuple[Article, ArticleAnalysis]
):
    article, _ = analyzed_article
    run = WorkflowRun(
        type="writing",
        input=WorkflowInput(article_ids=[article.id]),
        status="pending",
    )
    await run.insert()
    yield run
    # Clean up so status changes don't leak into subsequent tests
    existing = await WorkflowRun.find_one(WorkflowRun.id == run.id)
    if existing:
        await existing.delete()


@pytest.fixture
async def sample_draft(db: None) -> Draft:
    draft = Draft(
        source_article_ids=[uuid.uuid4()],
        title="测试仿写稿件",
        title_candidates=["标题A", "标题B", "标题C"],
        content="# 测试标题\n\n这是一篇测试仿写稿件的内容。",
        status="draft",
    )
    await draft.insert()
    return draft


@pytest.fixture
def fake_redis_sync():
    """Sync fakeredis patch for Celery tasks."""
    try:
        import fakeredis
        server = fakeredis.FakeServer()
        r = fakeredis.FakeRedis(server=server)
        with patch("app.core.redis_client.sync_redis", r):
            yield r
    except ImportError:
        yield MagicMock()


@pytest.fixture
async def fake_redis_async():
    """Async fakeredis patch for FastAPI SSE."""
    try:
        import fakeredis.aioredis
        server = fakeredis.FakeServer()  # type: ignore[attr-defined]
        r = fakeredis.aioredis.FakeRedis(server=server)
        with patch("app.core.redis_client.async_redis", r):
            yield r
    except (ImportError, AttributeError):
        yield MagicMock()
