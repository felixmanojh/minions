#!/usr/bin/env python3
"""
Minion Check - run verification tasks across files.

Usage:
    python scripts/check.py "Check for missing docstrings" --files "src/**/*.py"
    python scripts/check.py "Find TODO comments" --files "*.py" --json
"""

from __future__ import annotations

import argparse
import asyncio
import glob
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from llm_gc.swarm import Swarm


async def run_check(
    task: str,
    files: list[str],
    repo_root: str = ".",
    max_workers: int = 5,
) -> dict:
    """Run verification task across files."""
    swarm = Swarm(
        workers=max_workers,
        max_retries=1,
        repo_root=repo_root,
        show_progress=True,
    )

    # Add check tasks for each file
    for file_pattern in files:
        root = Path(repo_root)
        matches = list(root.glob(file_pattern))

        for file_path in matches:
            if file_path.is_file():
                rel_path = str(file_path.relative_to(root))
                file_task = f"{task} in {rel_path}"
                swarm.add_task(
                    description=file_task,
                    context_files=[rel_path],
                )

    if not swarm.tasks:
        return {
            "task": task,
            "files_checked": 0,
            "findings": [],
            "stats": {"completed": 0, "failed": 0, "elapsed_seconds": 0},
            "error": "No files matched the patterns",
        }

    result = await swarm.run()

    # Extract findings
    findings = []
    for completed in result["completed"]:
        if completed.get("result"):
            findings.append({
                "file": completed.get("context_files", ["unknown"])[0] if completed.get("context_files") else "unknown",
                "analysis": completed["result"],
            })

    return {
        "task": task,
        "files_checked": len(swarm.tasks),
        "findings": findings,
        "stats": result["stats"],
    }


def main():
    parser = argparse.ArgumentParser(
        description="Run verification tasks across files using minions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/check.py "Check for missing docstrings" --files "src/**/*.py"
    python scripts/check.py "Find TODO comments" --files "*.py" --json
    python scripts/check.py "Review for bugs" --files src/api.py src/utils.py
        """,
    )
    parser.add_argument("task", help="The verification task to run")
    parser.add_argument(
        "--files",
        nargs="+",
        required=True,
        help="File patterns to check (glob patterns supported)",
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root (default: current directory)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=5,
        help="Number of parallel workers (default: 5)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )

    args = parser.parse_args()

    result = asyncio.run(
        run_check(
            task=args.task,
            files=args.files,
            repo_root=args.repo_root,
            max_workers=args.workers,
        )
    )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"\n{'=' * 50}")
        print(f"Check: {result['task']}")
        print(f"Files checked: {result['files_checked']}")
        print(f"{'=' * 50}\n")

        if result.get("error"):
            print(f"Error: {result['error']}")
        elif result["findings"]:
            for finding in result["findings"]:
                print(f"📄 {finding['file']}")
                print(f"   {finding['analysis'][:200]}...")
                print()
        else:
            print("No findings.")

        stats = result["stats"]
        print(f"\nCompleted: {stats['completed']}, Failed: {stats['failed']}, Time: {stats['elapsed_seconds']:.1f}s")


if __name__ == "__main__":
    main()
