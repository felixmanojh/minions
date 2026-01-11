"""Disk cache for Minions - persist computed data across runs.

Inspired by Aider's tag caching for large codebases.
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

from diskcache import Cache

T = TypeVar("T")

CACHE_VERSION = 1
CACHE_DIR_NAME = f".minions.cache.v{CACHE_VERSION}"


class MinionCache:
    """Persistent disk cache for expensive computations.

    Uses file mtime for cache invalidation.
    """

    def __init__(self, root: Path | str | None = None):
        """Initialize cache in the given root directory.

        Args:
            root: Directory to store cache. Defaults to ~/.minions/cache
        """
        if root is None:
            root = Path.home() / ".minions" / "cache"
        else:
            root = Path(root) / CACHE_DIR_NAME

        root.mkdir(parents=True, exist_ok=True)
        self._cache = Cache(str(root))
        self._root = root

    def get(self, key: str) -> Any | None:
        """Get value from cache."""
        return self._cache.get(key)

    def set(self, key: str, value: Any, expire: float | None = None) -> None:
        """Set value in cache with optional expiration."""
        self._cache.set(key, value, expire=expire)

    def get_or_compute(
        self,
        key: str,
        compute_fn: Callable[[], T],
        mtime: float | None = None,
    ) -> T:
        """Get from cache or compute and store.

        Args:
            key: Cache key
            compute_fn: Function to compute value if not cached
            mtime: File modification time for invalidation

        Returns:
            Cached or computed value
        """
        cached = self._cache.get(key)

        if cached is not None:
            # Check mtime if provided
            if mtime is None:
                # No mtime tracking - check if it's a wrapped result or raw
                if isinstance(cached, dict) and "result" in cached:
                    return cached["result"]
                return cached
            elif isinstance(cached, dict) and cached.get("mtime") == mtime:
                return cached.get("result")

        # Cache miss - compute and store
        result = compute_fn()

        if mtime is not None:
            self._cache.set(key, {"mtime": mtime, "result": result})
        else:
            self._cache.set(key, {"result": result})

        return result

    def get_file_cached(
        self,
        filepath: str | Path,
        compute_fn: Callable[[str], T],
    ) -> T:
        """Get cached result for a file, invalidate if file changed.

        Args:
            filepath: Path to file
            compute_fn: Function to compute value (receives filepath)

        Returns:
            Cached or computed value
        """
        filepath = Path(filepath)
        if not filepath.exists():
            return compute_fn(str(filepath))

        mtime = os.path.getmtime(filepath)
        key = self._file_key(filepath)

        return self.get_or_compute(key, lambda: compute_fn(str(filepath)), mtime)

    def _file_key(self, filepath: Path) -> str:
        """Generate cache key for a file."""
        abs_path = str(filepath.resolve())
        return hashlib.md5(abs_path.encode()).hexdigest()

    def clear(self) -> None:
        """Clear all cached data."""
        self._cache.clear()

    def close(self) -> None:
        """Close the cache."""
        self._cache.close()

    def __enter__(self) -> MinionCache:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


# Global cache instance
_global_cache: MinionCache | None = None


def get_cache(root: Path | str | None = None) -> MinionCache:
    """Get or create the global cache instance."""
    global _global_cache
    if _global_cache is None:
        _global_cache = MinionCache(root)
    return _global_cache


__all__ = ["MinionCache", "get_cache", "CACHE_VERSION"]
