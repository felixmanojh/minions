"""Failure logging for minion operations.

Dual logging:
- Quick reference log: ~/.minions/failures.log
- Full session data: ~/.minions/sessions/<timestamp>.json
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


MINIONS_DIR = Path.home() / ".minions"
FAILURES_LOG = MINIONS_DIR / "failures.log"
SESSIONS_DIR = MINIONS_DIR / "sessions"


def ensure_dirs():
    """Ensure minions directories exist."""
    MINIONS_DIR.mkdir(parents=True, exist_ok=True)
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def log_failure(
    file: str,
    reason: str,
    task: Optional[str] = None,
    original: Optional[str] = None,
    generated: Optional[str] = None,
    attempts: int = 1,
    extra: Optional[dict[str, Any]] = None,
) -> Path:
    """Log failure to both quick log and full session.

    Args:
        file: File path that failed
        reason: Failure reason
        task: Task that was attempted
        original: Original file content
        generated: Generated content (if any)
        attempts: Number of attempts made
        extra: Additional data to log

    Returns:
        Path to the session file.
    """
    ensure_dirs()
    timestamp = datetime.now()
    timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
    session_id = timestamp.strftime("%Y%m%d_%H%M%S")

    # Quick reference log (one line per failure)
    with open(FAILURES_LOG, "a") as f:
        # Truncate reason for quick log
        short_reason = reason[:100].replace("\n", " ")
        f.write(f"{timestamp_str} | {file} | FAIL | {short_reason}\n")

    # Full session data
    session_data = {
        "timestamp": timestamp_str,
        "file": file,
        "status": "failed",
        "reason": reason,
        "attempts": attempts,
    }

    if task:
        session_data["task"] = task
    if original:
        session_data["original"] = original
    if generated:
        session_data["generated"] = generated
    if extra:
        session_data.update(extra)

    session_file = SESSIONS_DIR / f"{session_id}.json"
    with open(session_file, "w") as f:
        json.dump(session_data, f, indent=2)

    return session_file


def log_success(
    file: str,
    task: Optional[str] = None,
    original: Optional[str] = None,
    generated: Optional[str] = None,
    attempts: int = 1,
    extra: Optional[dict[str, Any]] = None,
) -> Path:
    """Log successful operation to session file.

    Args:
        file: File path that succeeded
        task: Task that was performed
        original: Original file content
        generated: Generated content
        attempts: Number of attempts made
        extra: Additional data to log

    Returns:
        Path to the session file.
    """
    ensure_dirs()
    timestamp = datetime.now()
    timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
    session_id = timestamp.strftime("%Y%m%d_%H%M%S")

    session_data = {
        "timestamp": timestamp_str,
        "file": file,
        "status": "success",
        "attempts": attempts,
    }

    if task:
        session_data["task"] = task
    if original:
        session_data["original"] = original
    if generated:
        session_data["generated"] = generated
    if extra:
        session_data.update(extra)

    session_file = SESSIONS_DIR / f"{session_id}.json"
    with open(session_file, "w") as f:
        json.dump(session_data, f, indent=2)

    return session_file


def get_recent_failures(limit: int = 10) -> list[str]:
    """Get recent failure log lines.

    Args:
        limit: Maximum number of lines to return

    Returns:
        List of recent failure log lines.
    """
    if not FAILURES_LOG.exists():
        return []

    with open(FAILURES_LOG, "r") as f:
        lines = f.readlines()

    return [line.strip() for line in lines[-limit:]]


def get_session(session_id: str) -> Optional[dict]:
    """Load a session file by ID.

    Args:
        session_id: Session ID (timestamp format YYYYMMDD_HHMMSS)

    Returns:
        Session data dict or None if not found.
    """
    session_file = SESSIONS_DIR / f"{session_id}.json"
    if not session_file.exists():
        return None

    with open(session_file, "r") as f:
        return json.load(f)


def clear_old_sessions(days: int = 7) -> int:
    """Delete session files older than N days.

    Args:
        days: Delete sessions older than this many days

    Returns:
        Number of sessions deleted.
    """
    if not SESSIONS_DIR.exists():
        return 0

    cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
    deleted = 0

    for session_file in SESSIONS_DIR.glob("*.json"):
        if session_file.stat().st_mtime < cutoff:
            session_file.unlink()
            deleted += 1

    return deleted
