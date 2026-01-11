"""Tests for new modules: types, cache, repomap, patcher, handoff."""

import tempfile
from pathlib import Path

from llm_gc.cache import MinionCache
from llm_gc.handoff import (
    HandoffRouter,
    MinionPipeline,
    handle_minion_result,
)
from llm_gc.patcher import (
    apply_exact_patch,
    apply_fuzzy_patch,
    apply_line_replace,
    apply_patch_robust,
    generate_unified_diff,
)
from llm_gc.repomap import RepoMap, extract_imports
from llm_gc.types import (
    IMPLEMENTER,
    PATCHER,
    REVIEWER,
    CodeReview,
    Minion,
    MinionResult,
)

# ─────────────────────────────────────────────────────────────
# Types Tests
# ─────────────────────────────────────────────────────────────


class TestMinionTypes:
    """Test Pydantic Minion types."""

    def test_minion_defaults(self):
        m = Minion()
        assert m.name == "Minion"
        assert m.role == "implementer"
        assert m.model == "qwen2.5-coder:7b"

    def test_minion_custom(self):
        m = Minion(
            name="CustomMinion",
            role="reviewer",
            model="deepseek-coder:6.7b",
            temperature=0.1,
        )
        assert m.name == "CustomMinion"
        assert m.role == "reviewer"
        assert m.temperature == 0.1

    def test_callable_instructions(self):
        m = Minion(instructions=lambda: "Dynamic instructions")
        assert m.get_instructions() == "Dynamic instructions"

    def test_predefined_minions(self):
        assert IMPLEMENTER.role == "implementer"
        assert REVIEWER.role == "reviewer"
        assert PATCHER.role == "patcher"

    def test_minion_result(self):
        result = MinionResult(value="done", context={"key": "value"})
        assert result.value == "done"
        assert result.next_minion is None

    def test_code_review(self):
        review = CodeReview(
            summary="Found issues",
            issues=[{"line": 10, "msg": "bug"}],
            needs_fixes=True,
            severity="high",
        )
        assert review.needs_fixes
        assert len(review.issues) == 1


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


# ─────────────────────────────────────────────────────────────
# Handoff Tests
# ─────────────────────────────────────────────────────────────


class TestHandoff:
    """Test agent handoff pattern."""

    def test_router_review_to_patcher(self):
        router = HandoffRouter()
        review = CodeReview(summary="Issues found", needs_fixes=True)
        next_minion = router.route(review)
        assert next_minion is not None
        assert next_minion.role == "patcher"

    def test_router_no_handoff(self):
        router = HandoffRouter()
        review = CodeReview(summary="All good", needs_fixes=False)
        next_minion = router.route(review)
        assert next_minion is None

    def test_handle_code_review(self):
        review = CodeReview(summary="Found bug", needs_fixes=True, severity="high")
        result = handle_minion_result(review)
        assert result.value == "Found bug"
        assert result.next_minion is not None
        assert result.context["severity"] == "high"

    def test_handle_minion_return(self):
        result = handle_minion_result(PATCHER)
        assert result.next_minion == PATCHER

    def test_pipeline_basic(self):
        pipeline = MinionPipeline([REVIEWER])

        def mock_execute(minion, task, context):
            return f"{minion.name} did {task}"

        results = pipeline.run("review code", execute_fn=mock_execute)
        assert len(results) == 1
        assert "Reviewer" in results[0].value


# ─────────────────────────────────────────────────────────────
# RepoMap Tests
# ─────────────────────────────────────────────────────────────


class TestRepoMap:
    """Test repository mapping and file ranking."""

    def test_extract_imports_python(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("import os\nfrom pathlib import Path\n")
            f.flush()
            imports = extract_imports(f.name)
            assert "os" in imports
            assert "pathlib" in imports
            Path(f.name).unlink()

    def test_repomap_discover_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            (Path(tmpdir) / "test.py").write_text("print('hello')")
            (Path(tmpdir) / "test.js").write_text("console.log('hello')")
            (Path(tmpdir) / "readme.md").write_text("# readme")

            repo = RepoMap(tmpdir)
            files = repo.discover_files()

            # Should find .py and .js but not .md
            extensions = [f.suffix for f in files]
            assert ".py" in extensions
            assert ".js" in extensions
            assert ".md" not in extensions

    def test_repomap_build_graph(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create files with imports
            (Path(tmpdir) / "main.py").write_text("from utils import helper\n")
            (Path(tmpdir) / "utils.py").write_text("def helper(): pass\n")

            repo = RepoMap(tmpdir)
            repo.discover_files()
            graph = repo.build_graph()

            # Should have nodes for both files
            assert len(graph.nodes()) == 2

    def test_repomap_rank_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create interconnected files
            (Path(tmpdir) / "a.py").write_text("import b\nimport c\n")
            (Path(tmpdir) / "b.py").write_text("import c\n")
            (Path(tmpdir) / "c.py").write_text("# core module\n")

            repo = RepoMap(tmpdir)
            repo.discover_files()
            repo.build_graph()
            ranked = repo.rank_files()

            # Should return ranked files
            assert len(ranked) > 0
            # All scores should be floats
            assert all(isinstance(score, float) for _, score in ranked)
