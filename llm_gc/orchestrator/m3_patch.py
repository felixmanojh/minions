"""Patch-focused orchestrator (Milestone M3)."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from dataclasses import dataclass

from llm_gc.orchestrator.base import ChatTurn
from llm_gc.orchestrator.m1_chat import (
    AgentSpec,
    ChatOrchestrator,
)
from llm_gc.parsers import FileChange, parse_file_blocks
from llm_gc.tools import FileReadRequest
from llm_gc.tools.diff_generator import FileDiff, generate_diff, generate_multi_diff

PATCH_AGENTS = [
    AgentSpec(
        name="Implementer",
        config_key="implementer",
        system_message=(
            "You are a junior developer making small code changes.\n"
            "RULES:\n"
            "- Make MINIMAL changes - only what's asked\n"
            "- Output COMPLETE file in fenced block: ```path/to/file.py\n"
            "- NO explanations, NO comments about changes\n"
            "- Copy unchanged parts EXACTLY\n"
            "- One file at a time"
        ),
    ),
    AgentSpec(
        name="Reviewer",
        config_key="reviewer",
        system_message=(
            "You review code changes. Keep it SHORT (under 50 words).\n"
            "- Check: syntax errors, typos, missing brackets\n"
            "- Say 'LGTM' if code looks correct\n"
            "- Only flag BUGS, not style preferences"
        ),
    ),
]


NEGATIVE_REVIEW_KEYWORDS = [
    "bug",
    "error",
    "fails",
    "failing",
    "issue",
    "missing",
    "breaks",
    "wrong",
    "not ready",
    "reject",
]

POSITIVE_REVIEW_KEYWORDS = ["lgtm", "looks good", "ship it", "approved", "good to go"]


@dataclass
class ReviewVerdict:
    approved: bool
    reason: str


class PatchOrchestrator(ChatOrchestrator):
    """Extends ChatOrchestrator to capture final file contents and produce a diff."""

    def __init__(
        self,
        *,
        task: str,
        rounds: int = 4,
        preset: str | None = None,
        config_path: str | Path | None = None,
        session_dir: str | Path = "sessions",
        repo_root: str | Path | None = None,
        read_requests: Sequence[FileReadRequest] | None = None,
        target_files: Sequence[str] | None = None,
    ) -> None:
        super().__init__(
            task=task,
            rounds=rounds,
            preset=preset,
            config_path=config_path,
            session_dir=session_dir,
            agents=PATCH_AGENTS,
            repo_root=repo_root,
            read_requests=read_requests,
        )
        self.target_files = [Path(f) for f in (target_files or [])]
        self.require_target_selection = not self.target_files

    async def run(self) -> dict:
        result = await super().run()
        turns: list[ChatTurn] = result.get("turns", [])
        reviewer_turn = self._latest_reviewer_turn(turns)
        verdict = self._analyze_review(reviewer_turn)

        metadata = result.get("metadata", {})
        metadata["review_verdict"] = {
            "approved": verdict.approved,
            "reason": verdict.reason,
        }

        if not verdict.approved:
            metadata["status"] = "rejected_by_reviewer"
            return {
                **result,
                "patch_path": None,
                "changes": [],
                "diffs": [],
                "metadata": metadata,
            }

        implementer_turn = self._latest_implementer_turn(turns)
        file_changes = parse_file_blocks(implementer_turn.content if implementer_turn else "")
        file_diffs = self._build_diffs(file_changes)
        patch_text = generate_multi_diff(file_diffs)
        patch_path = self._write_patch_file(patch_text)

        metadata["patched_files"] = [str(change.path) for change in file_changes]
        metadata["patch_path"] = str(patch_path)

        return {
            **result,
            "patch_path": patch_path,
            "changes": file_changes,
            "diffs": file_diffs,
            "metadata": metadata,
        }

    def _build_prompt(self, agent: AgentSpec, history: list[ChatTurn], round_index: int) -> str:
        prompt = super()._build_prompt(agent, history, round_index)
        additions: list[str] = []
        if agent.name == "Implementer":
            if self.target_files:
                additions.append(
                    "Modify these files: " + ", ".join(str(path) for path in self.target_files)
                )
            elif round_index == 0:
                additions.append(
                    "No target files were provided. Identify which files must change"
                    " before you begin coding and clearly list them."
                )
            if round_index == self.rounds - 1:
                additions.append(
                    "THIS IS THE FINAL ROUND. Output the complete modified files"
                    " using the fenced format for each file."
                )
        elif agent.name == "Reviewer" and round_index == self.rounds - 1:
            additions.append(
                "THIS IS THE FINAL REVIEW. Focus on bugs or blocking issues in the provided code."
            )

        if additions:
            prompt = f"{prompt}\n\nAdditional instructions:\n- " + "\n- ".join(additions)
        return prompt

    def _latest_implementer_turn(self, turns: list[ChatTurn]) -> ChatTurn | None:
        for turn in reversed(turns):
            if turn.role == "Implementer":
                return turn
        return None

    def _latest_reviewer_turn(self, turns: list[ChatTurn]) -> ChatTurn | None:
        for turn in reversed(turns):
            if turn.role == "Reviewer":
                return turn
        return None

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

    def _analyze_review(self, reviewer_turn: ChatTurn | None) -> ReviewVerdict:
        if not reviewer_turn:
            return ReviewVerdict(approved=False, reason="No reviewer response")
        text = reviewer_turn.content.lower()
        if any(keyword in text for keyword in NEGATIVE_REVIEW_KEYWORDS):
            return ReviewVerdict(approved=False, reason=reviewer_turn.content.strip())
        if any(keyword in text for keyword in POSITIVE_REVIEW_KEYWORDS):
            return ReviewVerdict(approved=True, reason=reviewer_turn.content.strip())
        # Default to rejection if reviewer didn't explicitly approve
        return ReviewVerdict(approved=False, reason="Reviewer did not approve (missing LGTM)")


async def run_patch(
    *,
    task: str,
    rounds: int = 4,
    preset: str | None = None,
    config_path: str | Path | None = None,
    session_dir: str | Path = "sessions",
    repo_root: str | Path | None = None,
    read_requests: Sequence[FileReadRequest] | None = None,
    target_files: Sequence[str] | None = None,
) -> dict:
    orchestrator = PatchOrchestrator(
        task=task,
        rounds=rounds,
        preset=preset,
        config_path=config_path,
        session_dir=session_dir,
        repo_root=repo_root,
        read_requests=read_requests,
        target_files=target_files,
    )
    return await orchestrator.run()


__all__ = ["PATCH_AGENTS", "PatchOrchestrator", "run_patch"]
