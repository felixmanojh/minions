"""Minimal Implementer/Reviewer chat loop for Milestone M1."""

from __future__ import annotations

import textwrap
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
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
class AgentSpec:
    name: str
    config_key: str
    system_message: str
    response_limit: int = 200


@dataclass
class ContextSnippet:
    label: str
    content: str


DEFAULT_AGENTS = [
    AgentSpec(
        name="Implementer",
        config_key="implementer",
        system_message=(
            "You are a junior developer. Keep responses SHORT (under 150 words).\n"
            "- List 2-3 bullet points max\n"
            "- Focus on ONE thing at a time\n"
            "- If asked for code, output ONLY the code, no explanations\n"
            "- Don't overthink - just do the simple, obvious thing"
        ),
    ),
    AgentSpec(
        name="Reviewer",
        config_key="reviewer",
        system_message=(
            "You are a code reviewer. Keep responses SHORT (under 100 words).\n"
            "- Point out 1-2 issues max\n"
            "- Be specific: line numbers, exact problems\n"
            "- Say 'LGTM' if no issues\n"
            "- Don't suggest improvements unless there's a bug"
        ),
    ),
]


class ChatOrchestrator:
    """Runs sequential turns between configured agents."""

    def __init__(
        self,
        *,
        task: str,
        rounds: int = 3,
        preset: str | None = None,
        config_path: str | Path | None = None,
        session_dir: str | Path = "sessions",
        agents: Iterable[AgentSpec] | None = None,
        repo_root: str | Path | None = None,
        read_requests: Sequence[FileReadRequest] | None = None,
        summary_chars: int = 4000,
    ) -> None:
        if rounds < 1:
            raise ValueError("rounds must be >= 1")
        self.task = task
        self.rounds = rounds
        self.preset = preset
        self.session_dir = Path(session_dir)
        self.agents = list(agents or DEFAULT_AGENTS)
        self.models = load_models(config_path, preset=preset)
        self.client = OllamaClient()
        self.repo_root = Path(repo_root or Path.cwd()).resolve()
        self.file_reader = FileReader(self.repo_root)
        self.repo_summary: RepoSummary | None = None
        self.repo_map: RepoMap | None = None
        self.summary_chars = summary_chars
        self.context_snippets: list[ContextSnippet] = []
        self.session_id = datetime.utcnow().strftime("%Y%m%d-%H%M%S-m2")
        self._prepare_context(read_requests or [])

    def run(self) -> dict:
        """Execute the chat loop and persist transcript."""

        history: list[ChatTurn] = []
        for round_index in range(self.rounds):
            for agent in self.agents:
                turn = self._produce_turn(agent, history, round_index)
                history.append(turn)
                render_turn(turn)
        summary = history[-1].content if history else ""
        metadata = {
            "task": self.task,
            "rounds": self.rounds,
            "agents": [asdict(agent) for agent in self.agents],
            "session_id": self.session_id,
            "repo_root": str(self.repo_root),
            "context_files": [snippet.label for snippet in self.context_snippets],
            "repo_summary_sources": (self.repo_summary.sources if self.repo_summary else {}),
            "symbol_count": len(self.repo_map.symbols) if self.repo_map else 0,
        }
        transcript_path = persist_transcript(
            task=self.task,
            turns=history,
            summary=summary,
            output_dir=self.session_dir,
            metadata=metadata,
        )
        summary_path = self._write_repo_summary_file()
        return {
            "summary": summary,
            "turns": history,
            "transcript_path": transcript_path,
            "summary_path": summary_path,
            "metadata": metadata,
        }

    def _produce_turn(
        self,
        agent: AgentSpec,
        history: list[ChatTurn],
        round_index: int,
    ) -> ChatTurn:
        config = self.models.get(agent.config_key)
        if not config:
            available = ", ".join(self.models.keys()) or "<empty>"
            raise KeyError(f"Config '{agent.config_key}' missing. Available: {available}")
        prompt = self._build_prompt(agent, history, round_index)
        content, latency_ms = self.client.generate(prompt, config)
        token_estimate = max(1, len(content.split()))
        return ChatTurn(
            role=agent.name,
            content=content,
            latency_ms=latency_ms,
            token_estimate=token_estimate,
            model=config.model,
            round_index=round_index,
        )

    def _build_prompt(self, agent: AgentSpec, history: list[ChatTurn], round_index: int) -> str:
        context = "\n".join(f"{turn.role}: {turn.content}" for turn in history[-6:])
        if not context:
            context = "(conversation has not started)"
        repo_context = self._build_repo_context()
        return textwrap.dedent(
            f"""
            You are {agent.name}.
            {agent.system_message}

            Primary task: {self.task}

            Repository context:
            {repo_context}

            Previous conversation:
            {context}

            Instructions:
            - respond in <= {agent.response_limit} tokens
            - do not execute commands or modify files
            - focus on reasoning and clarity
            - end with a short action summary line
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
            except Exception as exc:  # pragma: no cover - surface errors to LLMs
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


def run_chat(
    *,
    task: str,
    rounds: int = 3,
    preset: str | None = None,
    config_path: str | Path | None = None,
    session_dir: str | Path = "sessions",
    repo_root: str | Path | None = None,
    read_requests: Sequence[FileReadRequest] | None = None,
) -> dict:
    orchestrator = ChatOrchestrator(
        task=task,
        rounds=rounds,
        preset=preset,
        config_path=config_path,
        session_dir=session_dir,
        repo_root=repo_root,
        read_requests=read_requests,
    )
    return orchestrator.run()


__all__ = [
    "AgentSpec",
    "ChatOrchestrator",
    "ContextSnippet",
    "DEFAULT_AGENTS",
    "run_chat",
]
