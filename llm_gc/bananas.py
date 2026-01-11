"""Banana counter 🍌 - Track successful minion task completions."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

# Store bananas in user's home directory for persistence
BANANA_FILE = Path.home() / ".minions" / "bananas.json"


def _load_data() -> dict:
    """Load banana data from file."""
    if not BANANA_FILE.exists():
        return {
            "total": 0,
            "history": [],
            "streak": 0,
            "best_streak": 0,
            "last_date": None,
        }
    try:
        return json.loads(BANANA_FILE.read_text())
    except (json.JSONDecodeError, IOError):
        return {"total": 0, "history": [], "streak": 0, "best_streak": 0, "last_date": None}


def _save_data(data: dict) -> None:
    """Save banana data to file."""
    BANANA_FILE.parent.mkdir(parents=True, exist_ok=True)
    BANANA_FILE.write_text(json.dumps(data, indent=2))


def add_bananas(count: int, task_type: str = "swarm") -> int:
    """Add bananas for completed tasks.

    Args:
        count: Number of bananas to add
        task_type: Type of task (swarm, patch, chat)

    Returns:
        New total banana count
    """
    data = _load_data()
    data["total"] += count

    # Track history (last 100 entries)
    today = datetime.now().strftime("%Y-%m-%d")
    data["history"].append({
        "date": today,
        "count": count,
        "type": task_type,
        "timestamp": datetime.now().isoformat(),
    })
    data["history"] = data["history"][-100:]  # Keep last 100

    # Update streak
    if data["last_date"] == today:
        pass  # Same day, streak continues
    elif data["last_date"] == (datetime.now().date().isoformat()):
        data["streak"] += 1
    else:
        # Check if yesterday
        from datetime import timedelta
        yesterday = (datetime.now().date() - timedelta(days=1)).isoformat()
        if data["last_date"] == yesterday:
            data["streak"] += 1
        else:
            data["streak"] = 1  # Reset streak

    data["last_date"] = today
    data["best_streak"] = max(data["best_streak"], data["streak"])

    _save_data(data)
    return data["total"]


def get_bananas() -> int:
    """Get current banana count."""
    return _load_data()["total"]


def get_stats() -> dict:
    """Get full banana statistics."""
    data = _load_data()

    # Calculate today's bananas
    today = datetime.now().strftime("%Y-%m-%d")
    today_bananas = sum(
        h["count"] for h in data["history"]
        if h.get("date") == today
    )

    return {
        "total": data["total"],
        "today": today_bananas,
        "streak": data["streak"],
        "best_streak": data["best_streak"],
    }


def format_stats() -> str:
    """Format banana stats for display."""
    stats = get_stats()

    # Banana pile based on total
    total = stats["total"]
    if total == 0:
        pile = "🍌"
    elif total < 10:
        pile = "🍌" * total
    elif total < 50:
        pile = "🍌" * 10 + f" (+{total - 10})"
    elif total < 100:
        pile = "🍌🍌🍌🍌🍌 x10"
    elif total < 500:
        pile = "🍌🍌🍌🍌🍌 x20+"
    else:
        pile = "🍌👑 BANANA KING!"

    lines = [
        "=" * 40,
        "🍌 BANANA STATS 🍌",
        "=" * 40,
        f"Total bananas: {stats['total']}",
        f"Today: {stats['today']}",
        f"Current streak: {stats['streak']} days",
        f"Best streak: {stats['best_streak']} days",
        "",
        pile,
        "=" * 40,
    ]
    return "\n".join(lines)


def celebrate(count: int) -> str:
    """Generate celebration message for earned bananas."""
    if count == 0:
        return ""
    elif count == 1:
        return "🍌 +1 banana!"
    elif count < 5:
        return f"🍌 +{count} bananas!"
    elif count < 10:
        return f"🍌🍌 +{count} bananas! Nice work!"
    elif count < 20:
        return f"🍌🍌🍌 +{count} bananas! Excellent!"
    else:
        return f"🍌🍌🍌🍌🍌 +{count} BANANAS! AMAZING!"


__all__ = ["add_bananas", "get_bananas", "get_stats", "format_stats", "celebrate"]
