"""Swarm mode: parallel minion execution for file processing."""

from __future__ import annotations

import asyncio
import glob as globlib
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

try:
    from tqdm import tqdm

    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False

from llm_gc.bananas import add_bananas, celebrate, get_bananas
from llm_gc.metrics import log_metric
from llm_gc.orchestrator.m1_chat import run_task
from llm_gc.orchestrator.m3_patch import run_patch
from llm_gc.skill import parse_read_requests


@dataclass
class MinionTask:
    """A single task for a minion."""

    description: str
    kind: str = "task"  # "task", "patch", or "analyze"
    target: str | None = None
    context_files: list[str] = field(default_factory=list)
    repo_root: str = "."
    retries: int = 0
    max_retries: int = 2
    status: str = "pending"
    result: str | None = None
    error: str | None = None


def simplify_prompt(prompt: str, retry_count: int) -> str:
    """Make prompt simpler for retry attempts."""
    if retry_count == 0:
        return prompt

    if retry_count == 1:
        simple = prompt.replace("Please ", "").replace("Could you ", "")
        simple = simple.replace("I need you to ", "").replace("I want you to ", "")
        return f"SIMPLE TASK.\n{simple}\nOUTPUT ONLY THE RESULT."

    words = prompt.split()[:20]
    return f"DO THIS: {' '.join(words)}..."


async def run_minion_task(task: MinionTask) -> MinionTask:
    """Run a single minion task."""
    prompt = simplify_prompt(task.description, task.retries)
    start_time = time.time()

    try:
        if task.kind == "patch":
            result = await run_patch(
                task=prompt,
                repo_root=task.repo_root,
                read_requests=parse_read_requests(task.context_files),
                target_files=[task.target] if task.target else [],
            )
            task.result = str(result.get("patch_path", ""))
            task.status = "completed" if result.get("patch_path") else "empty"
        else:
            result = await run_task(
                task=prompt,
                repo_root=task.repo_root,
                read_requests=parse_read_requests(task.context_files),
            )
            task.result = result.get("summary", "")
            task.status = "completed"
    except Exception as e:
        task.error = str(e)
        task.status = "failed"

    duration_ms = int((time.time() - start_time) * 1000)
    log_metric(
        task_type="swarm",
        task_description=task.description,
        duration_ms=duration_ms,
        role="implementer",
        success=task.status == "completed",
        retries=task.retries,
        error=task.error,
        patch_applied=task.kind == "patch" and task.status == "completed",
    )

    return task


