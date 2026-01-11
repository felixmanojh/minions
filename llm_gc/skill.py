"""Programmatic entry points for external assistants (Claude/Codex)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from llm_gc.orchestrator.m1_chat import run_chat
from llm_gc.tools import FileReadRequest


@dataclass
class ChatSkillRequest:
    """Parameters to run a chat session as a tool call."""

    task: str
    rounds: int = 3
    repo_root: Path = Path.cwd()
    read_requests: Sequence[FileReadRequest] | None = None
    config_path: Path | None = None
    session_dir: Path = Path("sessions")


@dataclass
class ChatSkillResult:
    summary: str
    transcript_path: Path
    summary_path: Path | None
    metadata: dict


def run_chat_skill(params: ChatSkillRequest) -> ChatSkillResult:
    """Execute the chat orchestrator and return structured results.

    External assistants (Claude/Codex) can import this function, pass a
    `ChatSkillRequest`, and receive stable metadata suitable for tool outputs.
    """

    result = run_chat(
        task=params.task,
        rounds=params.rounds,
        config_path=params.config_path,
        session_dir=params.session_dir,
        repo_root=params.repo_root,
        read_requests=params.read_requests,
    )
    return ChatSkillResult(
        summary=result.get("summary", ""),
        transcript_path=Path(result["transcript_path"]),
        summary_path=Path(result["summary_path"]) if result.get("summary_path") else None,
        metadata=result.get("metadata", {}),
    )


def parse_read_requests(raw_values: Iterable[str]) -> list[FileReadRequest]:
    """Utility for parsing PATH[:START-END] strings into FileReadRequest objects."""

    requests: list[FileReadRequest] = []
    for value in raw_values:
        if not value:
            continue
        path, _, range_part = value.partition(":")
        start = end = None
        if range_part:
            start_str, _, end_str = range_part.partition("-")
            try:
                start = int(start_str) if start_str else None
                end = int(end_str) if end_str else None
            except ValueError as exc:
                raise ValueError(f"Invalid range '{range_part}' for read request '{value}'") from exc
        requests.append(FileReadRequest(path=path, start=start, end=end))
    return requests


__all__ = [
    "ChatSkillRequest",
    "ChatSkillResult",
    "parse_read_requests",
    "run_chat_skill",
]
