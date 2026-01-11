"""Single-shot minion task execution - no rounds, no debate."""

from __future__ import annotations

import textwrap
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from llm_gc.config import load_models
from llm_gc.orchestrator.base import ChatTurn, OllamaClient, persist_transcript, render_turn
from llm_gc.tools import (
    FileReader,
    FileReadRequest,
    RepoSummary,
    build_repo_summary,
)
from llm_gc.tools.repomap import RepoMap, build_repomap


@dataclass
class ContextSnippet:
    label: str
    content: str


# Single minion system prompt - focused on task completion
MINION_SYSTEM_PROMPT = """You are a coding minion. Execute the task efficiently.

Rules:
- Be concise (under 200 words)
- If asked for code, output ONLY the code
- Focus on the task, nothing else
- End with a one-line summary of what you did
"""


class MinionExecutor:
    """Single-shot minion task executor."""

    def __init__(
        self,
        *,
        task: str,
        model: str | None = None,
        preset: str | None = None,
        config_path: str | Path | None = None,
        session_dir: str | Path = "sessions",
        repo_root: str | Path | None = None,
        read_requests: Sequence[FileReadRequest] | None = None,
        summary_chars: int = 4000,
    ) -> None:
        self.task = task
        self.preset = preset
        self.session_dir = Path(session_dir)
        self.models = load_models(config_path, preset=preset)
        self.model_override = model
        self.client = OllamaClient()
        self.repo_root = Path(repo_root or Path.cwd()).resolve()
        self.file_reader = FileReader(self.repo_root)
        self.repo_summary: RepoSummary | None = None
        self.repo_map: RepoMap | None = None
        self.summary_chars = summary_chars
        self.context_snippets: list[ContextSnippet] = []
        self.session_id = datetime.utcnow().strftime("%Y%m%d-%H%M%S-minion")
        self._prepare_context(read_requests or [])

    async def run(self) -> dict:
        """Execute single-shot task and return result."""
        # Get model config (use implementer by default)
        config = self.models.get("implementer")
        if not config:
            available = ", ".join(self.models.keys()) or "<empty>"
            raise KeyError(f"No 'implementer' config found. Available: {available}")

        # Override model if specified
        if self.model_override:
            config = config.__class__(
                model=self.model_override,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
            )

        # Build prompt and execute
        prompt = self._build_prompt()
        content, latency_ms = await self.client.prompt(prompt, config, role="implementer")
        token_estimate = max(1, len(content.split()))

        turn = ChatTurn(
            role="Minion",
            content=content,
            latency_ms=latency_ms,
            token_estimate=token_estimate,
            model=config.model,
            round_index=0,
        )
        render_turn(turn)

        # Persist result
        metadata = {
            "task": self.task,
            "model": config.model,
            "session_id": self.session_id,
            "repo_root": str(self.repo_root),
            "context_files": [snippet.label for snippet in self.context_snippets],
        }
        transcript_path = persist_transcript(
            task=self.task,
            turns=[turn],
            summary=content,
            output_dir=self.session_dir,
            metadata=metadata,
        )
        summary_path = self._write_repo_summary_file()

        return {
            "summary": content,
            "model": config.model,
            "latency_ms": latency_ms,
            "transcript_path": transcript_path,
            "summary_path": summary_path,
            "metadata": metadata,
        }

    def _build_prompt(self) -> str:
        repo_context = self._build_repo_context()
        return textwrap.dedent(
            f"""
            {MINION_SYSTEM_PROMPT}

            Task: {self.task}

            Repository context:
            {repo_context}

            Execute the task now.
            """
        ).strip()

    def _build_repo_context(self) -> str:
        sections: list[str] = []
        if self.repo_summary and self.repo_summary.text:
            sections.append(self.repo_summary.text)
        if self.repo_map and self.repo_map.symbols:
            sections.append("# Repo symbol map\n" + self.repo_map.as_text())
        for snippet in self.context_snippets:
            sections.append(f"{snippet.label}\n{snippet.content}")
        return "\n\n".join(sections) or "(no repo context)"

    def _prepare_context(self, read_requests: Sequence[FileReadRequest]) -> None:
        self.repo_summary = build_repo_summary(self.repo_root, max_chars=self.summary_chars)
        self.repo_map = build_repomap(self.repo_root)
        for request in read_requests:
            try:
                content = self.file_reader.read(request)
                label = f"Snippet: {request.describe()}"
            except Exception as exc:
                content = f"Error reading {request.path}: {exc}"
                label = f"Snippet error: {request.describe()}"
            self.context_snippets.append(ContextSnippet(label=label, content=content))

    def _write_repo_summary_file(self) -> Path:
        self.session_dir.mkdir(parents=True, exist_ok=True)
        path = self.session_dir / f"{self.session_id}-summary.txt"
        if self.repo_summary and self.repo_summary.text:
            path.write_text(self.repo_summary.text.strip() + "\n")
        else:
            path.write_text("(no summary available)\n")
        return path


async def run_task(
    *,
    task: str,
    model: str | None = None,
    preset: str | None = None,
    config_path: str | Path | None = None,
    session_dir: str | Path = "sessions",
    repo_root: str | Path | None = None,
    read_requests: Sequence[FileReadRequest] | None = None,
) -> dict:
    """Execute a single minion task.

    Args:
        task: The task description
        model: Optional model override
        preset: Config preset (lite/medium/large)
        config_path: Path to models.yaml
        session_dir: Where to save transcripts
        repo_root: Repository root directory
        read_requests: Files to include as context

    Returns:
        dict with summary, model, latency_ms, paths
    """
    executor = MinionExecutor(
        task=task,
        model=model,
        preset=preset,
        config_path=config_path,
        session_dir=session_dir,
        repo_root=repo_root,
        read_requests=read_requests,
    )
    return await executor.run()


# Backwards compatibility alias
async def run_chat(
    *,
    task: str,
    rounds: int = 1,  # Ignored - kept for API compatibility
    preset: str | None = None,
    config_path: str | Path | None = None,
    session_dir: str | Path = "sessions",
    repo_root: str | Path | None = None,
    read_requests: Sequence[FileReadRequest] | None = None,
) -> dict:
    """Backwards-compatible wrapper for run_task."""
    return await run_task(
        task=task,
        preset=preset,
        config_path=config_path,
        session_dir=session_dir,
        repo_root=repo_root,
        read_requests=read_requests,
    )


__all__ = [
    "ContextSnippet",
    "MinionExecutor",
    "MINION_SYSTEM_PROMPT",
    "run_task",
    "run_chat",
]
