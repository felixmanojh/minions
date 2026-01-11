#!/usr/bin/env python3
"""Minion Metrics CLI - View performance, quality, and usage analytics."""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime

from llm_gc.metrics import (
    THRESHOLDS,
    get_health_indicator,
    get_metrics,
    get_summary,
)


# ANSI color codes
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"


def color_indicator(health: str) -> str:
    """Get colored indicator for health status."""
    if health == "good":
        return f"{GREEN}●{RESET}"
    elif health == "okay":
        return f"{YELLOW}●{RESET}"
    elif health == "bad":
        return f"{RED}●{RESET}"
    return "○"


def format_duration(ms: float) -> str:
    """Format duration in human-readable form."""
    if ms < 1000:
        return f"{ms:.0f}ms"
    elif ms < 60000:
        return f"{ms/1000:.1f}s"
    else:
        return f"{ms/60000:.1f}m"


def format_percent(value: float | None) -> str:
    """Format percentage."""
    if value is None:
        return "N/A"
    return f"{value * 100:.0f}%"


def print_dashboard():
    """Print the main metrics dashboard."""
    summary = get_summary()

    if summary["total"] == 0:
        print("No metrics recorded yet. Run some minion tasks first!")
        return

    # Header
    print(f"\n{BOLD}┌─────────────────────────────────────────┐{RESET}")
    print(f"{BOLD}│ 🍌 MINION METRICS                       │{RESET}")
    print(f"{BOLD}├─────────────────────────────────────────┤{RESET}")

    # Overview
    success_health = get_health_indicator("success_rate", summary["success_rate"])
    print(f"│ Tasks: {summary['total']} total ({summary['success_count']} success, {format_percent(summary['success_rate'])}) {color_indicator(success_health)}")
    print(f"│ Today: {summary['today_count']} tasks, avg {format_duration(summary['avg_duration_ms'])}")
    print("│")

    # By Role
    print("│ By Role:")
    for role, stats in sorted(summary["by_role"].items()):
        if role and role != "unknown":
            rate = stats.get("success_rate", 0)
            print(f"│   {role.capitalize():12} {stats['total']:3}  ({format_percent(rate)} success)")
    print("│")

    # Performance
    print("│ Performance:")
    duration_health = get_health_indicator("avg_duration_ms", summary["avg_duration_ms"])
    print(f"│   Avg latency: {format_duration(summary['avg_duration_ms'])} {color_indicator(duration_health)}")

    # Fastest model
    if summary["by_model"]:
        fastest = min(summary["by_model"].items(), key=lambda x: x[1].get("avg_duration_ms", float("inf")))
        print(f"│   Fastest: {fastest[0]} ({format_duration(fastest[1]['avg_duration_ms'])})")

    retry_health = get_health_indicator("retry_rate", summary["retry_rate"])
    retry_count = int(summary["retry_rate"] * summary["total"])
    print(f"│   Retries: {retry_count} ({format_percent(summary['retry_rate'])}) {color_indicator(retry_health)}")
    print("│")

    # Quality
    print("│ Quality:")
    if summary["avg_judge_score"] is not None:
        judge_health = get_health_indicator("avg_judge_score", summary["avg_judge_score"])
        print(f"│   Avg judge score: {summary['avg_judge_score']:.2f} {color_indicator(judge_health)}")

    if summary["patch_success_rate"] is not None:
        patch_health = get_health_indicator("patch_success_rate", summary["patch_success_rate"])
        print(f"│   Patches applied: {format_percent(summary['patch_success_rate'])} {color_indicator(patch_health)}")

    if summary["test_pass_rate"] is not None:
        test_health = get_health_indicator("test_pass_rate", summary["test_pass_rate"])
        print(f"│   Tests passed: {format_percent(summary['test_pass_rate'])} {color_indicator(test_health)}")

    print(f"{BOLD}└─────────────────────────────────────────┘{RESET}\n")


