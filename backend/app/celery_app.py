import asyncio

from celery import Celery
from celery.signals import worker_process_init

from app.core.config import settings

celery_app = Celery(
    "content_intelligence",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.fetch",
        "app.tasks.analyze",
        "app.tasks.workflow",
        "app.tasks.rewrite",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # celery-redbeat scheduler settings
    redbeat_redis_url=settings.REDIS_URL,
    beat_scheduler="redbeat.RedBeatScheduler",
    # Result expiry
    result_expires=3600,
)

# Per-process persistent event loop — created once per forked worker, reused
# across tasks so Motor's AsyncIOMotorClient stays bound to the correct loop.
_worker_loop: asyncio.AbstractEventLoop | None = None


def get_worker_loop() -> asyncio.AbstractEventLoop:
    """Return the persistent event loop for this worker process.

    Initialises DB on first call so Motor is bound to the correct loop.
    """
    global _worker_loop
    if _worker_loop is None or _worker_loop.is_closed():
        from app.core.db import init_db

        _worker_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_worker_loop)
        _worker_loop.run_until_complete(init_db())
    return _worker_loop


@worker_process_init.connect
def init_worker_process(**kwargs: object) -> None:
    """Pre-warm the persistent loop in each forked worker process."""
    get_worker_loop()
