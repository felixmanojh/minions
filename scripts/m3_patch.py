#!/usr/bin/env python3
"""CLI entry point for Milestone M3 patch workflow."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from llm_gc.orchestrator.m3_patch import run_patch
from llm_gc.skill import parse_read_requests


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run patch-focused Implementer/Reviewer chat")
    parser.add_argument("task", help="Natural language task description")
    parser.add_argument("--rounds", type=int, default=4, help="Total number of rounds")
    parser.add_argument(
        "--preset",
        choices=["nano", "small", "medium", "large"],
        default=None,
        help="Model preset: nano (0.5B), small (1-3B), medium (7B), large (14B+)",
    )
    parser.add_argument("--config", type=Path, default=None, help="Path to models.yaml override")
    parser.add_argument(
        "--sessions", type=Path, default=Path("sessions"), help="Directory to store artifacts"
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root (file reads/diffs scoped here)",
    )
    parser.add_argument(
        "--read",
        action="append",
        default=[],
        metavar="PATH[:START-END]",
        help="Preload file snippets (repeatable)",
    )
    parser.add_argument(
        "--target",
        action="append",
        default=[],
        metavar="PATH",
        help="Target files expected to change (repeatable)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON output for downstream tooling",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    read_requests = parse_read_requests(args.read)
    result = run_patch(
        task=args.task,
        rounds=args.rounds,
        preset=args.preset,
        config_path=args.config,
        session_dir=args.sessions,
        repo_root=args.repo_root,
        read_requests=read_requests,
        target_files=args.target,
    )
    if args.json:
        payload = {
            "task": args.task,
            "rounds": args.rounds,
            "preset": args.preset or "default",
            "repo_root": str(args.repo_root),
            "read_requests": [req.describe() for req in read_requests],
            "targets": args.target,
            "summary": result.get("summary", ""),
            "transcript_path": str(result.get("transcript_path")),
            "summary_path": str(result.get("summary_path")),
            "patch_path": str(result.get("patch_path")),
            "metadata": result.get("metadata", {}),
        }
        print(json.dumps(payload, indent=2))
        return

    print("\n=== Final Summary ===\n")
    print(result.get("summary", ""))
    print(f"\nTranscript saved to: {result['transcript_path']}")
    if result.get("summary_path"):
        print(f"Repo summary saved to: {result['summary_path']}")
    if result.get("patch_path"):
        print(f"Unified diff saved to: {result['patch_path']}")


if __name__ == "__main__":  # pragma: no cover
    main()
