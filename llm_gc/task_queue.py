"""File-backed task queue for delegating chat/patch runs."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Literal
import json
import uuid
from datetime import datetime

from llm_gc.orchestrator.m1_chat import run_chat
from llm_gc.orchestrator.m3_patch import run_patch
from llm_gc.skill import parse_read_requests


def _run_task_worker(task_dict: dict) -> dict:
    """Worker function for parallel execution (must be top-level for pickling)."""
    task = Task(**task_dict)
    try:
        if task.kind == "chat":
            result = run_chat(
                task=task.description,
                rounds=task.rounds,
                repo_root=task.repo_root,
                read_requests=parse_read_requests(task.read_requests),
            )
            task.summary = result.get("summary", "")
            task.result_path = str(result.get("transcript_path"))
        else:
            result = run_patch(
                task=task.description,
                rounds=task.rounds,
                repo_root=task.repo_root,
                read_requests=parse_read_requests(task.read_requests),
                target_files=task.targets,
            )
            task.summary = result.get("summary", "")
            task.result_path = str(result.get("patch_path"))
        task.status = "completed"
    except Exception as exc:
        task.status = "failed"
        task.error = str(exc)
    return asdict(task)

TaskKind = Literal["chat", "patch"]
TaskStatus = Literal["pending", "running", "completed", "failed"]


@dataclass
class Task:
    id: str
    kind: TaskKind
    description: str
    repo_root: str
    rounds: int
    read_requests: List[str] = field(default_factory=list)
    targets: List[str] = field(default_factory=list)  # patch only
    status: TaskStatus = "pending"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    result_path: str | None = None
    summary: str | None = None
    error: str | None = None


class TaskQueue:
    def __init__(self, path: str | Path = Path("sessions/task_queue.json")) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.tasks: List[Task] = []
        self._load()

    def enqueue_chat(
        self,
        *,
        description: str,
        repo_root: Path,
        rounds: int = 3,
        read_requests: Iterable[str] = (),
    ) -> Task:
        task = Task(
            id=str(uuid.uuid4()),
            kind="chat",
            description=description,
            repo_root=str(repo_root),
            rounds=rounds,
            read_requests=list(read_requests),
        )
        self.tasks.append(task)
        self._persist()
        return task

    def enqueue_patch(
        self,
        *,
        description: str,
        repo_root: Path,
        rounds: int = 4,
        read_requests: Iterable[str] = (),
        targets: Iterable[str] = (),
    ) -> Task:
        task = Task(
            id=str(uuid.uuid4()),
            kind="patch",
            description=description,
            repo_root=str(repo_root),
            rounds=rounds,
            read_requests=list(read_requests),
            targets=list(targets),
        )
        self.tasks.append(task)
        self._persist()
        return task

    def list_tasks(self) -> List[Task]:
        return list(self.tasks)

    def run_next(self) -> Task | None:
        pending = next((task for task in self.tasks if task.status == "pending"), None)
        if not pending:
            return None
        pending.status = "running"
        self._persist()
        try:
            if pending.kind == "chat":
                result = run_chat(
                    task=pending.description,
                    rounds=pending.rounds,
                    repo_root=pending.repo_root,
                    read_requests=parse_read_requests(pending.read_requests),
                )
                pending.summary = result.get("summary", "")
                pending.result_path = str(result.get("transcript_path"))
            else:
                result = run_patch(
                    task=pending.description,
                    rounds=pending.rounds,
                    repo_root=pending.repo_root,
                    read_requests=parse_read_requests(pending.read_requests),
                    target_files=pending.targets,
                )
                pending.summary = result.get("summary", "")
                pending.result_path = str(result.get("patch_path"))
            pending.status = "completed"
        except Exception as exc:  # pragma: no cover - runtime safety
            pending.status = "failed"
            pending.error = str(exc)
        finally:
            self._persist()
        return pending

    def run_parallel(self, max_workers: int = 3) -> List[Task]:
        """Run all pending tasks in parallel.

        Args:
            max_workers: Maximum number of concurrent tasks (default 3)

        Returns:
            List of completed/failed tasks
        """
        pending = [task for task in self.tasks if task.status == "pending"]
        if not pending:
            return []

        # Mark all as running
        for task in pending:
            task.status = "running"
        self._persist()

        # Run in parallel
        results: List[Task] = []
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            future_to_task = {
                executor.submit(_run_task_worker, asdict(task)): task
                for task in pending
            }
            for future in as_completed(future_to_task):
                original_task = future_to_task[future]
                try:
                    result_dict = future.result()
                    # Update original task with results
                    original_task.status = result_dict["status"]
                    original_task.summary = result_dict.get("summary")
                    original_task.result_path = result_dict.get("result_path")
                    original_task.error = result_dict.get("error")
                except Exception as exc:
                    original_task.status = "failed"
                    original_task.error = str(exc)
                results.append(original_task)
                self._persist()

        return results

    def _load(self) -> None:
        if not self.path.exists():
            self.tasks = []
            return
        data = json.loads(self.path.read_text() or "[]")
        self.tasks = [Task(**entry) for entry in data]

    def _persist(self) -> None:
        data = [asdict(task) for task in self.tasks]
        self.path.write_text(json.dumps(data, indent=2) + "\n")


__all__ = ["Task", "TaskQueue"]
