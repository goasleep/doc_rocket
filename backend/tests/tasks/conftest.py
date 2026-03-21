"""Conftest for Celery task tests."""
import pytest

from tests.fixtures.content import (  # noqa: F401
    sample_source,
    sample_article,
    analyzed_article,
    sample_agent_configs,
)


@pytest.fixture(scope="function")
def celery_always_eager():
    """Make Celery tasks execute synchronously in tests."""
    from app.celery_app import celery_app
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    yield
    celery_app.conf.task_always_eager = False
