"""Skill content caching with TTL support."""
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CachedSkill:
    """Cached skill entry with TTL."""

    name: str
    body: str
    description: str
    cached_at: float = field(default_factory=time.time)
    ttl_seconds: int = 3600  # Default 1 hour TTL

    def is_expired(self) -> bool:
        """Check if the cached entry has expired."""
        return time.time() - self.cached_at > self.ttl_seconds


class SkillCache:
    """In-memory cache for skill content with TTL support.

    Provides caching for skill content to avoid repeated database queries.
    Skills are cached with a configurable TTL and automatically invalidated
    when updates occur.
    """

    def __init__(self, default_ttl_seconds: int = 3600):
        """Initialize the skill cache.

        Args:
            default_ttl_seconds: Default TTL for cached skills (default: 1 hour)
        """
        self._cache: dict[str, CachedSkill] = {}
        self._default_ttl = default_ttl_seconds

    def get(self, name: str) -> CachedSkill | None:
        """Get a cached skill by name.

        Args:
            name: The skill name to retrieve

        Returns:
            The cached skill if found and not expired, None otherwise
        """
        cached = self._cache.get(name)
        if cached is None:
            return None

        if cached.is_expired():
            del self._cache[name]
            return None

        return cached

    def set(
        self,
        name: str,
        body: str,
        description: str = "",
        ttl_seconds: int | None = None,
    ) -> CachedSkill:
        """Cache a skill.

        Args:
            name: The skill name
            body: The skill body content
            description: The skill description
            ttl_seconds: Optional custom TTL (uses default if not specified)

        Returns:
            The cached skill entry
        """
        cached = CachedSkill(
            name=name,
            body=body,
            description=description,
            ttl_seconds=ttl_seconds or self._default_ttl,
        )
        self._cache[name] = cached
        return cached

    def invalidate(self, name: str) -> bool:
        """Invalidate a cached skill.

        Args:
            name: The skill name to invalidate

        Returns:
            True if the skill was in cache and removed, False otherwise
        """
        if name in self._cache:
            del self._cache[name]
            return True
        return False

    def invalidate_all(self) -> None:
        """Clear all cached skills."""
        self._cache.clear()

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dict with cache statistics
        """
        total = len(self._cache)
        expired = sum(1 for c in self._cache.values() if c.is_expired())
        valid = total - expired

        return {
            "total_entries": total,
            "valid_entries": valid,
            "expired_entries": expired,
            "cached_skills": list(self._cache.keys()),
        }

    def cleanup_expired(self) -> int:
        """Remove all expired entries from cache.

        Returns:
            Number of entries removed
        """
        expired_names = [name for name, cached in self._cache.items() if cached.is_expired()]
        for name in expired_names:
            del self._cache[name]
        return len(expired_names)


# Global skill cache instance
_skill_cache: SkillCache | None = None


def get_skill_cache() -> SkillCache:
    """Get the global skill cache instance.

    Returns:
        The global SkillCache instance (creates if needed)
    """
    global _skill_cache
    if _skill_cache is None:
        _skill_cache = SkillCache()
    return _skill_cache


def reset_skill_cache() -> None:
    """Reset the global skill cache (useful for testing)."""
    global _skill_cache
    _skill_cache = None
