"""Swarm mode: parallel minion execution with auto-retry."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional
import sys
import time

from llm_gc.orchestrator.m1_chat import run_chat
from llm_gc.orchestrator.m3_patch import run_patch
from llm_gc.skill import parse_read_requests


@dataclass
class MinionTask:
    """A single task for a minion."""
    description: str
    kind: str = "chat"  # "chat" or "patch"
    target: Optional[str] = None
    context_files: List[str] = field(default_factory=list)
    repo_root: str = "."
    rounds: int = 2  # Fewer rounds for speed
    retries: int = 0
    max_retries: int = 2
    status: str = "pending"
    result: Optional[str] = None
    error: Optional[str] = None


def simplify_prompt(prompt: str, retry_count: int) -> str:
    """Make prompt simpler for retry attempts (minion-speak)."""
    if retry_count == 0:
        return prompt

    # Retry 1: Strip to essentials
    if retry_count == 1:
        # Remove verbose language
        simple = prompt.replace("Please ", "").replace("Could you ", "")
        simple = simple.replace("I need you to ", "").replace("I want you to ", "")
        # Add minion-speak directive
        return f"SIMPLE TASK. ONE THING ONLY.\n{simple}\nOUTPUT ONLY THE RESULT. NO EXPLANATION."

    # Retry 2+: Ultra simple
    words = prompt.split()[:20]  # First 20 words only
    return f"DO THIS: {' '.join(words)}..."


def run_minion_task(task: MinionTask) -> MinionTask:
    """Run a single minion task with retry logic."""
    prompt = simplify_prompt(task.description, task.retries)

    try:
        if task.kind == "patch":
            result = run_patch(
                task=prompt,
                rounds=task.rounds,
                repo_root=task.repo_root,
                read_requests=parse_read_requests(task.context_files),
                target_files=[task.target] if task.target else [],
            )
            task.result = str(result.get("patch_path", ""))
            task.status = "completed" if result.get("patch_path") else "empty"
        else:
            result = run_chat(
                task=prompt,
                rounds=task.rounds,
                repo_root=task.repo_root,
                read_requests=parse_read_requests(task.context_files),
            )
            task.result = result.get("summary", "")
            task.status = "completed"
    except Exception as e:
        task.error = str(e)
        task.status = "failed"

    return task


def _worker(task_dict: dict) -> dict:
    """Pickle-friendly worker wrapper."""
    task = MinionTask(**task_dict)
    result = run_minion_task(task)
    return {
        "description": result.description,
        "kind": result.kind,
        "target": result.target,
        "context_files": result.context_files,
        "repo_root": result.repo_root,
        "rounds": result.rounds,
        "retries": result.retries,
        "max_retries": result.max_retries,
        "status": result.status,
        "result": result.result,
        "error": result.error,
    }


class Swarm:
    """Dispatch multiple minions in parallel with auto-retry."""

    def __init__(
        self,
        workers: int = 5,
        max_retries: int = 2,
        rounds: int = 2,
        repo_root: str = ".",
    ):
        self.workers = workers
        self.max_retries = max_retries
        self.rounds = rounds
        self.repo_root = repo_root
        self.tasks: List[MinionTask] = []
        self.completed: List[MinionTask] = []
        self.failed: List[MinionTask] = []

    def add_chat(self, description: str, context_files: List[str] = None) -> None:
        """Add a chat task to the swarm."""
        self.tasks.append(MinionTask(
            description=description,
            kind="chat",
            context_files=context_files or [],
            repo_root=self.repo_root,
            rounds=self.rounds,
            max_retries=self.max_retries,
        ))

    def add_patch(
        self,
        description: str,
        target: str,
        context_files: List[str] = None,
    ) -> None:
        """Add a patch task to the swarm."""
        self.tasks.append(MinionTask(
            description=description,
            kind="patch",
            target=target,
            context_files=context_files or [],
            repo_root=self.repo_root,
            rounds=self.rounds,
            max_retries=self.max_retries,
        ))

    def run(self, on_progress: Callable[[str], None] = None) -> dict:
        """Execute all tasks with parallel workers and auto-retry.

        Returns:
            dict with completed, failed, and stats
        """
        pending = list(self.tasks)
        retry_queue: List[MinionTask] = []

        total = len(pending)
        completed_count = 0
        failed_count = 0
        retry_count = 0

        def log(msg: str):
            if on_progress:
                on_progress(msg)
            else:
                print(msg, file=sys.stderr)

        log(f"🍌 Swarm starting: {total} tasks, {self.workers} workers")
        start_time = time.time()

        while pending or retry_queue:
            # Add retries to pending
            pending.extend(retry_queue)
            retry_queue = []

            if not pending:
                break

            # Run batch
            with ProcessPoolExecutor(max_workers=self.workers) as executor:
                task_dicts = [
                    {
                        "description": t.description,
                        "kind": t.kind,
                        "target": t.target,
                        "context_files": t.context_files,
                        "repo_root": t.repo_root,
                        "rounds": t.rounds,
                        "retries": t.retries,
                        "max_retries": t.max_retries,
                        "status": t.status,
                        "result": t.result,
                        "error": t.error,
                    }
                    for t in pending
                ]

                futures = {executor.submit(_worker, d): d for d in task_dicts}
                pending = []

                for future in as_completed(futures):
                    try:
                        result = future.result()
                        task = MinionTask(**result)

                        if task.status == "completed":
                            self.completed.append(task)
                            completed_count += 1
                            log(f"  🍌 Done: {task.description[:40]}...")
                        elif task.status == "empty":
                            # Empty result, might retry
                            if task.retries < task.max_retries:
                                task.retries += 1
                                retry_queue.append(task)
                                retry_count += 1
                                log(f"  🔄 Retry {task.retries}: {task.description[:40]}...")
                            else:
                                self.failed.append(task)
                                failed_count += 1
                                log(f"  ❌ Empty: {task.description[:40]}...")
                        else:  # failed
                            if task.retries < task.max_retries:
                                task.retries += 1
                                retry_queue.append(task)
                                retry_count += 1
                                log(f"  🔄 Retry {task.retries}: {task.description[:40]}...")
                            else:
                                self.failed.append(task)
                                failed_count += 1
                                log(f"  ❌ Failed: {task.description[:40]}...")
                    except Exception as e:
                        failed_count += 1
                        log(f"  ❌ Error: {e}")

        elapsed = time.time() - start_time
        log(f"\n🍌 Swarm complete! {completed_count}/{total} succeeded in {elapsed:.1f}s")
        if retry_count:
            log(f"   Retries: {retry_count}")
        if failed_count:
            log(f"   Failed: {failed_count}")

        return {
            "completed": [t.__dict__ for t in self.completed],
            "failed": [t.__dict__ for t in self.failed],
            "stats": {
                "total": total,
                "completed": completed_count,
                "failed": failed_count,
                "retries": retry_count,
                "elapsed_seconds": elapsed,
            }
        }


def swarm_dispatch(
    tasks: List[dict],
    workers: int = 5,
    max_retries: int = 2,
    repo_root: str = ".",
) -> dict:
    """Convenience function to dispatch multiple tasks.

    Args:
        tasks: List of dicts with keys:
            - description: str (required)
            - kind: "chat" or "patch" (default: "chat")
            - target: str (required for patch)
            - context_files: List[str] (optional)
        workers: Number of parallel workers
        max_retries: Max retries per task
        repo_root: Repository root path

    Returns:
        Results dict with completed, failed, and stats
    """
    swarm = Swarm(workers=workers, max_retries=max_retries, repo_root=repo_root)

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

    return swarm.run()


__all__ = ["MinionTask", "Swarm", "swarm_dispatch", "simplify_prompt"]
