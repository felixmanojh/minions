"""Tests for bootstrap.py - Ollama health checks."""

from unittest.mock import MagicMock, patch

import pytest

from llm_gc.bootstrap import (
    check_models_available,
    check_ollama_running,
    ensure_ollama,
    get_available_models,
    wait_for_ollama,
)

# ─────────────────────────────────────────────────────────────
# Ollama Health Check Tests
# ─────────────────────────────────────────────────────────────


class TestCheckOllamaRunning:
    """Test basic Ollama connectivity check."""

    def test_running_returns_true(self):
        """Should return True when Ollama responds 200."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("httpx.get", return_value=mock_response):
            assert check_ollama_running() is True

    def test_not_running_returns_false(self):
        """Should return False on connection error."""
        with patch("httpx.get", side_effect=Exception("Connection refused")):
            assert check_ollama_running() is False

    def test_bad_status_returns_false(self):
        """Should return False on non-200 status."""
        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch("httpx.get", return_value=mock_response):
            assert check_ollama_running() is False


# ─────────────────────────────────────────────────────────────
# Wait for Ollama Tests
# ─────────────────────────────────────────────────────────────


class TestWaitForOllama:
    """Test retry logic for Ollama health checks."""

    def test_immediate_success(self):
        """Should return True immediately if Ollama is running."""
        with patch("llm_gc.bootstrap.check_ollama_running", return_value=True):
            assert wait_for_ollama(retries=3, quiet=True) is True

    def test_retry_then_success(self):
        """Should retry and return True on eventual success."""
        # Fail twice, then succeed
        side_effects = [False, False, True]

        with patch("llm_gc.bootstrap.check_ollama_running", side_effect=side_effects):
            with patch("time.sleep"):
                assert wait_for_ollama(retries=3, backoff=0.1, quiet=True) is True

    def test_all_retries_fail(self):
        """Should return False after exhausting retries."""
        with patch("llm_gc.bootstrap.check_ollama_running", return_value=False):
            with patch("time.sleep"):
                assert wait_for_ollama(retries=2, backoff=0.1, quiet=True) is False

    def test_backoff_doubles(self):
        """Should use exponential backoff."""
        sleep_calls = []

        def track_sleep(duration):
            sleep_calls.append(duration)

        with patch("llm_gc.bootstrap.check_ollama_running", return_value=False):
            with patch("time.sleep", side_effect=track_sleep):
                wait_for_ollama(retries=3, backoff=1.0, quiet=True)

        # Backoff: 1.0, 2.0, 4.0
        assert len(sleep_calls) == 3
        assert sleep_calls[0] == 1.0
        assert sleep_calls[1] == 2.0
        assert sleep_calls[2] == 4.0


# ─────────────────────────────────────────────────────────────
# Get Available Models Tests
# ─────────────────────────────────────────────────────────────


class TestGetAvailableModels:
    """Test model listing from Ollama."""

    def test_returns_model_names(self):
        """Should return list of model names."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "qwen2.5-coder:7b"},
                {"name": "deepseek-coder:6.7b"},
            ]
        }

        with patch("httpx.get", return_value=mock_response):
            models = get_available_models()

        assert models == ["qwen2.5-coder:7b", "deepseek-coder:6.7b"]

    def test_empty_on_error(self):
        """Should return empty list on connection error."""
        with patch("httpx.get", side_effect=Exception("Connection refused")):
            assert get_available_models() == []

    def test_empty_on_no_models(self):
        """Should return empty list when no models."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"models": []}

        with patch("httpx.get", return_value=mock_response):
            assert get_available_models() == []


# ─────────────────────────────────────────────────────────────
# Check Models Available Tests
# ─────────────────────────────────────────────────────────────


class TestCheckModelsAvailable:
    """Test model availability checking."""

    def test_all_available(self):
        """Should categorize all models as available."""
        with patch("llm_gc.bootstrap.get_available_models") as mock:
            mock.return_value = ["qwen2.5-coder:7b", "deepseek-coder:6.7b"]
            available, missing = check_models_available(["qwen2.5-coder:7b"])

        assert available == ["qwen2.5-coder:7b"]
        assert missing == []

    def test_some_missing(self):
        """Should categorize missing models correctly."""
        with patch("llm_gc.bootstrap.get_available_models") as mock:
            mock.return_value = ["qwen2.5-coder:7b"]
            available, missing = check_models_available(
                [
                    "qwen2.5-coder:7b",
                    "nonexistent:7b",
                ]
            )

        assert available == ["qwen2.5-coder:7b"]
        assert missing == ["nonexistent:7b"]

    def test_prefix_match(self):
        """Should match model by prefix (base name)."""
        with patch("llm_gc.bootstrap.get_available_models") as mock:
            mock.return_value = ["qwen2.5-coder:7b-instruct"]
            available, missing = check_models_available(["qwen2.5-coder:7b"])

        # Should match because qwen2.5-coder prefix matches
        assert available == ["qwen2.5-coder:7b"]
        assert missing == []


# ─────────────────────────────────────────────────────────────
# Ensure Ollama Tests
# ─────────────────────────────────────────────────────────────


class TestEnsureOllama:
    """Test the main ensure_ollama function."""

    def test_raises_when_not_running(self):
        """Should raise RuntimeError when Ollama is not running."""
        with patch("llm_gc.bootstrap.wait_for_ollama", return_value=False):
            with pytest.raises(RuntimeError) as exc:
                ensure_ollama()

        assert "Ollama is not running" in str(exc.value)
        assert "ollama serve" in str(exc.value)

    def test_raises_when_models_missing(self):
        """Should raise RuntimeError when required models are missing."""
        with patch("llm_gc.bootstrap.wait_for_ollama", return_value=True):
            with patch("llm_gc.bootstrap.check_models_available") as mock:
                mock.return_value = ([], ["missing:7b"])
                with pytest.raises(RuntimeError) as exc:
                    ensure_ollama(required_models=["missing:7b"])

        assert "Missing models" in str(exc.value)
        assert "ollama pull missing:7b" in str(exc.value)

    def test_success_no_models(self):
        """Should succeed when Ollama is running and no models required."""
        with patch("llm_gc.bootstrap.wait_for_ollama", return_value=True):
            ensure_ollama()  # Should not raise

    def test_success_with_models(self):
        """Should succeed when all required models are available."""
        with patch("llm_gc.bootstrap.wait_for_ollama", return_value=True):
            with patch("llm_gc.bootstrap.check_models_available") as mock:
                mock.return_value = (["qwen2.5-coder:7b"], [])
                ensure_ollama(required_models=["qwen2.5-coder:7b"])  # Should not raise
