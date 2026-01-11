"""Judge agent for Minions - selects best approach and scores quality.

The Judge synthesizes proposals from other minions and scores them
against a quality rubric. Enables early stopping on consensus.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from llm_gc.metrics import log_metric


class QualityCriterion(str, Enum):
    """Quality criteria for scoring proposals."""

    CORRECTNESS = "correctness"  # Does it solve the problem?
    MINIMAL_DIFF = "minimal_diff"  # Is the change minimal?
    TESTS = "tests"  # Are tests added/updated?
    SECURITY = "security"  # No new security risks?
    CLARITY = "clarity"  # Clear and reproducible?


# Weights for each criterion (must sum to 1.0)
DEFAULT_WEIGHTS = {
    QualityCriterion.CORRECTNESS: 0.35,
    QualityCriterion.MINIMAL_DIFF: 0.20,
    QualityCriterion.TESTS: 0.15,
    QualityCriterion.SECURITY: 0.15,
    QualityCriterion.CLARITY: 0.15,
}


class CriterionScore(BaseModel):
    """Score for a single quality criterion."""

    criterion: QualityCriterion
    score: float = Field(ge=0.0, le=1.0)  # 0-1 score
    reasoning: str = ""
    weight: float = Field(default=0.2, ge=0.0, le=1.0)


class ProposalScore(BaseModel):
    """Complete scoring for a proposal."""

    proposal_id: str
    source_minion: str
    criteria_scores: list[CriterionScore] = Field(default_factory=list)
    total_score: float = Field(default=0.0, ge=0.0, le=1.0)
    rank: int = 0
    selected: bool = False
    feedback: str = ""

    def compute_total(self) -> float:
        """Compute weighted total score."""
        if not self.criteria_scores:
            return 0.0
        total = sum(cs.score * cs.weight for cs in self.criteria_scores)
        self.total_score = min(1.0, total)
        return self.total_score


class JudgmentResult(BaseModel):
    """Result from Judge evaluation."""

    proposals: list[ProposalScore] = Field(default_factory=list)
    selected_proposal: str | None = None
    consensus_reached: bool = False
    consensus_strength: float = Field(default=0.0, ge=0.0, le=1.0)
    final_recommendation: str = ""
    risk_notes: list[str] = Field(default_factory=list)
    test_plan: list[str] = Field(default_factory=list)
    early_stop: bool = False
    rounds_used: int = 0


@dataclass
class ConsensusDetector:
    """Detects consensus among proposals for early stopping."""

    threshold: float = 0.85  # Agreement threshold for consensus
    min_proposals: int = 2  # Minimum proposals to consider
    score_gap: float = 0.15  # Gap between top and others for clear winner

    def check_consensus(self, scores: list[ProposalScore]) -> tuple[bool, float]:
        """Check if proposals have reached consensus.

        Args:
            scores: List of scored proposals

        Returns:
            (consensus_reached, consensus_strength)
        """
        if len(scores) < self.min_proposals:
            return False, 0.0

        # Sort by total score descending
        sorted_scores = sorted(scores, key=lambda x: x.total_score, reverse=True)

        # Check if top proposal is clearly better
        top_score = sorted_scores[0].total_score
        second_score = sorted_scores[1].total_score if len(sorted_scores) > 1 else 0.0

        # Clear winner if gap is large enough
        if top_score - second_score >= self.score_gap:
            strength = min(1.0, (top_score - second_score) / self.score_gap)
            return True, strength

        # Check if all proposals agree (high scores, small variance)
        avg_score = sum(s.total_score for s in sorted_scores) / len(sorted_scores)
        if avg_score >= self.threshold:
            # High agreement - all proposals are good
            variance = sum((s.total_score - avg_score) ** 2 for s in sorted_scores) / len(sorted_scores)
            if variance < 0.05:  # Low variance
                return True, avg_score

        return False, 0.0


@dataclass
class QualityRubric:
    """Scoring rubric for evaluating proposals."""

    weights: dict[QualityCriterion, float] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))

    def __post_init__(self):
        # Normalize weights to sum to 1.0
        total = sum(self.weights.values())
        if total > 0:
            self.weights = {k: v / total for k, v in self.weights.items()}

    def score_proposal(
        self,
        proposal: str,
        original_task: str,
        context: dict | None = None,
    ) -> ProposalScore:
        """Score a proposal against the rubric.

        This is a heuristic scorer - in practice, the LLM Judge
        would provide these scores based on analysis.

        Args:
            proposal: The proposal text/code
            original_task: The original task description
            context: Additional context (files, tests, etc.)

        Returns:
            ProposalScore with criterion scores
        """
        context = context or {}
        criteria_scores = []

        for criterion, weight in self.weights.items():
            score = self._score_criterion(criterion, proposal, original_task, context)
            criteria_scores.append(CriterionScore(
                criterion=criterion,
                score=score,
                weight=weight,
                reasoning=f"Heuristic score for {criterion.value}",
            ))

        proposal_score = ProposalScore(
            proposal_id=f"prop_{hash(proposal) % 10000}",
            source_minion="unknown",
            criteria_scores=criteria_scores,
        )
        proposal_score.compute_total()
        return proposal_score

    def _score_criterion(
        self,
        criterion: QualityCriterion,
        proposal: str,
        task: str,
        context: dict,
    ) -> float:
        """Heuristic scoring for a single criterion."""
        proposal_lower = proposal.lower()

        if criterion == QualityCriterion.CORRECTNESS:
            # Check if proposal addresses the task
            task_words = set(task.lower().split())
            proposal_words = set(proposal_lower.split())
            overlap = len(task_words & proposal_words) / max(len(task_words), 1)
            return min(1.0, overlap * 2)  # Scale up

        elif criterion == QualityCriterion.MINIMAL_DIFF:
            # Shorter proposals (relative to task) are more minimal
            ratio = len(proposal) / max(len(task) * 10, 1)
            return max(0.0, 1.0 - min(ratio, 1.0))

        elif criterion == QualityCriterion.TESTS:
            # Check for test-related content
            test_keywords = ["test", "assert", "expect", "should", "verify"]
            has_tests = any(kw in proposal_lower for kw in test_keywords)
            return 0.8 if has_tests else 0.3

        elif criterion == QualityCriterion.SECURITY:
            # Check for security red flags
            security_risks = ["eval(", "exec(", "shell=true", "password", "secret"]
            has_risks = any(risk in proposal_lower for risk in security_risks)
            return 0.2 if has_risks else 0.9

        elif criterion == QualityCriterion.CLARITY:
            # Check for explanation/comments
            has_explanation = "```" in proposal or "#" in proposal or "//" in proposal
            return 0.8 if has_explanation else 0.5

        return 0.5  # Default


@dataclass
class Judge:
    """Judge agent that evaluates and selects proposals."""

    rubric: QualityRubric = field(default_factory=QualityRubric)
    consensus_detector: ConsensusDetector = field(default_factory=ConsensusDetector)
    max_rounds: int = 5
    current_round: int = 0

    def evaluate(
        self,
        proposals: list[dict],
        task: str,
        context: dict | None = None,
    ) -> JudgmentResult:
        """Evaluate proposals and select the best one.

        Args:
            proposals: List of {content: str, source: str} dicts
            task: Original task description
            context: Additional context

        Returns:
            JudgmentResult with selected proposal and scores
        """
        start_time = time.time()
        self.current_round += 1
        context = context or {}

        # Score each proposal
        scored_proposals = []
        for i, prop in enumerate(proposals):
            content = prop.get("content", str(prop))
            source = prop.get("source", f"minion_{i}")

            score = self.rubric.score_proposal(content, task, context)
            score.proposal_id = f"prop_{i}"
            score.source_minion = source
            scored_proposals.append(score)

        # Rank proposals
        sorted_proposals = sorted(
            scored_proposals,
            key=lambda x: x.total_score,
            reverse=True,
        )
        for rank, prop in enumerate(sorted_proposals):
            prop.rank = rank + 1

        # Check for consensus
        consensus, strength = self.consensus_detector.check_consensus(sorted_proposals)

        # Select best proposal
        selected = sorted_proposals[0] if sorted_proposals else None
        if selected:
            selected.selected = True

        # Determine if we should stop early
        early_stop = consensus or self.current_round >= self.max_rounds

        # Build result
        result = JudgmentResult(
            proposals=sorted_proposals,
            selected_proposal=selected.proposal_id if selected else None,
            consensus_reached=consensus,
            consensus_strength=strength,
            early_stop=early_stop,
            rounds_used=self.current_round,
        )

        # Add recommendation
        if selected:
            result.final_recommendation = self._build_recommendation(selected, sorted_proposals)
            result.risk_notes = self._extract_risks(sorted_proposals)
            result.test_plan = self._build_test_plan(selected, task)

        # Log judge metrics
        duration_ms = int((time.time() - start_time) * 1000)
        log_metric(
            task_type="judge",
            task_description=task[:100],
            duration_ms=duration_ms,
            role="judge",
            success=selected is not None,
            judge_score=selected.total_score if selected else None,
        )

        return result

    def _build_recommendation(
        self,
        selected: ProposalScore,
        all_proposals: list[ProposalScore],
    ) -> str:
        """Build final recommendation text."""
        lines = [
            f"Selected proposal from {selected.source_minion}",
            f"Score: {selected.total_score:.2f}",
        ]

        # Add criterion breakdown
        for cs in selected.criteria_scores:
            lines.append(f"  - {cs.criterion.value}: {cs.score:.2f}")

        if len(all_proposals) > 1:
            runner_up = all_proposals[1]
            lines.append(f"Runner-up: {runner_up.source_minion} ({runner_up.total_score:.2f})")

        return "\n".join(lines)

    def _extract_risks(self, proposals: list[ProposalScore]) -> list[str]:
        """Extract risk notes from proposals."""
        risks = []
        for prop in proposals:
            for cs in prop.criteria_scores:
                if cs.criterion == QualityCriterion.SECURITY and cs.score < 0.5:
                    risks.append(f"Security concern in {prop.source_minion}: {cs.reasoning}")
        return risks

    def _build_test_plan(self, selected: ProposalScore, task: str) -> list[str]:
        """Build a test plan for the selected proposal."""
        return [
            f"Verify: {task[:100]}",
            "Run existing tests",
            "Check for regressions",
            "Manual review of changes",
        ]

    def should_continue(self) -> bool:
        """Check if judging should continue."""
        return self.current_round < self.max_rounds


# Prompt templates for LLM-based judging
JUDGE_SYSTEM_PROMPT = """You are a code Judge. Your job is to:
1. Evaluate proposals from other agents
2. Score them against the quality rubric
3. Select the best approach
4. Provide constructive feedback

Quality Rubric (in order of importance):
- Correctness (35%): Does it solve the problem correctly?
- Minimal Diff (20%): Is the change as small as possible?
- Tests (15%): Are tests added or updated?
- Security (15%): Are there any security risks?
- Clarity (15%): Is the solution clear and reproducible?

End your response with:
SELECTED: <proposal_id>
SCORE: <0-100>
CONSENSUS: <yes/no>
"""

JUDGE_EVALUATION_PROMPT = """Task: {task}

Proposals to evaluate:
{proposals}

Previous feedback (if any):
{feedback}

Evaluate each proposal and select the best one.
"""


__all__ = [
    "Judge",
    "JudgmentResult",
    "ProposalScore",
    "CriterionScore",
    "QualityCriterion",
    "QualityRubric",
    "ConsensusDetector",
    "DEFAULT_WEIGHTS",
    "JUDGE_SYSTEM_PROMPT",
    "JUDGE_EVALUATION_PROMPT",
]
