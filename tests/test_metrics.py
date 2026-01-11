"""Tests for the metrics module."""

from __future__ import annotations

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from llm_gc.metrics import (
    THRESHOLDS,
    MetricEvent,
    clear_metrics,
    get_health_indicator,
    get_metrics,
    get_performance_by_model,
    get_success_rate_by_role,
    get_summary,
    log_metric,
)


@pytest.fixture
def temp_metrics_file(tmp_path):
    """Use a temporary metrics file for testing."""
    metrics_file = tmp_path / "metrics.json"
    with patch("llm_gc.metrics.METRICS_FILE", metrics_file):
        yield metrics_file


class TestMetricEvent:
    """Test MetricEvent dataclass."""

    def test_default_values(self):
        """Test that MetricEvent has sensible defaults."""
        event = MetricEvent()
        assert event.task_type == "chat"
        assert event.success is True
        assert event.retries == 0
        assert event.duration_ms == 0
        assert event.id is not None
        assert event.timestamp is not None

    def test_custom_values(self):
        """Test MetricEvent with custom values."""
        event = MetricEvent(
            task_type="patch",
            task_description="Fix the bug",
            duration_ms=1500,
            model="qwen2.5-coder:7b",
            role="implementer",
            success=True,
            judge_score=0.85,
        )
        assert event.task_type == "patch"
        assert event.task_description == "Fix the bug"
        assert event.duration_ms == 1500
        assert event.model == "qwen2.5-coder:7b"
        assert event.role == "implementer"
        assert event.judge_score == 0.85

    def test_all_task_types(self):
        """Test all valid task types."""
        for task_type in ["chat", "patch", "swarm", "judge", "test", "apply"]:
            event = MetricEvent(task_type=task_type)
            assert event.task_type == task_type


class TestLogMetric:
    """Test log_metric function."""

    def test_log_metric_creates_file(self, temp_metrics_file):
        """Test that log_metric creates the metrics file."""
        log_metric(task_type="chat", duration_ms=100)
        assert temp_metrics_file.exists()

    def test_log_metric_appends_event(self, temp_metrics_file):
        """Test that log_metric appends events."""
        log_metric(task_type="chat", duration_ms=100)
        log_metric(task_type="patch", duration_ms=200)

        events = json.loads(temp_metrics_file.read_text())
        assert len(events) == 2
        assert events[0]["task_type"] == "chat"
        assert events[1]["task_type"] == "patch"

    def test_log_metric_truncates_description(self, temp_metrics_file):
        """Test that long descriptions are truncated."""
        long_desc = "x" * 300
        log_metric(task_description=long_desc)

        events = json.loads(temp_metrics_file.read_text())
        assert len(events[0]["task_description"]) == 200

    def test_log_metric_truncates_error(self, temp_metrics_file):
        """Test that long errors are truncated."""
        long_error = "e" * 600
        log_metric(error=long_error)

        events = json.loads(temp_metrics_file.read_text())
        assert len(events[0]["error"]) == 500


class TestGetMetrics:
    """Test get_metrics function."""

    def test_get_metrics_empty(self, temp_metrics_file):
        """Test get_metrics with no data."""
        events = get_metrics()
        assert events == []

    def test_get_metrics_returns_events(self, temp_metrics_file):
        """Test get_metrics returns logged events."""
        log_metric(task_type="chat", duration_ms=100)
        log_metric(task_type="patch", duration_ms=200)

        events = get_metrics()
        assert len(events) == 2

    def test_get_metrics_newest_first(self, temp_metrics_file):
        """Test that events are returned newest first."""
        log_metric(task_description="first")
        log_metric(task_description="second")

        events = get_metrics()
        assert events[0]["task_description"] == "second"
        assert events[1]["task_description"] == "first"

    def test_get_metrics_filter_by_role(self, temp_metrics_file):
        """Test filtering by role."""
        log_metric(role="implementer")
        log_metric(role="reviewer")
        log_metric(role="implementer")

        events = get_metrics(role="implementer")
        assert len(events) == 2
        assert all(e["role"] == "implementer" for e in events)

    def test_get_metrics_filter_by_task_type(self, temp_metrics_file):
        """Test filtering by task type."""
        log_metric(task_type="chat")
        log_metric(task_type="patch")
        log_metric(task_type="chat")

        events = get_metrics(task_type="chat")
        assert len(events) == 2
        assert all(e["task_type"] == "chat" for e in events)

    def test_get_metrics_filter_by_failures(self, temp_metrics_file):
        """Test filtering by failures."""
        log_metric(success=True)
        log_metric(success=False)
        log_metric(success=True)

        events = get_metrics(failures_only=True)
        assert len(events) == 1
        assert events[0]["success"] is False

    def test_get_metrics_limit(self, temp_metrics_file):
        """Test limit parameter."""
        for i in range(10):
            log_metric(task_description=f"task_{i}")

        events = get_metrics(limit=3)
        assert len(events) == 3


