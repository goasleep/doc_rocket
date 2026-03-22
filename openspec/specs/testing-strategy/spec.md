## ADDED Requirements

### Requirement: Test environment setup
The system SHALL maintain all tests runnable without real external services (no real Kimi/Claude/OpenAI API calls, no real Redis required); test isolation SHALL use fakeredis and mocked LLM clients.

Required test dependencies (add to pyproject.toml dev group):
- `fakeredis` — pure-Python Redis mock, replaces real Redis in tests
- `pytest-mock` — `mocker` fixture for easy patching
- `respx` — mock httpx HTTP calls (for FetcherAgent URL fetching)

Test environment variables (separate `.env.test`):
```
MONGODB_URL=mongodb://localhost:27018
MONGODB_DB=test_fastapi_app
REDIS_URL=redis://localhost:6379/1   # different DB index from dev
SECRET_KEY=test-secret-key-for-testing-only
```

#### Scenario: Tests pass without real API keys
- **WHEN** test suite runs with no KIMI_API_KEY / ANTHROPIC_API_KEY set
- **THEN** all tests pass because LLM clients are mocked at the factory level

### Requirement: Test structure
Tests SHALL be organized into three layers matching the system architecture.

```
backend/tests/
  conftest.py                    ← existing: db, client, auth fixtures
  fixtures/
    __init__.py
    content.py                   ← sample Source, Article, Analysis, Draft factories
    agents.py                    ← sample AgentConfig fixtures
    llm.py                       ← mock LLM client factory fixtures
  unit/
    test_encryption.py
    test_llm_factory.py
    agents/
      test_analyzer_agent.py
      test_editor_agent.py
      test_reviewer_agent.py
      test_fetcher_agent.py
  integration/
    api/
      test_sources.py
      test_articles.py
      test_submit.py
      test_analyses.py
      test_agents_config.py
      test_workflows.py
      test_drafts.py
      test_system_config.py
    test_sse.py
  tasks/
    conftest.py                  ← Celery ALWAYS_EAGER + fakeredis fixtures
    test_fetch_task.py
    test_analyze_task.py
    test_workflow_task.py
```

#### Scenario: All test layers runnable independently
- **WHEN** developer runs `uv run pytest tests/unit/` or `uv run pytest tests/integration/`
- **THEN** only that layer executes without needing the other layers' dependencies

### Requirement: LLM client mocking strategy
All tests that exercise Agent logic SHALL mock the LLM client at the `get_llm_client` factory level, returning deterministic structured responses without real API calls.

**Mock fixture pattern** (in `tests/fixtures/llm.py`):

```python
import pytest
from unittest.mock import AsyncMock, patch

MOCK_ANALYSIS_RESPONSE = '''{
  "quality_score": 85,
  "quality_breakdown": {"content_depth": 88, "readability": 82, "originality": 85, "virality_potential": 85},
  "hook_type": "痛点型",
  "framework": "PAS",
  "emotional_triggers": ["焦虑", "好奇"],
  "key_phrases": ["这个错误让我损失了50万"],
  "keywords": ["创业", "陷阱"],
  "structure": {"intro": "痛点场景", "body_sections": ["原因分析", "解决方案"], "cta": "资源引导型"},
  "style": {"tone": "犀利直接", "formality": "口语化", "avg_sentence_length": 18},
  "target_audience": "25-35岁创业者"
}'''

MOCK_WRITE_RESPONSE = "# 测试标题\n\n这是一段测试生成的文章内容..."

MOCK_EDITOR_RESPONSE = '''{
  "content": "# 优化后的标题\n\n重写后的段落内容...",
  "title_candidates": ["候选标题A", "候选标题B", "候选标题C"],
  "changed_sections": ["第2段", "第4段"]
}'''

MOCK_REVIEWER_RESPONSE = '''{
  "fact_check_flags": [{"severity": "warning", "description": "第3段数据来源未注明"}],
  "legal_notes": [],
  "format_issues": [{"severity": "info", "description": "建议添加小标题分隔"}]
}'''

@pytest.fixture
def mock_llm_chat():
    """Mock get_llm_client factory — returns an AsyncMock chat method."""
    mock_client = AsyncMock()
    # Default response; individual tests override mock_client.chat.return_value
    mock_client.chat.return_value = MOCK_ANALYSIS_RESPONSE
    with patch("app.core.llm.factory.get_llm_client", return_value=mock_client):
        yield mock_client
```

