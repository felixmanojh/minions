"""Tests for model_router.py - role inference and model selection."""

import os
from unittest.mock import MagicMock, patch

import pytest

from llm_gc.model_router import (
    ROLE_IMPLEMENTER,
    ROLE_PATCHER,
    ROLE_REVIEWER,
    _has_diff_markers,
    _has_file_reference,
    _has_patcher_signals,
    apply_env_override,
    infer_role,
    load_model_config,
    route,
    route_explicit,
    validate_model_available,
    validate_models,
)

# ─────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────


@pytest.fixture
def config():
    """Load the default model config."""
    return load_model_config()


@pytest.fixture
def routing_rules(config):
    """Get routing rules from config."""
    return config.routing


# ─────────────────────────────────────────────────────────────
# Role Inference Tests
# ─────────────────────────────────────────────────────────────


class TestRoleInference:
    """Test role inference from user requests."""

    def test_reviewer_keywords(self, routing_rules):
        """Reviewer keywords should route to reviewer."""
        requests = [
            "Review my auth implementation",
            "Find bugs in this code",
            "Debug the parser issue",
            "Check for security vulnerabilities",
            "Audit the authentication flow",
        ]
        for req in requests:
            assert infer_role(req, routing_rules) == ROLE_REVIEWER, f"Failed for: {req}"

    def test_implementer_keywords(self, routing_rules):
        """Implementer keywords should route to implementer."""
        requests = [
            "Implement a new feature",
            "Create a user service",
            "Generate tests for the API",
            "Refactor the database module",
            "Write documentation for utils",
            "Add logging to all functions",
        ]
        for req in requests:
            assert infer_role(req, routing_rules) == ROLE_IMPLEMENTER, f"Failed for: {req}"

    def test_patcher_keywords(self, routing_rules):
        """Patcher keywords should route to patcher."""
        requests = [
            "Apply this patch",
            "Edit the config file",
            "Insert error handling here",
            "Replace the deprecated function",
        ]
        for req in requests:
            assert infer_role(req, routing_rules) == ROLE_PATCHER, f"Failed for: {req}"

    def test_default_to_implementer(self, routing_rules):
        """Unknown requests should default to implementer."""
        requests = [
            "Do something with this",
            "Help me with my code",
            "I need assistance",
        ]
        for req in requests:
            assert infer_role(req, routing_rules) == ROLE_IMPLEMENTER, f"Failed for: {req}"


# ─────────────────────────────────────────────────────────────
# Fix Keyword Edge Cases
# ─────────────────────────────────────────────────────────────


class TestFixKeyword:
    """Test smart handling of ambiguous 'fix' keyword."""

    def test_fix_bug_goes_to_reviewer(self, routing_rules):
        """fix + bug should route to reviewer."""
        requests = [
            "fix bug in parser",
            "fix the error in worker",
            "fix failing tests",
            "fix broken authentication",
        ]
        for req in requests:
            assert infer_role(req, routing_rules) == ROLE_REVIEWER, f"Failed for: {req}"

    def test_fix_with_patcher_signals_goes_to_patcher(self, routing_rules):
        """fix + patcher signals should route to patcher."""
        requests = [
            "fix with minimal change",
            "fix this one line",
            "fix just this line",
        ]
        for req in requests:
            assert infer_role(req, routing_rules) == ROLE_PATCHER, f"Failed for: {req}"

    def test_fix_with_file_and_this_goes_to_patcher(self, routing_rules):
        """fix + file reference + 'this' should route to patcher."""
        requests = [
            "fix this line in worker.py",
            "fix this in config.ts",
        ]
        for req in requests:
            assert infer_role(req, routing_rules) == ROLE_PATCHER, f"Failed for: {req}"

    def test_fix_implement_goes_to_implementer(self, routing_rules):
        """fix + implement should route to implementer."""
        req = "fix and implement new feature"
        assert infer_role(req, routing_rules) == ROLE_IMPLEMENTER


# ─────────────────────────────────────────────────────────────
# Diff Marker Detection
# ─────────────────────────────────────────────────────────────


class TestDiffMarkers:
    """Test detection of unified diff markers."""

    def test_diff_git_marker(self):
        assert _has_diff_markers("diff --git a/foo.py b/foo.py")
        assert _has_diff_markers("here's the change:\ndiff --git a/x b/x")

    def test_hunk_header_marker(self):
        assert _has_diff_markers("@@ -1,3 +1,4 @@")
        assert _has_diff_markers("patch:\n@@ -10,5 +10,6 @@")

    def test_plus_minus_markers(self):
        assert _has_diff_markers("+++ b/foo.py")
        assert _has_diff_markers("--- a/foo.py")

    def test_no_diff_markers(self):
        assert not _has_diff_markers("review my code")
        assert not _has_diff_markers("fix the bug")

    def test_diff_routes_to_patcher(self, routing_rules):
        """Requests with diff markers should route to patcher."""
        req = "apply this: diff --git a/foo.py b/foo.py"
        assert infer_role(req, routing_rules) == ROLE_PATCHER


# ─────────────────────────────────────────────────────────────
# File Reference Detection
# ─────────────────────────────────────────────────────────────


