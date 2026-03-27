"""Tests for skill loading and caching."""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.agents.skill_cache import SkillCache, CachedSkill, get_skill_cache, reset_skill_cache


class TestCachedSkill:
    """Test cases for CachedSkill dataclass."""

    def test_creation(self):
        """Test creating a cached skill entry."""
        cached = CachedSkill(
            name="test-skill",
            body="Skill content here",
            description="Test description",
            ttl_seconds=3600,
        )

        assert cached.name == "test-skill"
        assert cached.body == "Skill content here"
        assert cached.description == "Test description"
        assert cached.ttl_seconds == 3600
        assert cached.cached_at > 0

    def test_is_expired_false(self):
        """Test that fresh cache entry is not expired."""
        cached = CachedSkill(
            name="test-skill",
            body="Content",
            description="Test description",
            ttl_seconds=3600,  # 1 hour
        )

        assert not cached.is_expired()

    def test_is_expired_true(self):
        """Test that old cache entry is expired."""
        cached = CachedSkill(
            name="test-skill",
            body="Content",
            description="Test description",
            ttl_seconds=1,  # 1 second
        )

        # Simulate time passing
        cached.cached_at -= 2

        assert cached.is_expired()


class TestSkillCache:
    """Test cases for SkillCache."""

    def test_get_nonexistent(self):
        """Test getting a skill not in cache."""
        cache = SkillCache()

        result = cache.get("nonexistent")

        assert result is None

    def test_set_and_get(self):
        """Test setting and getting a cached skill."""
        cache = SkillCache()

        cache.set("my-skill", "Skill body", "Description")
        result = cache.get("my-skill")

        assert result is not None
        assert result.name == "my-skill"
        assert result.body == "Skill body"
        assert result.description == "Description"

    def test_get_expired(self):
        """Test that expired entries are removed on get."""
        cache = SkillCache()

        cache.set("expiring-skill", "Body", "Desc", ttl_seconds=3600)
        # Manually expire the entry by modifying cached_at
        cache._cache["expiring-skill"].cached_at -= 4000

        # Should be expired
        result = cache.get("expiring-skill")
        assert result is None

    def test_invalidate_existing(self):
        """Test invalidating an existing cached skill."""
        cache = SkillCache()

        cache.set("skill-to-invalidate", "Body", "Desc")
        removed = cache.invalidate("skill-to-invalidate")

        assert removed is True
        assert cache.get("skill-to-invalidate") is None

    def test_invalidate_nonexistent(self):
        """Test invalidating a skill not in cache."""
        cache = SkillCache()

        removed = cache.invalidate("nonexistent")

        assert removed is False

    def test_invalidate_all(self):
        """Test clearing all cached skills."""
        cache = SkillCache()

        cache.set("skill1", "Body1", "Desc1")
        cache.set("skill2", "Body2", "Desc2")

        cache.invalidate_all()

        assert cache.get("skill1") is None
        assert cache.get("skill2") is None

    def test_get_stats(self):
        """Test getting cache statistics."""
        cache = SkillCache()

        cache.set("skill1", "Body1", "Desc1")
        cache.set("skill2", "Body2", "Desc2")

        stats = cache.get_stats()

        assert stats["total_entries"] == 2
        assert stats["valid_entries"] == 2
        assert stats["expired_entries"] == 0
        assert set(stats["cached_skills"]) == {"skill1", "skill2"}

    def test_cleanup_expired(self):
        """Test cleaning up expired entries."""
        cache = SkillCache()

        cache.set("fresh", "Body", "Desc", ttl_seconds=3600)
        cache.set("expired", "Body", "Desc", ttl_seconds=3600)
        # Manually expire the second entry
        cache._cache["expired"].cached_at -= 4000

        removed = cache.cleanup_expired()

        assert removed == 1
        assert cache.get("fresh") is not None
        assert cache.get("expired") is None

    def test_custom_ttl(self):
        """Test custom TTL per skill."""
        cache = SkillCache(default_ttl_seconds=3600)

        cache.set("short-lived", "Body", "Desc", ttl_seconds=1)

        assert cache._cache["short-lived"].ttl_seconds == 1


class TestSkillCacheGlobal:
    """Test cases for global skill cache instance."""

    def setup_method(self):
        """Reset cache before each test."""
        reset_skill_cache()

    def teardown_method(self):
        """Reset cache after each test."""
        reset_skill_cache()

    def test_get_skill_cache_singleton(self):
        """Test that get_skill_cache returns the same instance."""
        cache1 = get_skill_cache()
        cache2 = get_skill_cache()

        assert cache1 is cache2

    def test_global_cache_persists_data(self):
        """Test that global cache persists data across calls."""
        cache = get_skill_cache()
        cache.set("global-skill", "Body", "Desc")

        # Get cache again (should be same instance)
        cache2 = get_skill_cache()
        result = cache2.get("global-skill")

        assert result is not None
        assert result.body == "Body"


class TestSkillCacheAsync:
    """Async test cases for skill cache integration."""

    @pytest.mark.asyncio
    async def test_concurrent_access(self):
        """Test concurrent access to cache."""
        cache = SkillCache()

        async def set_skill(i: int) -> None:
            cache.set(f"skill-{i}", f"Body {i}", f"Desc {i}")

        # Concurrent writes
        await asyncio.gather(*[set_skill(i) for i in range(10)])

        stats = cache.get_stats()
        assert stats["total_entries"] == 10