Usage in tests:
```python
async def test_analyzer_produces_analysis(mock_llm_chat, sample_article):
    mock_llm_chat.chat.return_value = MOCK_ANALYSIS_RESPONSE
    agent = AnalyzerAgent(config=analyzer_config)
    result = await agent.run(sample_article.content)
    assert result.quality_score == 85
    assert result.hook_type == "痛点型"
```

#### Scenario: Mock LLM returns structured analysis
- **WHEN** AnalyzerAgent.run() is called with mock_llm_chat fixture
- **THEN** agent parses MOCK_ANALYSIS_RESPONSE and returns a valid ArticleAnalysis object

#### Scenario: Mock LLM returns editor output with title candidates
- **WHEN** EditorAgent.run() is called with mock_llm_chat returning MOCK_EDITOR_RESPONSE
- **THEN** agent returns output with title_candidates array of length 3

### Requirement: Celery task testing with ALWAYS_EAGER
All Celery task tests SHALL use `CELERY_TASK_ALWAYS_EAGER=True` to execute tasks synchronously in the test process, without a real Redis broker or Celery worker.

**Celery test conftest** (in `tests/tasks/conftest.py`):

```python
import asyncio
import pytest
from app.celery_app import celery_app

@pytest.fixture(scope="session")
def celery_config():
    return {
        "task_always_eager": True,
        "task_eager_propagates": True,  # re-raise exceptions from tasks
    }

@pytest.fixture(autouse=True)
def configure_celery_eager(celery_config):
    celery_app.conf.update(celery_config)
    yield
    celery_app.conf.task_always_eager = False
```

**Handling asyncio.run() inside Celery tasks during tests**:

Celery tasks use `asyncio.run(_async_body())` internally. With ALWAYS_EAGER, the task runs in the test's thread. Since pytest-anyio already manages an event loop, calling `asyncio.run()` from inside a test's async context raises `RuntimeError: This event loop is already running`.

**Solution** — use `nest_asyncio` or restructure tasks to expose a testable async function:

```python
# In task definition (tasks/analyze.py):
async def _analyze_article_async(article_id: str) -> None:
    """Pure async logic — testable directly."""
    article = await Article.find_one(...)
    ...

@celery_app.task(name="analyze_article")
def analyze_article_task(article_id: str) -> None:
    """Celery entry point."""
    asyncio.run(_analyze_article_async(article_id))

# In tests — test the async function directly:
async def test_analyze_task_logic(db, sample_article, mock_llm_chat):
    mock_llm_chat.chat.return_value = MOCK_ANALYSIS_RESPONSE
    await _analyze_article_async(str(sample_article.id))
    analysis = await ArticleAnalysis.find_one(ArticleAnalysis.article_id == sample_article.id)
    assert analysis is not None
    assert analysis.quality_score == 85
```

This pattern keeps the async business logic testable directly, separate from the Celery task wrapper. The Celery wrapper itself only needs a single smoke test.

#### Scenario: analyze_article_async produces ArticleAnalysis
- **WHEN** `_analyze_article_async(article_id)` is called with a raw article and mock LLM
- **THEN** ArticleAnalysis is created in MongoDB and Article.status changes to "analyzed"

#### Scenario: fetch_source_task chains to analyze
- **WHEN** `_fetch_source_async(source_id)` runs with mock FetcherAgent returning 2 articles
- **THEN** 2 Article documents are created and `analyze_article_task.delay()` is called twice

