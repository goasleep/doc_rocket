"""Seed an approved draft and enable WeChat MP config for smoke testing."""
import asyncio
import uuid
from datetime import datetime, timezone

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings
from app.models import Article, Draft, SystemConfig

# URL used by the frontend smoke test
SMOKE_TEST_URL = "https://www.ruanyifeng.com/blog/2024/03/weekly-issue-292.html"


async def main() -> None:
    client = AsyncIOMotorClient(
        settings.MONGODB_URL, uuidRepresentation="standard"
    )
    db = client[settings.MONGODB_DB]
    await init_beanie(
        database=db,
        document_models=[SystemConfig, Draft, Article],
    )

    # Clean up previous smoke test articles so the analysis polling starts fresh
    smoke_article = await Article.find_one(Article.url == SMOKE_TEST_URL)
    if smoke_article:
        await smoke_article.delete()
        print("Cleaned up previous smoke test article.")

    # Clean up previous smoke draft to avoid duplicates
    existing = await Draft.find_one(Draft.title == "冒烟测试仿写稿件")
    if existing:
        await existing.delete()

    # 1. Enable WeChat MP in system config via Beanie model
    config = await SystemConfig.find_one()
    if not config:
        config = SystemConfig()
    config.wechat_mp.enabled = True
    config.wechat_mp.app_id = "wx_smoke_test_appid"
    config.wechat_mp.app_secret_encrypted = None
    await config.save()
    print("WeChat MP config enabled.")

    # 2. Insert an approved draft
    draft = Draft(
        id=uuid.uuid4(),
        source_article_ids=[],
        workflow_run_id=None,
        title="冒烟测试仿写稿件",
        title_candidates=["候选标题 A", "候选标题 B"],
        content="# 冒烟测试\n\n这是一篇用于全链路冒烟测试的仿写稿件。\n\n- 测试提交\n- 测试分析\n- 测试工作流\n- 测试发布",
        status="approved",
        edit_history=[],
        created_at=datetime.now(timezone.utc),
        cover_image_url=None,
        thumb_media_id=None,
    )
    await draft.insert()
    print(f"Seeded approved draft: {draft.id}")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