class TestLoadSkillTool:
    """Test cases for load_skill tool function."""

    @pytest.mark.asyncio
    async def test_load_skill_from_cache(self):
        """Test that load_skill returns cached content when available."""
        from app.core.tools.builtin import load_skill
        from app.core.agents.skill_cache import get_skill_cache

        # Pre-populate cache
        cache = get_skill_cache()
        cache.set("cached-skill", "Cached body content", "Cached desc")

        result = await load_skill("cached-skill")

        assert "Cached body content" in result
        assert "from cache" in result

    @pytest.mark.asyncio
    async def test_load_skill_from_db(self):
        """Test that load_skill fetches from DB and caches when not in cache."""
        import sys
        from app.core.agents.skill_cache import get_skill_cache

        # Create a mock skill object
        mock_skill = MagicMock()
        mock_skill.name = "db-skill"
        mock_skill.body = "DB body content"
        mock_skill.description = "DB description"

        # Create a mock Skill class
        mock_Skill_class = MagicMock()
        mock_Skill_class.find_one = AsyncMock(return_value=mock_skill)
        mock_Skill_class.name = MagicMock()  # For query construction

        # Create mock app.models module
        mock_models = MagicMock()
        mock_models.Skill = mock_Skill_class

        # Patch sys.modules to inject our mock
        original_module = sys.modules.get('app.models')
        sys.modules['app.models'] = mock_models

        try:
            # Import after patching
            from app.core.tools.builtin import load_skill
            result = await load_skill("db-skill")

            assert "DB body content" in result

            # Verify it was cached
            cache = get_skill_cache()
            cached = cache.get("db-skill")
            assert cached is not None
            assert cached.body == "DB body content"
        finally:
            if original_module:
                sys.modules['app.models'] = original_module
            else:
                del sys.modules['app.models']
            # Clean up cache
            cache = get_skill_cache()
            cache.invalidate("db-skill")

    @pytest.mark.asyncio
    async def test_load_skill_not_found(self):
        """Test load_skill with non-existent skill."""
        import sys

        # Create a mock Skill class that returns None for find_one
        mock_Skill_class = MagicMock()
        mock_Skill_class.find_one = AsyncMock(return_value=None)
        mock_Skill_class.find = MagicMock(return_value=AsyncMock(
            to_list=AsyncMock(return_value=[])
        ))
        mock_Skill_class.name = MagicMock()

        # Create mock app.models module
        mock_models = MagicMock()
        mock_models.Skill = mock_Skill_class

        # Patch sys.modules to inject our mock
        original_module = sys.modules.get('app.models')
        sys.modules['app.models'] = mock_models

        try:
            # Import after patching
            from app.core.tools.builtin import load_skill
            result = await load_skill("nonexistent")
            assert "not found" in result.lower()
        finally:
            if original_module:
                sys.modules['app.models'] = original_module
            else:
                del sys.modules['app.models']


class TestSkillCacheInvalidation:
    """Test cases for cache invalidation on skill updates."""

    @pytest.mark.asyncio
    async def test_update_skill_invalidates_cache(self):
        """Test that updating a skill invalidates its cache entry."""
        import uuid
        from datetime import datetime, timezone
        from app.api.routes.skills import update_skill
        from app.core.agents.skill_cache import get_skill_cache

        # Pre-populate cache
        cache = get_skill_cache()
        cache.set("skill-to-update", "Old body", "Old desc")

        mock_skill = AsyncMock()
        mock_skill.name = "skill-to-update"
        mock_skill.id = uuid.uuid4()
        mock_skill.body = "Test body"
        mock_skill.description = "Test description"
        mock_skill.scripts = []
        mock_skill.needs_network = False
        mock_skill.is_active = True
        mock_skill.source = "test"
        mock_skill.imported_from = None
        mock_skill.created_at = datetime.now(timezone.utc)
        mock_skill.updated_at = datetime.now(timezone.utc)

        with patch("app.api.routes.skills._get_or_404", return_value=mock_skill):
            from app.models import SkillUpdate
            await update_skill(
                current_user=AsyncMock(),
                skill_id="test-id",
                body=SkillUpdate(description="New description"),
            )

        # Cache should be invalidated
        assert cache.get("skill-to-update") is None

    @pytest.mark.asyncio
    async def test_delete_skill_invalidates_cache(self):
        """Test that deleting a skill invalidates its cache entry."""
        import uuid
        from datetime import datetime, timezone
        from app.api.routes.skills import delete_skill
        from app.core.agents.skill_cache import get_skill_cache

        # Pre-populate cache
        cache = get_skill_cache()
        cache.set("skill-to-delete", "Body", "Desc")

        mock_skill = AsyncMock()
        mock_skill.name = "skill-to-delete"
        mock_skill.id = uuid.uuid4()
        mock_skill.body = "Test body"
        mock_skill.description = "Test description"
        mock_skill.scripts = []
        mock_skill.needs_network = False
        mock_skill.is_active = True
        mock_skill.source = "test"
        mock_skill.imported_from = None
        mock_skill.created_at = datetime.now(timezone.utc)
        mock_skill.updated_at = datetime.now(timezone.utc)

        with patch("app.api.routes.skills._get_or_404", return_value=mock_skill):
            await delete_skill(
                current_user=AsyncMock(),
                skill_id="test-id",
            )

        # Cache should be invalidated
        assert cache.get("skill-to-delete") is None