#### Scenario: writing_workflow_task publishes SSE events
- **WHEN** `_writing_workflow_async(run_id)` runs with mock Agents and fakeredis
- **THEN** Redis pub/sub channel `workflow:{run_id}` receives at least: agent_start (×3), agent_output (×3), workflow_paused (×1) events

### Requirement: Redis mocking with fakeredis
Tests that involve Redis (SSE pub/sub, Celery result backend) SHALL use `fakeredis` to avoid requiring a real Redis server.

**fakeredis fixture** (in `tests/fixtures/content.py`):

```python
import pytest
import fakeredis
from unittest.mock import patch

@pytest.fixture
def fake_redis_sync():
    server = fakeredis.FakeServer()
    r = fakeredis.FakeRedis(server=server)
    with patch("app.core.redis_client.sync_redis", r):
        yield r

@pytest.fixture
async def fake_redis_async(fake_redis_sync):
    """Async fakeredis backed by same FakeServer."""
    import fakeredis.aioredis
    r = fakeredis.aioredis.FakeRedis(server=fake_redis_sync.server)
    with patch("app.core.redis_client.async_redis", r):
        yield r
```

#### Scenario: fakeredis captures workflow events
- **WHEN** workflow task publishes events to `workflow:{run_id}` using fake_redis_sync
- **THEN** fake_redis_async subscription in the SSE test receives the same events

### Requirement: SSE endpoint testing
The SSE endpoint SHALL be testable using httpx streaming; tests SHALL verify correct event sequence by publishing mock events to fakeredis and reading the SSE stream.

**SSE test pattern**:

```python
async def test_sse_stream_receives_events(
    client: AsyncClient,
    superuser_token_headers: dict,
    fake_redis_async,
    sample_workflow_run,
):
    collected_events = []

    # Start SSE stream in background
    async def consume_sse():
        async with client.stream(
            "GET",
            f"/api/v1/workflows/{sample_workflow_run.id}/stream",
            headers=superuser_token_headers,
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    collected_events.append(json.loads(line[5:].strip()))
                    if len(collected_events) >= 2:
                        break  # stop after receiving expected events

    sse_task = asyncio.create_task(consume_sse())

    # Publish test events to fakeredis
    await asyncio.sleep(0.1)
    await fake_redis_async.publish(
        f"workflow:{sample_workflow_run.id}",
        json.dumps({"type": "agent_start", "agent": "Writer", "message": "开始..."})
    )
    await fake_redis_async.publish(
        f"workflow:{sample_workflow_run.id}",
        json.dumps({"type": "workflow_paused", "draft_id": "xxx"})
    )

    await asyncio.wait_for(sse_task, timeout=5.0)

    assert collected_events[0]["type"] == "agent_start"
    assert collected_events[1]["type"] == "workflow_paused"
```

#### Scenario: SSE stream delivers events in order
- **WHEN** fakeredis publishes agent_start then workflow_paused events
- **THEN** SSE endpoint streams them to client in the same order

#### Scenario: SSE stream sends keepalive
- **WHEN** no events are published for 10 seconds
- **THEN** SSE stream sends at least one ": keepalive" comment line

### Requirement: FetcherAgent HTTP mocking
FetcherAgent uses httpx to fetch URLs; tests SHALL mock HTTP calls using `respx` to avoid real network requests.

**respx mock pattern**:

```python
import respx
import httpx

@respx.mock
async def test_fetcher_api_source(mock_llm_chat, sample_api_source):
    respx.get(sample_api_source.url).mock(
        return_value=httpx.Response(200, json={
            "data": {
                "items": [
                    {"title": "Test Article", "body": "Content here", "link": "https://example.com/1"}
                ]
            }
        })
    )
    agent = FetcherAgent()
    articles = await agent.fetch_source(sample_api_source)
    assert len(articles) == 1
    assert articles[0].title == "Test Article"

@respx.mock
async def test_fetcher_rss_source(sample_rss_source):
    respx.get(sample_rss_source.url).mock(
        return_value=httpx.Response(200, content=RSS_FEED_FIXTURE_BYTES, headers={"content-type": "application/rss+xml"})
    )
    agent = FetcherAgent()
    articles = await agent.fetch_source(sample_rss_source)
    assert len(articles) >= 1
    assert articles[0].url is not None
```

