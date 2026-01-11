#!/usr/bin/env python3
"""CLI entry point for Milestone M1 chat."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from llm_gc.orchestrator.m1_chat import run_chat
from llm_gc.skill import parse_read_requests


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Implementer/Reviewer chat loop")
    parser.add_argument("task", help="Natural language task description")
    parser.add_argument("--rounds", type=int, default=3, help="Number of Implementer rounds")
    parser.add_argument(
        "--preset",
        choices=["nano", "small", "medium", "large"],
        default=None,
        help="Model preset: nano (0.5B), small (1-3B), medium (7B), large (14B+)",
    )
    parser.add_argument(
        "--config", type=Path, default=None, help="Optional path to models.yaml override"
    )
    parser.add_argument(
        "--sessions", type=Path, default=Path("sessions"), help="Where to store transcripts"
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Path to the repo root for context reads",
    )
    parser.add_argument(
        "--read",
        action="append",
        default=[],
        metavar="PATH[:START-END]",
        help="Preload a file snippet (can be passed multiple times)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON summary (for tooling integration)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    read_requests = parse_read_requests(args.read)
    result = run_chat(
        task=args.task,
        rounds=args.rounds,
        preset=args.preset,
        config_path=args.config,
        session_dir=args.sessions,
        repo_root=args.repo_root,
        read_requests=read_requests,
    )
    if args.json:
        payload = {
            "task": args.task,
            "rounds": args.rounds,
            "preset": args.preset or "default",
            "repo_root": str(args.repo_root),
            "read_requests": [req.describe() for req in read_requests],
            "summary": result.get("summary", ""),
            "transcript_path": str(result.get("transcript_path")),
            "summary_path": str(result.get("summary_path")),
            "metadata": result.get("metadata", {}),
        }
        print(json.dumps(payload, indent=2))
        return

    print("\n=== Final Summary ===\n")
    print(result.get("summary", ""))
    print(f"\nTranscript saved to: {result['transcript_path']}")
    if result.get("summary_path"):
        print(f"Repo summary saved to: {result['summary_path']}")
    if read_requests:
        print("Context files:")
        for req in read_requests:
            print(f" - {req.describe()}")


if __name__ == "__main__":  # pragma: no cover
    main()
