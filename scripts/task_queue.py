#!/usr/bin/env python3
"""CLI interface for the local task queue."""

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

from llm_gc.skill import parse_read_requests
from llm_gc.task_queue import TaskQueue


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Queue local LLM tasks")
    parser.add_argument(
        "--queue-file",
        type=Path,
        default=Path("sessions/task_queue.json"),
        help="Path to JSON queue file",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    enqueue_chat = subparsers.add_parser("enqueue-chat", help="Queue a chat task")
    enqueue_chat.add_argument("task", help="Task description")
    enqueue_chat.add_argument("--repo-root", type=Path, default=Path.cwd())
    enqueue_chat.add_argument("--rounds", type=int, default=3)
    enqueue_chat.add_argument(
        "--read", action="append", default=[], metavar="PATH[:START-END]"
    )

    enqueue_patch = subparsers.add_parser("enqueue-patch", help="Queue a patch task")
    enqueue_patch.add_argument("task", help="Task description")
    enqueue_patch.add_argument("--repo-root", type=Path, default=Path.cwd())
    enqueue_patch.add_argument("--rounds", type=int, default=4)
    enqueue_patch.add_argument(
        "--read", action="append", default=[], metavar="PATH[:START-END]"
    )
    enqueue_patch.add_argument("--target", action="append", default=[], metavar="PATH")

    subparsers.add_parser("list", help="List queued tasks")
    subparsers.add_parser("run-next", help="Execute the next pending task")

    run_parallel = subparsers.add_parser("run-parallel", help="Run all pending tasks in parallel")
    run_parallel.add_argument(
        "--workers", type=int, default=3, help="Max concurrent tasks (default: 3)"
    )

    subparsers.add_parser("clear-completed", help="Remove completed/failed tasks from queue")

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    queue = TaskQueue(path=args.queue_file)
    if args.command == "enqueue-chat":
        task = queue.enqueue_chat(
            description=args.task,
            repo_root=args.repo_root,
            rounds=args.rounds,
            read_requests=args.read,
        )
        print(json.dumps({"queued": task.id, "kind": task.kind}, indent=2))
    elif args.command == "enqueue-patch":
        task = queue.enqueue_patch(
            description=args.task,
            repo_root=args.repo_root,
            rounds=args.rounds,
            read_requests=args.read,
            targets=args.target,
        )
        print(json.dumps({"queued": task.id, "kind": task.kind}, indent=2))
    elif args.command == "list":
        tasks = [task.__dict__ for task in queue.list_tasks()]
        print(json.dumps(tasks, indent=2))
    elif args.command == "run-next":
        task = queue.run_next()
        if not task:
            print("No pending tasks.")
            return
        print(json.dumps(task.__dict__, indent=2))
    elif args.command == "run-parallel":
        print(f"Running pending tasks with {args.workers} workers...")
        results = queue.run_parallel(max_workers=args.workers)
        if not results:
            print("No pending tasks.")
            return
        print(f"\nCompleted {len(results)} tasks:")
        for task in results:
            status_icon = "✓" if task.status == "completed" else "✗"
            print(f"  {status_icon} {task.description[:50]}...")
            if task.result_path:
                print(f"    → {task.result_path}")
        print(json.dumps([t.__dict__ for t in results], indent=2))
    elif args.command == "clear-completed":
        before = len(queue.tasks)
        queue.tasks = [t for t in queue.tasks if t.status == "pending"]
        queue._persist()
        removed = before - len(queue.tasks)
        print(f"Removed {removed} completed/failed tasks.")
    else:  # pragma: no cover
        raise ValueError(f"Unknown command {args.command}")


if __name__ == "__main__":
    main()
