"""Agent handoff pattern for Minions.

Inspired by OpenAI Swarm's agent handoff mechanism.
Enables automatic transitions: Reviewer → Patcher, Implementer → Reviewer, etc.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from llm_gc.types import (
    IMPLEMENTER,
    PATCHER,
    REVIEWER,
    CodeReview,
    Minion,
    MinionResult,
    TaskContext,
)


class HandoffRouter:
    """Routes results to appropriate next minion based on outcome."""

    def __init__(self):
        self._rules: list[tuple[Callable[[Any], bool], Minion]] = []
        self._default_rules()

    def _default_rules(self) -> None:
        """Set up default handoff rules."""
        # Review with issues → Patcher
        self.add_rule(
            lambda r: isinstance(r, CodeReview) and r.needs_fixes,
            PATCHER,
        )

        # Review with critical issues → Implementer (needs rewrite)
        self.add_rule(
            lambda r: isinstance(r, CodeReview) and r.severity == "critical",
            IMPLEMENTER,
        )

    def add_rule(
        self,
        condition: Callable[[Any], bool],
        target_minion: Minion,
    ) -> None:
        """Add a handoff rule.

        Args:
            condition: Function that returns True if handoff should occur
            target_minion: Minion to hand off to
        """
        self._rules.append((condition, target_minion))

    def route(self, result: Any) -> Minion | None:
        """Determine which minion should handle the result.

        Args:
            result: Result from current minion

        Returns:
            Next minion or None if no handoff needed
        """
        for condition, target in self._rules:
            try:
                if condition(result):
                    return target
            except Exception:
                continue

        return None


def handle_minion_result(
    result: Any,
    router: HandoffRouter | None = None,
) -> MinionResult:
    """Process a minion result and determine next steps.

    Args:
        result: Raw result from minion execution
        router: Optional custom handoff router

    Returns:
        MinionResult with optional next_minion for handoff
    """
    if router is None:
        router = HandoffRouter()

    # Already a MinionResult - check for handoff
    if isinstance(result, MinionResult):
        if result.next_minion is None:
            # Try to determine handoff from value
            next_minion = router.route(result.value)
            if next_minion:
                result.next_minion = next_minion
        return result

    # CodeReview - check if needs fixes
    if isinstance(result, CodeReview):
        next_minion = router.route(result)
        return MinionResult(
            value=result.summary,
            next_minion=next_minion,
            context={
                "issues": list(result.issues),
                "severity": result.severity,
            },
        )

    # Minion returned directly - handoff
    if isinstance(result, Minion):
        return MinionResult(
            value=f"Handing off to {result.name}",
            next_minion=result,
        )

    # Dict result
    if isinstance(result, dict):
        return MinionResult(
            value=str(result.get("summary", result.get("value", str(result)))),
            context=result,
        )

    # String or other
    return MinionResult(value=str(result))


class MinionPipeline:
    """Execute a sequence of minions with automatic handoffs."""

    def __init__(
        self,
        minions: list[Minion] | None = None,
        max_handoffs: int = 5,
    ):
        """Initialize pipeline.

        Args:
            minions: Initial minion sequence (optional)
            max_handoffs: Maximum automatic handoffs to prevent loops
        """
        self.minions = minions or []
        self.max_handoffs = max_handoffs
        self.router = HandoffRouter()
        self.history: list[MinionResult] = []

    def add(self, minion: Minion) -> MinionPipeline:
        """Add a minion to the pipeline."""
        self.minions.append(minion)
        return self

    def run(
        self,
        task: str,
        context: TaskContext | None = None,
        execute_fn: Callable[[Minion, str, TaskContext], Any] | None = None,
    ) -> list[MinionResult]:
        """Execute the pipeline.

        Args:
            task: Task description
            context: Initial context
            execute_fn: Function to execute a minion (minion, task, context) -> result

        Returns:
            List of results from each minion
        """
        if context is None:
            context = TaskContext(task=task)

        if execute_fn is None:
            # Default: just return the task as value
            def execute_fn(m: Minion, t: str, _c: TaskContext) -> str:
                return f"{m.name} processed: {t}"

        results: list[MinionResult] = []
        current_minions = list(self.minions)
        handoff_count = 0

        while current_minions and handoff_count < self.max_handoffs:
            minion = current_minions.pop(0)

            # Execute minion
            raw_result = execute_fn(minion, task, context)

            # Process result
            result = handle_minion_result(raw_result, self.router)
            results.append(result)

            # Update context with result
            context.history.append(
                {
                    "minion": minion.name,
                    "role": minion.role,
                    "result": result.value,
                }
            )
            context.metadata.update(result.context)

            # Check for handoff
            if result.next_minion:
                current_minions.insert(0, result.next_minion)
                handoff_count += 1
                task = f"Continue from previous: {result.value[:200]}"

        self.history = results
        return results


# Convenience functions for common patterns
def review_then_patch(
    task: str,
    context: TaskContext | None = None,
    execute_fn: Callable[[Minion, str, TaskContext], Any] | None = None,
) -> list[MinionResult]:
    """Run Reviewer → Patcher pipeline."""
    pipeline = MinionPipeline([REVIEWER, PATCHER])
    return pipeline.run(task, context, execute_fn)


def implement_review_patch(
    task: str,
    context: TaskContext | None = None,
    execute_fn: Callable[[Minion, str, TaskContext], Any] | None = None,
) -> list[MinionResult]:
    """Run full pipeline: Implementer → Reviewer → Patcher."""
    pipeline = MinionPipeline([IMPLEMENTER, REVIEWER, PATCHER])
    return pipeline.run(task, context, execute_fn)


__all__ = [
    "HandoffRouter",
    "MinionPipeline",
    "handle_minion_result",
    "review_then_patch",
    "implement_review_patch",
]
