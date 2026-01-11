#!/usr/bin/env python3
"""CLI for swarm mode - dispatch multiple minions in parallel."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Auto-bootstrap venv and dependencies
from llm_gc.bootstrap import ensure_venv
ensure_venv()

import argparse
import json

from llm_gc.swarm import Swarm


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Swarm mode: dispatch multiple minions in parallel"
    )
    parser.add_argument(
        "--workers", type=int, default=5, help="Number of parallel workers (default: 5)"
    )
    parser.add_argument(
        "--retries", type=int, default=2, help="Max retries per task (default: 2)"
    )
    parser.add_argument(
        "--rounds", type=int, default=2, help="Rounds per task (default: 2)"
    )
    parser.add_argument(
        "--repo-root", type=Path, default=Path.cwd(), help="Repository root"
    )
    parser.add_argument(
        "--json", action="store_true", help="Output JSON results"
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Batch command - takes JSON input
    batch = subparsers.add_parser("batch", help="Run batch from JSON file or stdin")
    batch.add_argument(
        "input", nargs="?", type=Path, help="JSON file with tasks (or stdin)"
    )

    # Quick multi-patch command
    patch = subparsers.add_parser("patch", help="Run same patch on multiple files")
    patch.add_argument("description", help="Task description")
    patch.add_argument("files", nargs="+", help="Target files")

    # Quick multi-chat command
    chat = subparsers.add_parser("chat", help="Run same chat on multiple contexts")
    chat.add_argument("description", help="Task description")
    chat.add_argument("--context", action="append", default=[], help="Context files")

    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    swarm = Swarm(
        workers=args.workers,
        max_retries=args.retries,
        rounds=args.rounds,
        repo_root=str(args.repo_root),
    )

    if args.command == "batch":
        # Read tasks from JSON
        if args.input:
            data = json.loads(args.input.read_text())
        else:
            data = json.loads(sys.stdin.read())

        tasks = data if isinstance(data, list) else data.get("tasks", [])
        for t in tasks:
            if t.get("kind") == "patch":
                swarm.add_patch(
                    description=t["description"],
                    target=t["target"],
                    context_files=t.get("context_files", []),
                )
            else:
                swarm.add_chat(
                    description=t["description"],
                    context_files=t.get("context_files", []),
                )

    elif args.command == "patch":
        # Same task on multiple files
        for f in args.files:
            swarm.add_patch(
                description=args.description,
                target=f,
                context_files=[f],
            )

    elif args.command == "chat":
        # Single chat with context
        swarm.add_chat(
            description=args.description,
            context_files=args.context,
        )

    # Run the swarm
    results = await swarm.run()

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        # Summary
        stats = results["stats"]
        print(f"\n{'='*50}")
        print(f"🍌 SWARM RESULTS")
        print(f"{'='*50}")
        print(f"Completed: {stats['completed']}/{stats['total']}")
        print(f"Failed:    {stats['failed']}")
        print(f"Retries:   {stats['retries']}")
        print(f"Time:      {stats['elapsed_seconds']:.1f}s")
        print()

        if results["completed"]:
            print("✅ Completed tasks:")
            for t in results["completed"]:
                print(f"   • {t['description'][:50]}...")
                if t.get("result"):
                    print(f"     → {t['result']}")

        if results["failed"]:
            print("\n❌ Failed tasks:")
            for t in results["failed"]:
                print(f"   • {t['description'][:50]}...")
                if t.get("error"):
                    print(f"     Error: {t['error'][:50]}...")


if __name__ == "__main__":
    asyncio.run(main())
