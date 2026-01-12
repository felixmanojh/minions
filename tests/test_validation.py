"""Tests for the Generate → Validate pipeline components."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from llm_gc.config import (
    get_configs,
    get_validator_config,
    MinionConfigs,
    ValidationConfig,
    ModelConfig,
)
from llm_gc.linter import basic_lint, get_error_context, LintResult
from llm_gc.validator import (
    CodeValidator,
    ValidationResult,
    create_retry_prompt,
)
from llm_gc.logging import (
    log_failure,
    log_success,
    get_recent_failures,
    MINIONS_DIR,
    SESSIONS_DIR,
)


# === Config Tests ===

class TestGetConfigs:
    """Tests for get_configs() function."""

    def test_returns_minion_configs(self):
        """get_configs returns MinionConfigs dataclass."""
        configs = get_configs()
        assert isinstance(configs, MinionConfigs)
        assert isinstance(configs.minion, ModelConfig)
        assert isinstance(configs.validation, ValidationConfig)

    def test_minion_has_required_fields(self):
        """Minion config has model, temperature, max_tokens, num_ctx."""
        configs = get_configs()
        assert configs.minion.model
        assert configs.minion.temperature >= 0
        assert configs.minion.max_tokens > 0
        assert configs.minion.num_ctx > 0

    def test_preset_lite_uses_same_validator(self):
        """Lite preset should have validator=None (uses minion)."""
        configs = get_configs(preset="lite")
        assert configs.validator is None

    def test_preset_standard_has_separate_validator(self):
        """Standard preset should have separate validator config."""
        configs = get_configs(preset="standard")
        assert configs.validator is not None
        assert isinstance(configs.validator, ModelConfig)

    def test_validation_config_defaults(self):
        """ValidationConfig has sensible defaults."""
        configs = get_configs()
        assert configs.validation.max_retries >= 0
        assert isinstance(configs.validation.notify_on_fail, bool)


class TestGetValidatorConfig:
    """Tests for get_validator_config() helper."""

    def test_returns_validator_when_set(self):
        """Returns validator config when explicitly set."""
        configs = get_configs(preset="standard")
        validator_cfg = get_validator_config(configs)
        assert validator_cfg.model == configs.validator.model

    def test_returns_minion_when_validator_none(self):
        """Returns minion-based config when validator is None."""
        configs = get_configs(preset="lite")
        validator_cfg = get_validator_config(configs)
        assert validator_cfg.model == configs.minion.model
        # Should have lower temperature for validation
        assert validator_cfg.temperature <= configs.minion.temperature


# === Linter Tests ===

class TestBasicLint:
    """Tests for basic_lint() function."""

    def test_valid_python_returns_none(self):
        """Valid Python code returns None (no errors)."""
        code = "def hello():\n    return 'world'\n"
        result = basic_lint("test.py", code)
        assert result is None

    def test_syntax_error_returns_lint_result(self):
        """Syntax error returns LintResult with error lines."""
        code = "def broken(\n"  # Missing closing paren
        result = basic_lint("test.py", code)
        assert result is not None
        assert isinstance(result, LintResult)
        assert result.has_errors
        assert len(result.lines) > 0

    def test_indentation_error(self):
        """Indentation error is caught."""
        code = "def foo():\nreturn 1"  # Missing indent
        result = basic_lint("test.py", code)
        assert result is not None
        assert result.has_errors

    def test_non_python_file_returns_none(self):
        """Non-Python files return None (no check)."""
        code = "not valid python {"
        result = basic_lint("test.txt", code)
        # Without tree-sitter for .txt, should return None
        assert result is None


class TestGetErrorContext:
    """Tests for get_error_context() function."""

    def test_returns_string_with_line_numbers(self):
        """Error context includes line numbers."""
        code = "line1\nline2\nline3\nline4\nline5"
        context = get_error_context("test.py", code, [3])
        assert "3" in context
        assert "line3" in context

    def test_multiple_error_lines(self):
        """Multiple error lines are all included."""
        code = "\n".join(f"line{i}" for i in range(1, 11))
        context = get_error_context("test.py", code, [2, 5, 8])
        assert "line2" in context
        assert "line5" in context
        assert "line8" in context


# === Validator Tests ===

class TestValidationResult:
    """Tests for ValidationResult model."""

    def test_passed_result(self):
        """Passed result has passed=True."""
        result = ValidationResult(passed=True)
        assert result.passed
        assert result.reason is None

    def test_failed_result_with_reason(self):
        """Failed result has passed=False and reason."""
        result = ValidationResult(passed=False, reason="Syntax error on line 5")
        assert not result.passed
        assert "Syntax error" in result.reason


class TestCodeValidatorParsing:
    """Tests for CodeValidator response parsing."""

    @pytest.fixture
    def validator(self):
        """Create validator with mock client."""
        mock_client = MagicMock()
        mock_config = ModelConfig(
            model="test-model",
            temperature=0.1,
            max_tokens=400,
            num_ctx=8192,
        )
        return CodeValidator(client=mock_client, config=mock_config)

    def test_parse_pass_response(self, validator):
        """PASS response is parsed correctly."""
        result = validator._parse_response("PASS")
        assert result.passed

    def test_parse_pass_with_extra_text(self, validator):
        """PASS with extra text still passes."""
        result = validator._parse_response("PASS\nAll checks succeeded.")
        assert result.passed

    def test_parse_fail_with_reason(self, validator):
        """FAIL: reason is parsed correctly."""
        result = validator._parse_response("FAIL: Syntax error on line 42")
        assert not result.passed
        assert "Syntax error" in result.reason

    def test_parse_fail_dash_format(self, validator):
        """FAIL - reason format is parsed correctly."""
        result = validator._parse_response("FAIL - Missing docstring")
        assert not result.passed
        assert "Missing docstring" in result.reason

    def test_parse_invalid_response(self, validator):
        """Invalid response is treated as failure."""
        result = validator._parse_response("I think the code looks good")
        assert not result.passed
        assert "Invalid validator response" in result.reason


class TestCreateRetryPrompt:
    """Tests for create_retry_prompt() function."""

    def test_includes_original_code(self):
        """Retry prompt includes original code."""
        prompt = create_retry_prompt(
            original="def foo(): pass",
            generated="def foo() pass",  # Missing colon
            error="Syntax error",
        )
        assert "def foo(): pass" in prompt

    def test_includes_error_message(self):
        """Retry prompt includes error message."""
        prompt = create_retry_prompt(
            original="x = 1",
            generated="x = ",
            error="SyntaxError: invalid syntax",
        )
        assert "SyntaxError" in prompt

    def test_includes_generated_code(self):
        """Retry prompt includes the broken generated code."""
        prompt = create_retry_prompt(
            original="x = 1",
            generated="x = broken",
            error="Error",
        )
        assert "x = broken" in prompt


# === Logging Tests ===

class TestLogging:
    """Tests for failure/success logging."""

    def test_log_failure_creates_files(self, tmp_path):
        """log_failure creates session file and appends to log."""
        with patch.object(Path, 'home', return_value=tmp_path):
            # Reimport to use patched home
            import importlib
            import llm_gc.logging as logging_module
            importlib.reload(logging_module)

            session_path = logging_module.log_failure(
                file="test.py",
                reason="Test failure",
                task="docstrings",
            )

            assert session_path.exists()
            assert session_path.suffix == ".json"

    def test_log_success_creates_session(self, tmp_path):
        """log_success creates session file."""
        with patch.object(Path, 'home', return_value=tmp_path):
            import importlib
            import llm_gc.logging as logging_module
            importlib.reload(logging_module)

            session_path = logging_module.log_success(
                file="test.py",
                task="types",
            )

            assert session_path.exists()

    def test_session_contains_required_fields(self, tmp_path):
        """Session file contains expected fields."""
        import json
        with patch.object(Path, 'home', return_value=tmp_path):
            import importlib
            import llm_gc.logging as logging_module
            importlib.reload(logging_module)

            session_path = logging_module.log_failure(
                file="myfile.py",
                reason="broken",
                task="headers",
                original="# original",
                generated="# broken",
                attempts=2,
            )

            data = json.loads(session_path.read_text())
            assert data["file"] == "myfile.py"
            assert data["status"] == "failed"
            assert data["reason"] == "broken"
            assert data["task"] == "headers"
            assert data["attempts"] == 2
