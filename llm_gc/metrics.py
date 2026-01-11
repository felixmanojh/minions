"""Metrics collection and analysis for Minions.

Tracks performance, quality, usage patterns, and efficiency.
"""

from __future__ import annotations

import json
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

# Store metrics in user's home directory
METRICS_FILE = Path.home() / ".minions" / "metrics.json"
MAX_EVENTS = 1000
PRUNE_COUNT = 200

# Thread lock for concurrent writes
_lock = threading.Lock()


@dataclass
class MetricEvent:
    """A single metric event."""

    # Identity
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    session_id: str = ""

    # Task info
    task_type: Literal["chat", "patch", "swarm", "judge", "test", "apply"] = "chat"
    task_description: str = ""

    # Performance
    duration_ms: int = 0
    model: str = ""
    role: str = ""
    tokens_estimated: int = 0

    # Quality
    success: bool = True
    retries: int = 0
    fallback_used: bool = False
    judge_score: float | None = None

    # Outcome
    patch_applied: bool | None = None
    tests_passed: bool | None = None
    error: str | None = None


def _load_metrics() -> list[dict]:
    """Load metrics from file."""
    if not METRICS_FILE.exists():
        return []
    try:
        data = json.loads(METRICS_FILE.read_text())
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save_metrics(events: list[dict]) -> None:
    """Save metrics to file with pruning."""
    # Prune if over limit
    if len(events) > MAX_EVENTS:
        events = events[-MAX_EVENTS + PRUNE_COUNT :]

    METRICS_FILE.parent.mkdir(parents=True, exist_ok=True)
    METRICS_FILE.write_text(json.dumps(events, indent=2))


def log_metric(
    task_type: str = "chat",
    task_description: str = "",
    duration_ms: int = 0,
    model: str = "",
    role: str = "",
    tokens_estimated: int = 0,
    success: bool = True,
    retries: int = 0,
    fallback_used: bool = False,
    judge_score: float | None = None,
    patch_applied: bool | None = None,
    tests_passed: bool | None = None,
    error: str | None = None,
    session_id: str = "",
) -> None:
    """Log a metric event.

    Fire-and-forget function to record task metrics.
    """
    event = MetricEvent(
        task_type=task_type,
        task_description=task_description[:200],  # Truncate long descriptions
        duration_ms=duration_ms,
        model=model,
        role=role,
        tokens_estimated=tokens_estimated,
        success=success,
        retries=retries,
        fallback_used=fallback_used,
        judge_score=judge_score,
        patch_applied=patch_applied,
        tests_passed=tests_passed,
        error=error[:500] if error else None,  # Truncate errors
        session_id=session_id,
    )

    with _lock:
        events = _load_metrics()
        events.append(asdict(event))
        _save_metrics(events)


def get_metrics(
    limit: int = 100,
    role: str | None = None,
    task_type: str | None = None,
    since: str | None = None,
    success_only: bool = False,
    failures_only: bool = False,
) -> list[dict]:
    """Get metrics with optional filtering.

    Args:
        limit: Max events to return
        role: Filter by role
        task_type: Filter by task type
        since: Filter by date (YYYY-MM-DD)
        success_only: Only successful tasks
        failures_only: Only failed tasks

    Returns:
        List of metric events (newest first)
    """
    events = _load_metrics()

    # Apply filters
    if role:
        events = [e for e in events if e.get("role") == role]
    if task_type:
        events = [e for e in events if e.get("task_type") == task_type]
    if since:
        events = [e for e in events if e.get("timestamp", "")[:10] >= since]
    if success_only:
        events = [e for e in events if e.get("success")]
    if failures_only:
        events = [e for e in events if not e.get("success")]

    # Return newest first, limited
    return list(reversed(events[-limit:]))


