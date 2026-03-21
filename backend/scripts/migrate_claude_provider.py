"""One-time migration: update AgentConfig records with model_provider='claude' to 'kimi'.

Run once after deploying the agentic-loop-and-skills change:
    uv run python scripts/migrate_claude_provider.py
"""
import asyncio
import os

from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie


async def main() -> None:
    mongodb_url = os.environ.get("MONGODB_URL", "mongodb://localhost:27017")
    mongodb_db = os.environ.get("MONGODB_DB", "app")

    client = AsyncIOMotorClient(mongodb_url)
    db = client[mongodb_db]

    from app.models.agent_config import AgentConfig
    await init_beanie(database=db, document_models=[AgentConfig])

    result = await AgentConfig.find(AgentConfig.model_provider == "claude").update(
        {"$set": {"model_provider": "kimi"}}
    )
    print(f"Migrated {result.modified_count} AgentConfig records from 'claude' to 'kimi'.")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