class TestFileReferences:
    """Test detection of file references."""

    def test_python_files(self):
        assert _has_file_reference("edit worker.py")
        assert _has_file_reference("update src/utils.py")

    def test_typescript_files(self):
        assert _has_file_reference("change index.ts")
        assert _has_file_reference("fix component.tsx")

    def test_other_extensions(self):
        assert _has_file_reference("edit main.go")
        assert _has_file_reference("update lib.rs")
        assert _has_file_reference("fix App.java")

    def test_no_file_reference(self):
        assert not _has_file_reference("review my code")
        assert not _has_file_reference("add logging")


# ─────────────────────────────────────────────────────────────
# Patcher Signals
# ─────────────────────────────────────────────────────────────


class TestPatcherSignals:
    """Test detection of patcher-specific phrases."""

    def test_minimal_change_signals(self):
        assert _has_patcher_signals("make the smallest change")
        assert _has_patcher_signals("with minimal change")

    def test_line_signals(self):
        assert _has_patcher_signals("change this one line")
        assert _has_patcher_signals("fix single line")
        assert _has_patcher_signals("just change this line")

    def test_no_patcher_signals(self):
        assert not _has_patcher_signals("refactor the module")
        assert not _has_patcher_signals("add new feature")


# ─────────────────────────────────────────────────────────────
# Environment Override
# ─────────────────────────────────────────────────────────────


class TestEnvOverride:
    """Test environment variable model overrides."""

    def test_override_prepends_model(self):
        """Override should be first, originals follow."""
        candidates = ["deepseek-coder:6.7b", "qwen2.5-coder:7b"]

        with patch.dict(os.environ, {"MINIONS_REVIEWER_MODEL": "mistral:7b"}):
            result = apply_env_override(ROLE_REVIEWER, candidates)

        assert result == ["mistral:7b", "deepseek-coder:6.7b", "qwen2.5-coder:7b"]

    def test_override_deduplicates(self):
        """If override matches existing, don't duplicate."""
        candidates = ["deepseek-coder:6.7b", "qwen2.5-coder:7b"]

        with patch.dict(os.environ, {"MINIONS_REVIEWER_MODEL": "deepseek-coder:6.7b"}):
            result = apply_env_override(ROLE_REVIEWER, candidates)

        assert result == ["deepseek-coder:6.7b", "qwen2.5-coder:7b"]

    def test_no_override_returns_original(self):
        """Without env var, return original candidates."""
        candidates = ["deepseek-coder:6.7b", "qwen2.5-coder:7b"]

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("MINIONS_REVIEWER_MODEL", None)
            result = apply_env_override(ROLE_REVIEWER, candidates)

        assert result == candidates


# ─────────────────────────────────────────────────────────────
# Route Function
# ─────────────────────────────────────────────────────────────


class TestRoute:
    """Test the main route() function."""

    def test_route_returns_role_and_candidates(self):
        role, candidates = route("Review my code")
        assert role == ROLE_REVIEWER
        assert isinstance(candidates, list)
        assert len(candidates) > 0

    def test_route_explicit_returns_candidates(self):
        candidates = route_explicit(ROLE_PATCHER)
        assert isinstance(candidates, list)
        assert "starcoder2:7b" in candidates[0] or "qwen" in candidates[0]


# ─────────────────────────────────────────────────────────────
# Model Validation
# ─────────────────────────────────────────────────────────────


class TestModelValidation:
    """Test model availability validation."""

    def test_validate_model_with_mock_ollama(self):
        """Test validation with mocked Ollama response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "qwen2.5-coder:7b"},
                {"name": "deepseek-coder:6.7b"},
            ]
        }

        with patch("httpx.get", return_value=mock_response):
            assert validate_model_available("qwen2.5-coder:7b") == True
            assert validate_model_available("nonexistent:7b") == False

    def test_validate_models_splits_available_and_missing(self):
        """Test that validate_models correctly categorizes models."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"models": [{"name": "qwen2.5-coder:7b"}]}

        with patch("httpx.get", return_value=mock_response):
            available, missing = validate_models(["qwen2.5-coder:7b", "missing:7b"])
            assert "qwen2.5-coder:7b" in available
            assert "missing:7b" in missing

    def test_validate_handles_connection_error(self):
        """Validation should return False on connection error."""
        with patch("httpx.get", side_effect=Exception("Connection refused")):
            assert validate_model_available("any:model") == False


# ─────────────────────────────────────────────────────────────
# Config Loading
# ─────────────────────────────────────────────────────────────


class TestConfigLoading:
    """Test model config loading."""

    def test_load_default_config(self):
        cfg = load_model_config()
        assert cfg.preset in ["lite", "medium", "large"]
        assert ROLE_IMPLEMENTER in cfg.roles
        assert ROLE_REVIEWER in cfg.roles
        assert ROLE_PATCHER in cfg.roles

    def test_config_has_routing_rules(self):
        cfg = load_model_config()
        assert len(cfg.routing.patcher_keywords) > 0
        assert len(cfg.routing.reviewer_keywords) > 0
        assert len(cfg.routing.implementer_keywords) > 0

    def test_roles_have_primary_and_fallbacks(self):
        cfg = load_model_config()
        for role_name, role_models in cfg.roles.items():
            assert role_models.primary, f"{role_name} missing primary"
            assert isinstance(role_models.fallbacks, list)