def print_help_metrics():
    """Print metric reference guide."""
    print(f"""
{BOLD}┌─────────────────────────────────────────────────────────────┐
│ 📊 METRIC REFERENCE                                         │
├─────────────────────────────────────────────────────────────┤{RESET}
│ {BOLD}SUCCESS RATE{RESET}                                                │
│   What: % of tasks completed without error                  │
│   {GREEN}Good: >90%{RESET}  │  {YELLOW}Okay: 70-90%{RESET}  │  {RED}Bad: <70%{RESET}                │
│   Fix: Check model availability, simplify prompts           │
│                                                             │
│ {BOLD}LATENCY{RESET} (avg response time)                                 │
│   What: Time from request to response                       │
│   {GREEN}Good: <2s{RESET}   │  {YELLOW}Okay: 2-5s{RESET}    │  {RED}Bad: >5s{RESET}                 │
│   Fix: Use smaller models, check Ollama resources           │
│                                                             │
│ {BOLD}RETRY RATE{RESET}                                                  │
│   What: % of tasks needing retry                            │
│   {GREEN}Good: <10%{RESET}  │  {YELLOW}Okay: 10-25%{RESET}  │  {RED}Bad: >25%{RESET}                │
│   Fix: Improve prompts, use more capable models             │
│                                                             │
│ {BOLD}JUDGE SCORE{RESET}                                                 │
│   What: Quality score (0-1) from Judge agent                │
│   {GREEN}Good: >0.8{RESET}  │  {YELLOW}Okay: 0.6-0.8{RESET} │  {RED}Bad: <0.6{RESET}                │
│   Fix: More context, clearer task descriptions              │
│                                                             │
│ {BOLD}PATCH SUCCESS{RESET}                                               │
│   What: % of patches that applied cleanly                   │
│   {GREEN}Good: >85%{RESET}  │  {YELLOW}Okay: 60-85%{RESET}  │  {RED}Bad: <60%{RESET}                │
│   Fix: Provide more file context, use exact matches         │
│                                                             │
│ {BOLD}TEST PASS RATE{RESET}                                              │
│   What: % of test runs that passed                          │
│   {GREEN}Good: >90%{RESET}  │  {YELLOW}Okay: 70-90%{RESET}  │  {RED}Bad: <70%{RESET}                │
│   Fix: Review failing patches, add more context             │
{BOLD}└─────────────────────────────────────────────────────────────┘{RESET}
""")


def print_events(events: list[dict]):
    """Print a list of metric events."""
    if not events:
        print("No matching events found.")
        return

    print(f"\n{BOLD}Recent Events ({len(events)}){RESET}")
    print("-" * 70)

    for e in events[:20]:  # Limit display
        ts = e.get("timestamp", "")[:19]
        task_type = e.get("task_type", "?")[:6]
        role = e.get("role", "?")[:10]
        duration = format_duration(e.get("duration_ms", 0))
        success = "✓" if e.get("success") else "✗"
        desc = e.get("task_description", "")[:30]

        print(f"{ts} │ {task_type:6} │ {role:10} │ {duration:6} │ {success} │ {desc}...")

    if len(events) > 20:
        print(f"... and {len(events) - 20} more")


def export_csv(events: list[dict]):
    """Export events to CSV."""
    if not events:
        return

    writer = csv.DictWriter(sys.stdout, fieldnames=events[0].keys())
    writer.writeheader()
    writer.writerows(events)


def main():
    parser = argparse.ArgumentParser(
        description="Minion Metrics - View analytics for your local LLM minions"
    )

    parser.add_argument(
        "--role",
        type=str,
        help="Filter by role (implementer, reviewer, patcher, judge)",
    )
    parser.add_argument(
        "--type",
        type=str,
        dest="task_type",
        help="Filter by task type (chat, patch, swarm, judge, test)",
    )
    parser.add_argument(
        "--today",
        action="store_true",
        help="Show only today's events",
    )
    parser.add_argument(
        "--failures",
        action="store_true",
        help="Show only failed tasks",
    )
    parser.add_argument(
        "--export",
        type=str,
        choices=["csv"],
        help="Export format",
    )
    parser.add_argument(
        "--help-metrics",
        action="store_true",
        help="Show metric reference guide",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Max events to show (default: 100)",
    )

    args = parser.parse_args()

    if args.help_metrics:
        print_help_metrics()
        return

    # If any filters, show filtered events
    if args.role or args.task_type or args.today or args.failures or args.export:
        since = datetime.now().strftime("%Y-%m-%d") if args.today else None

        events = get_metrics(
            limit=args.limit,
            role=args.role,
            task_type=args.task_type,
            since=since,
            failures_only=args.failures,
        )

        if args.export == "csv":
            export_csv(events)
        else:
            print_events(events)
    else:
        # Default: show dashboard
        print_dashboard()


if __name__ == "__main__":
    main()