#### Scenario: FetcherAgent parses API source with api_config
- **WHEN** FetcherAgent runs on an API source with mocked HTTP response
- **THEN** articles are extracted using api_config field mapping

#### Scenario: FetcherAgent parses RSS feed
- **WHEN** FetcherAgent runs on an RSS source with mocked feed response
- **THEN** feedparser extracts entries and maps to Article fields

### Requirement: Integration test fixtures for content models
Tests SHALL have reusable factory fixtures for all new models to avoid boilerplate setup.

**Content fixtures** (in `tests/fixtures/content.py`):

```python
@pytest.fixture
async def sample_source(db) -> AsyncGenerator[Source, None]:
    source = Source(
        name="Test API Source",
        type="api",
        url="https://api.example.com/articles",
        api_config={"items_path": "data.items", "title_field": "title",
                    "content_field": "body", "url_field": "link"},
        fetch_config={"interval_minutes": 60, "max_items_per_fetch": 10},
        is_active=True,
    )
    await source.insert()
    yield source
    await source.delete()

@pytest.fixture
async def sample_article(db) -> AsyncGenerator[Article, None]:
    article = Article(
        title="Test Article",
        content="这是一篇测试文章的内容，用于单元测试和集成测试。" * 10,
        status="raw",
        input_type="manual",
    )
    await article.insert()
    yield article
    await article.delete()

@pytest.fixture
async def analyzed_article(db, sample_article) -> AsyncGenerator[Article, None]:
    analysis = ArticleAnalysis(
        article_id=sample_article.id,
        quality_score=85.0,
        hook_type="痛点型",
        framework="PAS",
        ...
    )
    await analysis.insert()
    sample_article.status = "analyzed"
    await sample_article.save()
    yield sample_article
    await analysis.delete()

@pytest.fixture
async def sample_agent_configs(db) -> AsyncGenerator[list[AgentConfig], None]:
    configs = [
        AgentConfig(name="Writer", role="writer", workflow_order=1, ...),
        AgentConfig(name="Editor", role="editor", workflow_order=2, ...),
        AgentConfig(name="Reviewer", role="reviewer", workflow_order=3, ...),
    ]
    for c in configs:
        await c.insert()
    yield configs
    for c in configs:
        await c.delete()
```

#### Scenario: sample_source fixture creates valid Source document
- **WHEN** sample_source fixture is used in a test
- **THEN** Source document exists in test MongoDB and is cleaned up after test

### Requirement: API route test coverage
Every new API route SHALL have at minimum: a success case test, a 404/not-found test, and an auth-required test.

**Example pattern** (test_sources.py):

```python
async def test_create_source_success(client, superuser_token_headers):
    payload = {"name": "My Feed", "type": "api", "url": "https://...", "api_config": {...}, ...}
    r = await client.post("/api/v1/sources/", json=payload, headers=superuser_token_headers)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "My Feed"

async def test_create_source_unauthenticated(client):
    r = await client.post("/api/v1/sources/", json={...})
    assert r.status_code == 401

async def test_get_source_not_found(client, superuser_token_headers):
    r = await client.get("/api/v1/sources/00000000-0000-0000-0000-000000000000",
                         headers=superuser_token_headers)
    assert r.status_code == 404

async def test_system_config_requires_superuser(client, normal_user_token_headers):
    r = await client.patch("/api/v1/system-config", json={}, headers=normal_user_token_headers)
    assert r.status_code == 403
```

#### Scenario: All routes reject unauthenticated requests
- **WHEN** any new API endpoint is called without Authorization header
- **THEN** response is HTTP 401

#### Scenario: system_config PATCH rejects non-superuser
- **WHEN** regular user calls PATCH /system-config
- **THEN** response is HTTP 403
