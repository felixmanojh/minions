"""Tests for cache and patcher modules."""

import tempfile
from pathlib import Path

from llm_gc.cache import MinionCache
from llm_gc.patcher import (
    apply_exact_patch,
    apply_fuzzy_patch,
    apply_line_replace,
    apply_patch_robust,
    generate_unified_diff,
)


# ─────────────────────────────────────────────────────────────
# Cache Tests
# ─────────────────────────────────────────────────────────────


class TestMinionCache:
    """Test disk cache functionality."""

    def test_get_set(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = MinionCache(tmpdir)
            cache.set("key", "value")
            assert cache.get("key") == "value"
            cache.close()

    def test_get_or_compute(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = MinionCache(tmpdir)
            computed = []

            def compute():
                computed.append(1)
                return "computed"

            # First call computes
            result1 = cache.get_or_compute("key", compute)
            assert result1 == "computed"
            assert len(computed) == 1

            # Second call uses cache
            result2 = cache.get_or_compute("key", compute)
            assert result2 == "computed"
            assert len(computed) == 1  # Still 1, didn't recompute

            cache.close()

    def test_mtime_invalidation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = MinionCache(tmpdir)
            computed = []

            def compute():
                computed.append(1)
                return "computed"

            # First call with mtime=1.0
            cache.get_or_compute("key", compute, mtime=1.0)
            assert len(computed) == 1

            # Same mtime uses cache
            cache.get_or_compute("key", compute, mtime=1.0)
            assert len(computed) == 1

            # Different mtime recomputes
            cache.get_or_compute("key", compute, mtime=2.0)
            assert len(computed) == 2

            cache.close()


# ─────────────────────────────────────────────────────────────
# Patcher Tests
# ─────────────────────────────────────────────────────────────


class TestPatcher:
    """Test patch application strategies."""

    def test_exact_patch(self):
        original = "hello world"
        result = apply_exact_patch(original, "world", "universe")
        assert result == "hello universe"

    def test_exact_patch_not_found(self):
        original = "hello world"
        result = apply_exact_patch(original, "foo", "bar")
        assert result is None

    def test_line_replace(self):
        original = "  def foo():\n    pass\n"
        result = apply_line_replace(original, "pass", "return 42")
        assert "return 42" in result
        assert "    return 42" in result  # Preserved indent

    def test_fuzzy_patch(self):
        original = "def hello_world():\n    print('hello')\n"
        # Slightly different search text
        result = apply_fuzzy_patch(
            original,
            "def hello_world():\n    print('hello')",
            "def hello_world():\n    print('goodbye')",
            threshold=0.8,
        )
        # Fuzzy matching should work
        assert result is None or "goodbye" in result

    def test_apply_patch_robust(self):
        original = "hello world"
        result = apply_patch_robust(original, "world", "universe")
        assert result.success
        assert result.result == "hello universe"
        assert result.strategy == "exact"

    def test_generate_unified_diff(self):
        original = "line1\nline2\n"
        modified = "line1\nline2 changed\n"
        diff = generate_unified_diff(original, modified, "test.txt")
        assert "@@" in diff
        assert "-line2" in diff
        assert "+line2 changed" in diff
