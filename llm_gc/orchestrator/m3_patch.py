"""Single-shot patch generator."""

from __future__ import annotations

import textwrap
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from llm_gc.config import load_models
from llm_gc.orchestrator.base import ChatTurn, OllamaClient, persist_transcript, render_turn
from llm_gc.parsers import FileChange, parse_file_blocks
from llm_gc.tools import (
    FileReader,
    FileReadRequest,
    RepoSummary,
    build_repo_summary,
)
from llm_gc.tools.repomap import RepoMap, build_repomap
from llm_gc.tools.diff_generator import FileDiff, generate_diff, generate_multi_diff


# Single-shot patcher system prompt
PATCHER_SYSTEM_PROMPT = """You are a coding minion making small code changes.

RULES:
- Make MINIMAL changes - only what's asked
- Output COMPLETE file in fenced block: ```path/to/file.py
- NO explanations, NO comments about changes
- Copy unchanged parts EXACTLY
- One file at a time
- Be concise
"""


@dataclass
class ContextSnippet:
    label: str
    content: str


class PatchExecutor:
    """Single-shot patch executor."""

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
        target_files: Sequence[str] | None = None,
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
        self.session_id = datetime.utcnow().strftime("%Y%m%d-%H%M%S-patch")
        self.target_files = [Path(f) for f in (target_files or [])]
        self._prepare_context(read_requests or [])

    async def run(self) -> dict:
        """Execute single-shot patch task and return result with diff."""
        # Get model config (use patcher role, fallback to implementer)
        config = self.models.get("patcher") or self.models.get("implementer")
        if not config:
            available = ", ".join(self.models.keys()) or "<empty>"
            raise KeyError(f"No 'patcher' or 'implementer' config found. Available: {available}")

        # Override model if specified
        if self.model_override:
            config = config.__class__(
                model=self.model_override,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
            )

        # Build prompt and execute
        prompt = self._build_prompt()
        content, latency_ms = await self.client.prompt(prompt, config, role="patcher")
        token_estimate = max(1, len(content.split()))

        turn = ChatTurn(
            role="Patcher",
            content=content,
            latency_ms=latency_ms,
            token_estimate=token_estimate,
            model=config.model,
            round_index=0,
        )
        render_turn(turn)

        # Parse file changes and generate diff
        file_changes = parse_file_blocks(content)
        file_diffs = self._build_diffs(file_changes)
        patch_text = generate_multi_diff(file_diffs)
        patch_path = self._write_patch_file(patch_text) if patch_text.strip() else None

        # Persist result
        metadata = {
            "task": self.task,
            "model": config.model,
            "session_id": self.session_id,
            "repo_root": str(self.repo_root),
            "context_files": [snippet.label for snippet in self.context_snippets],
            "target_files": [str(f) for f in self.target_files],
            "patched_files": [str(change.path) for change in file_changes],
        }
        if patch_path:
            metadata["patch_path"] = str(patch_path)

        transcript_path = persist_transcript(
            task=self.task,
            turns=[turn],
            summary=content,
            output_dir=self.session_dir,
            metadata=metadata,
        )

        return {
            "summary": content,
            "model": config.model,
            "latency_ms": latency_ms,
            "transcript_path": transcript_path,
            "patch_path": patch_path,
            "changes": file_changes,
            "diffs": file_diffs,
            "metadata": metadata,
        }

    def _build_prompt(self) -> str:
        repo_context = self._build_repo_context()
        target_instruction = ""
        if self.target_files:
            target_instruction = f"\nModify these files: {', '.join(str(p) for p in self.target_files)}"
        else:
            target_instruction = "\nIdentify which files must change and output them."

        return textwrap.dedent(
            f"""
            {PATCHER_SYSTEM_PROMPT}

            Task: {self.task}{target_instruction}

            Repository context:
            {repo_context}

            Execute the patch now. Output complete file contents in fenced code blocks.
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

    def _build_diffs(self, changes: Sequence[FileChange]) -> list[FileDiff]:
        diffs: list[FileDiff] = []
        for change in changes:
            original = self._read_original_file(change.path)
            diffs.append(generate_diff(original, change.content, change.path))
        return diffs

    def _read_original_file(self, relative_path: Path) -> str:
        path = (self.repo_root / relative_path).resolve()
        if not str(path).startswith(str(self.repo_root)):
            raise ValueError(f"Path escapes repo root: {relative_path}")
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def _write_patch_file(self, patch_text: str) -> Path:
        self.session_dir.mkdir(parents=True, exist_ok=True)
        patch_path = self.session_dir / f"{self.session_id}.patch"
        patch_path.write_text((patch_text or "").strip() + "\n")
        return patch_path


async def run_patch(
    *,
    task: str,
    model: str | None = None,
    preset: str | None = None,
    config_path: str | Path | None = None,
    session_dir: str | Path = "sessions",
    repo_root: str | Path | None = None,
    read_requests: Sequence[FileReadRequest] | None = None,
    target_files: Sequence[str] | None = None,
) -> dict:
    """Execute a single-shot patch task.

    Args:
        task: The patch task description
        model: Optional model override
        preset: Config preset (lite/medium/large)
        config_path: Path to models.yaml
        session_dir: Where to save transcripts and patches
        repo_root: Repository root directory
        read_requests: Files to include as context
        target_files: Files to patch (optional - minion can identify)

    Returns:
        dict with patch_path, changes, diffs, summary, model, latency_ms
    """
    executor = PatchExecutor(
        task=task,
        model=model,
        preset=preset,
        config_path=config_path,
        session_dir=session_dir,
        repo_root=repo_root,
        read_requests=read_requests,
        target_files=target_files,
    )
    return await executor.run()


__all__ = ["PATCHER_SYSTEM_PROMPT", "PatchExecutor", "run_patch"]
