"""Core types for Minions - Pydantic models for type safety.

Inspired by OpenAI Swarm's clean agent definitions.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal, Union

from pydantic import BaseModel, ConfigDict, Field

# Type alias for minion functions
MinionFunction = Callable[..., Union[str, "Minion", "MinionResult", dict]]


class Minion(BaseModel):
    """A specialized local LLM agent for code tasks.

    Roles:
        - implementer: Code generation, refactoring, tests
        - reviewer: Bug detection, security, correctness
        - patcher: Surgical edits, FIM, minimal diffs
        - judge: Evaluates proposals, selects best approach
    """

    name: str = "Minion"
    role: Literal["implementer", "reviewer", "patcher", "judge"] = "implementer"
    model: str = "qwen2.5-coder:7b"
    instructions: str | Callable[[], str] = "You are a helpful coding minion."
    fallback_models: list[str] = Field(default_factory=list)
    temperature: float = Field(0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(1024, gt=0)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def get_instructions(self) -> str:
        """Resolve instructions (may be callable)."""
        if callable(self.instructions):
            return self.instructions()
        return self.instructions


class MinionResult(BaseModel):
    """Encapsulates return value from a minion task.

    Enables agent handoff by returning next_minion.
    """

    value: str = ""
    next_minion: Minion | None = None  # Triggers handoff if set
    context: dict = Field(default_factory=dict)  # Passed to next minion

    model_config = ConfigDict(arbitrary_types_allowed=True)


class CodeReview(BaseModel):
    """Result from a reviewer minion."""

    summary: str
    issues: list[dict] = Field(default_factory=list)
    needs_fixes: bool = False
    severity: Literal["none", "low", "medium", "high", "critical"] = "none"


class PatchResult(BaseModel):
    """Result from a patcher minion."""

    patch_content: str = ""
    patch_path: str | None = None
    files_modified: list[str] = Field(default_factory=list)
    applied: bool = False
    strategy_used: str | None = None


class TaskContext(BaseModel):
    """Context passed between minions during handoff."""

    task: str
    repo_root: str = "."
    target_files: list[str] = Field(default_factory=list)
    file_contents: dict[str, str] = Field(default_factory=dict)
    history: list[dict] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


# Default minion configurations
IMPLEMENTER = Minion(
    name="Implementer",
    role="implementer",
    model="qwen2.5-coder:7b",
    instructions="You are a code implementer. Write clean, working code.",
    fallback_models=["qwen2.5-coder:7b"],
)

REVIEWER = Minion(
    name="Reviewer",
    role="reviewer",
    model="deepseek-coder:6.7b",
    instructions="You are a code reviewer. Find bugs, security issues, and edge cases.",
    fallback_models=["qwen2.5-coder:7b"],
    temperature=0.1,
)

PATCHER = Minion(
    name="Patcher",
    role="patcher",
    model="starcoder2:7b",
    instructions="You are a surgical code patcher. Make minimal, precise edits.",
    fallback_models=["qwen2.5-coder:7b"],
    temperature=0.1,
)

JUDGE = Minion(
    name="Judge",
    role="judge",
    model="qwen2.5-coder:7b",
    instructions=(
        "You are a code Judge. Evaluate proposals, score them against the quality rubric "
        "(correctness, minimal diff, tests, security, clarity), and select the best approach."
    ),
    fallback_models=["deepseek-coder:6.7b"],
    temperature=0.1,
)


__all__ = [
    "Minion",
    "MinionResult",
    "MinionFunction",
    "CodeReview",
    "PatchResult",
    "TaskContext",
    "IMPLEMENTER",
    "REVIEWER",
    "PATCHER",
    "JUDGE",
]