def get_summary() -> dict:
    """Get summary statistics for dashboard."""
    events = _load_metrics()

    if not events:
        return {
            "total": 0,
            "success_count": 0,
            "success_rate": 0.0,
            "today_count": 0,
            "avg_duration_ms": 0,
            "by_role": {},
            "by_model": {},
            "retry_rate": 0.0,
            "avg_judge_score": None,
            "patch_success_rate": None,
            "test_pass_rate": None,
        }

    today = datetime.now().strftime("%Y-%m-%d")
    today_events = [e for e in events if e.get("timestamp", "")[:10] == today]

    # Success stats
    success_count = sum(1 for e in events if e.get("success"))
    success_rate = success_count / len(events) if events else 0

    # Duration stats
    durations = [e.get("duration_ms", 0) for e in events if e.get("duration_ms")]
    avg_duration = sum(durations) / len(durations) if durations else 0

    # By role
    by_role = {}
    for e in events:
        role = e.get("role", "unknown")
        if role not in by_role:
            by_role[role] = {"total": 0, "success": 0}
        by_role[role]["total"] += 1
        if e.get("success"):
            by_role[role]["success"] += 1

    # Calculate success rates per role
    for role_stats in by_role.values():
        role_stats["success_rate"] = (
            role_stats["success"] / role_stats["total"]
            if role_stats["total"] > 0
            else 0
        )

    # By model
    by_model = {}
    for e in events:
        model = e.get("model", "unknown")
        if model and model != "unknown":
            if model not in by_model:
                by_model[model] = {"total": 0, "durations": []}
            by_model[model]["total"] += 1
            if e.get("duration_ms"):
                by_model[model]["durations"].append(e["duration_ms"])

    # Calculate avg duration per model
    for model_stats in by_model.values():
        durs = model_stats["durations"]
        model_stats["avg_duration_ms"] = sum(durs) / len(durs) if durs else 0
        del model_stats["durations"]

    # Retry rate
    retry_count = sum(1 for e in events if e.get("retries", 0) > 0)
    retry_rate = retry_count / len(events) if events else 0

    # Judge scores
    judge_scores = [e.get("judge_score") for e in events if e.get("judge_score") is not None]
    avg_judge = sum(judge_scores) / len(judge_scores) if judge_scores else None

    # Patch success rate
    patch_events = [e for e in events if e.get("patch_applied") is not None]
    patch_success = sum(1 for e in patch_events if e.get("patch_applied"))
    patch_rate = patch_success / len(patch_events) if patch_events else None

    # Test pass rate
    test_events = [e for e in events if e.get("tests_passed") is not None]
    test_success = sum(1 for e in test_events if e.get("tests_passed"))
    test_rate = test_success / len(test_events) if test_events else None

    return {
        "total": len(events),
        "success_count": success_count,
        "success_rate": success_rate,
        "today_count": len(today_events),
        "avg_duration_ms": avg_duration,
        "by_role": by_role,
        "by_model": by_model,
        "retry_rate": retry_rate,
        "avg_judge_score": avg_judge,
        "patch_success_rate": patch_rate,
        "test_pass_rate": test_rate,
    }


def get_performance_by_model() -> dict[str, dict]:
    """Get performance stats grouped by model."""
    summary = get_summary()
    return summary.get("by_model", {})


def get_success_rate_by_role() -> dict[str, float]:
    """Get success rate grouped by role."""
    summary = get_summary()
    return {
        role: stats.get("success_rate", 0)
        for role, stats in summary.get("by_role", {}).items()
    }


# Thresholds for metric health indicators
THRESHOLDS = {
    "success_rate": {"good": 0.90, "okay": 0.70},
    "avg_duration_ms": {"good": 2000, "okay": 5000},  # Lower is better
    "retry_rate": {"good": 0.10, "okay": 0.25},  # Lower is better
    "avg_judge_score": {"good": 0.80, "okay": 0.60},
    "patch_success_rate": {"good": 0.85, "okay": 0.60},
    "test_pass_rate": {"good": 0.90, "okay": 0.70},
}


def get_health_indicator(metric: str, value: float | None) -> str:
    """Get health indicator for a metric value.

    Returns: 'good', 'okay', or 'bad'
    """
    if value is None:
        return "unknown"

    thresholds = THRESHOLDS.get(metric)
    if not thresholds:
        return "unknown"

    # For metrics where lower is better
    if metric in ("avg_duration_ms", "retry_rate"):
        if value <= thresholds["good"]:
            return "good"
        elif value <= thresholds["okay"]:
            return "okay"
        else:
            return "bad"
    else:
        # Higher is better
        if value >= thresholds["good"]:
            return "good"
        elif value >= thresholds["okay"]:
            return "okay"
        else:
            return "bad"


def clear_metrics() -> None:
    """Clear all metrics (for testing)."""
    with _lock:
        if METRICS_FILE.exists():
            METRICS_FILE.unlink()


__all__ = [
    "MetricEvent",
    "log_metric",
    "get_metrics",
    "get_summary",
    "get_performance_by_model",
    "get_success_rate_by_role",
    "get_health_indicator",
    "clear_metrics",
    "THRESHOLDS",
]