class Swarm:
    """Dispatch multiple minions in parallel."""

    def __init__(
        self,
        workers: int = 5,
        max_retries: int = 2,
        repo_root: str = ".",
        show_progress: bool = True,
    ):
        self.workers = workers
        self.max_retries = max_retries
        self.repo_root = repo_root
        self.show_progress = show_progress and TQDM_AVAILABLE
        self.tasks: list[MinionTask] = []
        self.completed: list[MinionTask] = []
        self.failed: list[MinionTask] = []

    def add_task(self, description: str, context_files: list[str] | None = None) -> None:
        """Add a single-shot task to the swarm."""
        self.tasks.append(
            MinionTask(
                description=description,
                kind="task",
                context_files=context_files or [],
                repo_root=self.repo_root,
                max_retries=self.max_retries,
            )
        )

    def add_patch(
        self,
        description: str,
        target: str,
        context_files: list[str] | None = None,
    ) -> None:
        """Add a patch task to the swarm."""
        self.tasks.append(
            MinionTask(
                description=description,
                kind="patch",
                target=target,
                context_files=context_files or [],
                repo_root=self.repo_root,
                max_retries=self.max_retries,
            )
        )

    def process_files(
        self,
        pattern: str,
        task: str,
        action: Literal["analyze", "patch"] = "analyze",
    ) -> None:
        """Add tasks for all files matching a glob pattern.

        Args:
            pattern: Glob pattern (e.g., "src/*.py", "**/*.ts")
            task: Task description (use {file} as placeholder)
            action: "analyze" for read-only, "patch" for modifications

        Example:
            swarm.process_files(
                pattern="src/**/*.py",
                task="Add type hints to {file}",
                action="patch"
            )
        """
        root = Path(self.repo_root)
        matches = list(root.glob(pattern))

        for file_path in matches:
            if file_path.is_file():
                rel_path = str(file_path.relative_to(root))
                file_task = task.replace("{file}", rel_path)

                if action == "patch":
                    self.add_patch(
                        description=file_task,
                        target=rel_path,
                        context_files=[rel_path],
                    )
                else:
                    self.add_task(
                        description=file_task,
                        context_files=[rel_path],
                    )

    async def run(self, on_progress: Callable[[str], None] | None = None) -> dict:
        """Execute all tasks in parallel with auto-retry.

        Returns:
            dict with completed, failed, and stats
        """
        pending = list(self.tasks)
        retry_queue: list[MinionTask] = []

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

        pbar = None
        if self.show_progress:
            pbar = tqdm(
                total=total,
                desc="🍌 Minions",
                unit="task",
                bar_format="{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
            )

        while pending or retry_queue:
            pending.extend(retry_queue)
            retry_queue = []

            if not pending:
                break

            # Run batch
            task_coroutines = [run_minion_task(task) for task in pending]
            results = await asyncio.gather(*task_coroutines, return_exceptions=True)
            pending = []

            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    task = self.tasks[i] if i < len(self.tasks) else MinionTask(description="unknown")
                    task.error = str(result)
                    task.status = "failed"
                else:
                    task = result

                if task.status == "completed":
                    self.completed.append(task)
                    completed_count += 1
                    if pbar:
                        pbar.update(1)
                        pbar.set_postfix_str(f"✓ {task.description[:25]}...")
                    else:
                        log(f"  🍌 Done: {task.description[:40]}...")
                elif task.status == "empty":
                    if task.retries < task.max_retries:
                        task.retries += 1
                        retry_queue.append(task)
                        retry_count += 1
                        if pbar:
                            pbar.set_postfix_str(f"↻ retry {task.retries}")
                        else:
                            log(f"  🔄 Retry {task.retries}: {task.description[:40]}...")
                    else:
                        self.failed.append(task)
                        failed_count += 1
                        if pbar:
                            pbar.update(1)
                            pbar.set_postfix_str("✗ empty")
                        else:
                            log(f"  ❌ Empty: {task.description[:40]}...")
                else:  # failed
                    if task.retries < task.max_retries:
                        task.retries += 1
                        retry_queue.append(task)
                        retry_count += 1
                        if pbar:
                            pbar.set_postfix_str(f"↻ retry {task.retries}")
                        else:
                            log(f"  🔄 Retry {task.retries}: {task.description[:40]}...")
                    else:
                        self.failed.append(task)
                        failed_count += 1
                        if pbar:
                            pbar.update(1)
                            pbar.set_postfix_str("✗ failed")
                        else:
                            log(f"  ❌ Failed: {task.description[:40]}...")

        if pbar:
            pbar.close()

        elapsed = time.time() - start_time

        if completed_count > 0:
            new_total = add_bananas(completed_count, task_type="swarm")
            log(f"\n{celebrate(completed_count)}")
            log(f"🍌 Total bananas: {new_total}")

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
                "bananas_earned": completed_count,
                "bananas_total": get_bananas(),
            },
        }


# Convenience function
async def process_files(
    pattern: str,
    task: str,
    action: Literal["analyze", "patch"] = "analyze",
    repo_root: str = ".",
    max_retries: int = 2,
) -> dict:
    """Process files matching a glob pattern in parallel.

    Args:
        pattern: Glob pattern (e.g., "src/*.py")
        task: Task description (use {file} as placeholder)
        action: "analyze" or "patch"
        repo_root: Repository root
        max_retries: Max retry attempts

    Returns:
        dict with completed, failed, stats
    """
    swarm = Swarm(repo_root=repo_root, max_retries=max_retries)
    swarm.process_files(pattern, task, action)
    return await swarm.run()


__all__ = ["MinionTask", "Swarm", "process_files", "simplify_prompt"]