class TestGetSummary:
    """Test get_summary function."""

    def test_summary_empty(self, temp_metrics_file):
        """Test summary with no data."""
        summary = get_summary()
        assert summary["total"] == 0
        assert summary["success_rate"] == 0.0
        assert summary["by_role"] == {}

    def test_summary_total_count(self, temp_metrics_file):
        """Test total count in summary."""
        log_metric()
        log_metric()
        log_metric()

        summary = get_summary()
        assert summary["total"] == 3

    def test_summary_success_rate(self, temp_metrics_file):
        """Test success rate calculation."""
        log_metric(success=True)
        log_metric(success=True)
        log_metric(success=False)
        log_metric(success=True)

        summary = get_summary()
        assert summary["success_rate"] == 0.75
        assert summary["success_count"] == 3

    def test_summary_by_role(self, temp_metrics_file):
        """Test role breakdown in summary."""
        log_metric(role="implementer", success=True)
        log_metric(role="implementer", success=True)
        log_metric(role="reviewer", success=False)

        summary = get_summary()
        assert summary["by_role"]["implementer"]["total"] == 2
        assert summary["by_role"]["implementer"]["success_rate"] == 1.0
        assert summary["by_role"]["reviewer"]["total"] == 1
        assert summary["by_role"]["reviewer"]["success_rate"] == 0.0

    def test_summary_avg_duration(self, temp_metrics_file):
        """Test average duration calculation."""
        log_metric(duration_ms=100)
        log_metric(duration_ms=200)
        log_metric(duration_ms=300)

        summary = get_summary()
        assert summary["avg_duration_ms"] == 200

    def test_summary_by_model(self, temp_metrics_file):
        """Test model breakdown in summary."""
        log_metric(model="qwen:7b", duration_ms=100)
        log_metric(model="qwen:7b", duration_ms=200)
        log_metric(model="llama:7b", duration_ms=300)

        summary = get_summary()
        assert summary["by_model"]["qwen:7b"]["total"] == 2
        assert summary["by_model"]["qwen:7b"]["avg_duration_ms"] == 150
        assert summary["by_model"]["llama:7b"]["total"] == 1

    def test_summary_retry_rate(self, temp_metrics_file):
        """Test retry rate calculation."""
        log_metric(retries=0)
        log_metric(retries=1)
        log_metric(retries=0)
        log_metric(retries=2)

        summary = get_summary()
        assert summary["retry_rate"] == 0.5

    def test_summary_judge_score(self, temp_metrics_file):
        """Test average judge score."""
        log_metric(judge_score=0.8)
        log_metric(judge_score=0.6)
        log_metric(judge_score=None)  # Should be ignored

        summary = get_summary()
        assert summary["avg_judge_score"] == 0.7

    def test_summary_patch_success_rate(self, temp_metrics_file):
        """Test patch success rate."""
        log_metric(patch_applied=True)
        log_metric(patch_applied=True)
        log_metric(patch_applied=False)
        log_metric(patch_applied=None)  # Should be ignored

        summary = get_summary()
        assert summary["patch_success_rate"] == pytest.approx(0.666, rel=0.01)

    def test_summary_test_pass_rate(self, temp_metrics_file):
        """Test test pass rate."""
        log_metric(tests_passed=True)
        log_metric(tests_passed=False)
        log_metric(tests_passed=None)  # Should be ignored

        summary = get_summary()
        assert summary["test_pass_rate"] == 0.5


class TestGetHealthIndicator:
    """Test get_health_indicator function."""

    def test_success_rate_good(self):
        """Test success rate good threshold."""
        assert get_health_indicator("success_rate", 0.95) == "good"

    def test_success_rate_okay(self):
        """Test success rate okay threshold."""
        assert get_health_indicator("success_rate", 0.80) == "okay"

    def test_success_rate_bad(self):
        """Test success rate bad threshold."""
        assert get_health_indicator("success_rate", 0.50) == "bad"

    def test_duration_good(self):
        """Test duration good threshold (lower is better)."""
        assert get_health_indicator("avg_duration_ms", 1000) == "good"

    def test_duration_okay(self):
        """Test duration okay threshold."""
        assert get_health_indicator("avg_duration_ms", 3000) == "okay"

    def test_duration_bad(self):
        """Test duration bad threshold."""
        assert get_health_indicator("avg_duration_ms", 10000) == "bad"

    def test_retry_rate_good(self):
        """Test retry rate good threshold (lower is better)."""
        assert get_health_indicator("retry_rate", 0.05) == "good"

    def test_retry_rate_bad(self):
        """Test retry rate bad threshold."""
        assert get_health_indicator("retry_rate", 0.30) == "bad"

    def test_none_value(self):
        """Test handling of None value."""
        assert get_health_indicator("success_rate", None) == "unknown"

    def test_unknown_metric(self):
        """Test handling of unknown metric."""
        assert get_health_indicator("unknown_metric", 0.5) == "unknown"


class TestHelperFunctions:
    """Test helper functions."""

    def test_get_performance_by_model(self, temp_metrics_file):
        """Test get_performance_by_model function."""
        log_metric(model="qwen:7b", duration_ms=100)
        log_metric(model="llama:7b", duration_ms=200)

        perf = get_performance_by_model()
        assert "qwen:7b" in perf
        assert "llama:7b" in perf

    def test_get_success_rate_by_role(self, temp_metrics_file):
        """Test get_success_rate_by_role function."""
        log_metric(role="implementer", success=True)
        log_metric(role="reviewer", success=False)

        rates = get_success_rate_by_role()
        assert rates["implementer"] == 1.0
        assert rates["reviewer"] == 0.0

    def test_clear_metrics(self, temp_metrics_file):
        """Test clear_metrics function."""
        log_metric()
        assert temp_metrics_file.exists()

        clear_metrics()
        assert not temp_metrics_file.exists()


class TestThresholds:
    """Test threshold constants."""

    def test_all_metrics_have_thresholds(self):
        """Test that all expected metrics have thresholds defined."""
        expected = [
            "success_rate",
            "avg_duration_ms",
            "retry_rate",
            "avg_judge_score",
            "patch_success_rate",
            "test_pass_rate",
        ]
        for metric in expected:
            assert metric in THRESHOLDS
            assert "good" in THRESHOLDS[metric]
            assert "okay" in THRESHOLDS[metric]
