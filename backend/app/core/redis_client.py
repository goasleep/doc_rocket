"""Redis client instances for both async (FastAPI SSE) and sync (Celery worker) usage."""
import json
from typing import AsyncGenerator

import redis
import redis.asyncio as aioredis

from app.core.config import settings

# Async client — used in FastAPI endpoints (SSE subscriptions)
async_redis: aioredis.Redis = aioredis.from_url(  # type: ignore[assignment]
    settings.REDIS_URL,
    decode_responses=True,
)

# Sync client — used in Celery workers (publish events)
sync_redis: redis.Redis = redis.from_url(  # type: ignore[assignment]
    settings.REDIS_URL,
    decode_responses=True,
)


def publish_workflow_event(run_id: str, event_type: str, data: dict) -> None:  # type: ignore[type-arg]
    """Publish a workflow event to Redis pub/sub (sync, for Celery workers)."""
    payload = json.dumps({"type": event_type, **data})
    sync_redis.publish(f"workflow:{run_id}", payload)


async def subscribe_workflow_events(run_id: str) -> aioredis.client.PubSub:
    """Subscribe to a workflow's Redis pub/sub channel (async, for FastAPI SSE)."""
    pubsub = async_redis.pubsub()
    await pubsub.subscribe(f"workflow:{run_id}")
    return pubsub


async def workflow_event_stream(run_id: str) -> AsyncGenerator[str, None]:
    """Async generator yielding SSE-formatted lines from the Redis pub/sub channel."""
    import asyncio

    pubsub = await subscribe_workflow_events(run_id)
    keepalive_interval = 10  # seconds
    try:
        while True:
            try:
                message = await asyncio.wait_for(pubsub.get_message(ignore_subscribe_messages=True), timeout=keepalive_interval)
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"
                continue

            if message is None:
                await asyncio.sleep(0.1)
                continue

            data = message.get("data", "")
            if isinstance(data, str):
                yield f"data: {data}\n\n"

                # Close stream when workflow is terminal
                try:
                    parsed = json.loads(data)
                    if parsed.get("type") in ("workflow_paused", "workflow_done", "workflow_failed"):
                        break
                except (json.JSONDecodeError, AttributeError):
                    pass

    finally:
        await pubsub.unsubscribe(f"workflow:{run_id}")
        await pubsub.close()
