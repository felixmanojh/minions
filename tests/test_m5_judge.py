"""Tests for M5: Judge agent and quality scoring."""

import pytest

from llm_gc.judge import (
    ConsensusDetector,
    CriterionScore,
    Judge,
    JudgmentResult,
    ProposalScore,
    QualityCriterion,
    QualityRubric,
)
from llm_gc.types import JUDGE, Minion


# ─────────────────────────────────────────────────────────────
# Judge Type Tests
# ─────────────────────────────────────────────────────────────


class TestJudgeType:
    """Test JUDGE minion type."""

    def test_judge_role(self):
        assert JUDGE.role == "judge"

    def test_judge_name(self):
        assert JUDGE.name == "Judge"

    def test_judge_temperature(self):
        assert JUDGE.temperature == 0.1

    def test_judge_instructions(self):
        assert "quality rubric" in JUDGE.instructions.lower()

    def test_create_custom_judge(self):
        judge = Minion(
            name="CustomJudge",
            role="judge",
            model="custom-model",
        )
        assert judge.role == "judge"


# ─────────────────────────────────────────────────────────────
# Quality Rubric Tests
# ─────────────────────────────────────────────────────────────


class TestQualityRubric:
    """Test quality scoring rubric."""

    def test_default_weights_sum_to_one(self):
        rubric = QualityRubric()
        total = sum(rubric.weights.values())
        assert abs(total - 1.0) < 0.01

    def test_score_proposal_returns_score(self):
        rubric = QualityRubric()
        score = rubric.score_proposal(
            proposal="def fix(): return 42",
            original_task="fix the function",
        )
        assert isinstance(score, ProposalScore)
        assert 0 <= score.total_score <= 1

    def test_score_has_all_criteria(self):
        rubric = QualityRubric()
        score = rubric.score_proposal(
            proposal="def fix(): pass",
            original_task="fix bug",
        )
        criteria = {cs.criterion for cs in score.criteria_scores}
        assert QualityCriterion.CORRECTNESS in criteria
        assert QualityCriterion.MINIMAL_DIFF in criteria
        assert QualityCriterion.TESTS in criteria
        assert QualityCriterion.SECURITY in criteria
        assert QualityCriterion.CLARITY in criteria

    def test_tests_keyword_boosts_score(self):
        rubric = QualityRubric()

        with_tests = rubric.score_proposal(
            proposal="def fix(): pass\ndef test_fix(): assert fix() is None",
            original_task="fix bug",
        )

        without_tests = rubric.score_proposal(
            proposal="def fix(): pass",
            original_task="fix bug",
        )

        # Find test criterion scores
        with_test_score = next(
            cs.score for cs in with_tests.criteria_scores
            if cs.criterion == QualityCriterion.TESTS
        )
        without_test_score = next(
            cs.score for cs in without_tests.criteria_scores
            if cs.criterion == QualityCriterion.TESTS
        )

        assert with_test_score > without_test_score

    def test_security_risk_lowers_score(self):
        rubric = QualityRubric()

        safe = rubric.score_proposal(
            proposal="def fix(): return 42",
            original_task="fix bug",
        )

        risky = rubric.score_proposal(
            proposal="def fix(): eval(user_input)",
            original_task="fix bug",
        )

        safe_security = next(
            cs.score for cs in safe.criteria_scores
            if cs.criterion == QualityCriterion.SECURITY
        )
        risky_security = next(
            cs.score for cs in risky.criteria_scores
            if cs.criterion == QualityCriterion.SECURITY
        )

        assert safe_security > risky_security


# ─────────────────────────────────────────────────────────────
# Consensus Detection Tests
# ─────────────────────────────────────────────────────────────


class TestConsensusDetector:
    """Test consensus detection for early stopping."""

    def test_no_consensus_with_one_proposal(self):
        detector = ConsensusDetector()
        scores = [
            ProposalScore(proposal_id="1", source_minion="A", total_score=0.9)
        ]
        consensus, strength = detector.check_consensus(scores)
        assert not consensus

    def test_consensus_with_clear_winner(self):
        detector = ConsensusDetector(score_gap=0.15)
        scores = [
            ProposalScore(proposal_id="1", source_minion="A", total_score=0.9),
            ProposalScore(proposal_id="2", source_minion="B", total_score=0.6),
        ]
        consensus, strength = detector.check_consensus(scores)
        assert consensus
        assert strength > 0

    def test_no_consensus_when_close(self):
        detector = ConsensusDetector(score_gap=0.15)
        scores = [
            ProposalScore(proposal_id="1", source_minion="A", total_score=0.8),
            ProposalScore(proposal_id="2", source_minion="B", total_score=0.75),
        ]
        consensus, _ = detector.check_consensus(scores)
        assert not consensus

    def test_consensus_when_all_high(self):
        detector = ConsensusDetector(threshold=0.85)
        scores = [
            ProposalScore(proposal_id="1", source_minion="A", total_score=0.9),
            ProposalScore(proposal_id="2", source_minion="B", total_score=0.88),
            ProposalScore(proposal_id="3", source_minion="C", total_score=0.87),
        ]
        consensus, strength = detector.check_consensus(scores)
        # All scores above threshold with low variance
        assert consensus or strength > 0.8


# ─────────────────────────────────────────────────────────────
# Judge Evaluation Tests
# ─────────────────────────────────────────────────────────────


class TestJudge:
    """Test Judge evaluation."""

    def test_evaluate_selects_best(self):
        judge = Judge()
        proposals = [
            {"content": "def fix(): return 42", "source": "Implementer"},
            {"content": "x = 1", "source": "Patcher"},
        ]
        result = judge.evaluate(proposals, task="fix the function")

        assert isinstance(result, JudgmentResult)
        assert result.selected_proposal is not None
        assert len(result.proposals) == 2

    def test_evaluate_ranks_proposals(self):
        judge = Judge()
        proposals = [
            {"content": "def fix(): return 42  # fixes the bug", "source": "A"},
            {"content": "pass", "source": "B"},
            {"content": "def fix(): pass  # test", "source": "C"},
        ]
        result = judge.evaluate(proposals, task="fix the function")

        ranks = [p.rank for p in result.proposals]
        assert 1 in ranks
        assert 2 in ranks
        assert 3 in ranks

    def test_early_stop_on_max_rounds(self):
        judge = Judge(max_rounds=2)

        # First round
        judge.evaluate([{"content": "a", "source": "A"}], task="task")
        assert judge.should_continue()

        # Second round
        result = judge.evaluate([{"content": "b", "source": "B"}], task="task")
        assert result.early_stop

    def test_final_recommendation_includes_score(self):
        judge = Judge()
        proposals = [
            {"content": "def fix(): return 42", "source": "Implementer"},
        ]
        result = judge.evaluate(proposals, task="fix")

        assert "Score:" in result.final_recommendation
        assert "Implementer" in result.final_recommendation

    def test_test_plan_generated(self):
        judge = Judge()
        proposals = [{"content": "fix code", "source": "A"}]
        result = judge.evaluate(proposals, task="fix the bug")

        assert len(result.test_plan) > 0
        assert any("test" in item.lower() for item in result.test_plan)


# ─────────────────────────────────────────────────────────────
# Proposal Score Tests
# ─────────────────────────────────────────────────────────────


class TestProposalScore:
    """Test ProposalScore model."""

    def test_compute_total(self):
        score = ProposalScore(
            proposal_id="1",
            source_minion="A",
            criteria_scores=[
                CriterionScore(
                    criterion=QualityCriterion.CORRECTNESS,
                    score=0.8,
                    weight=0.5,
                ),
                CriterionScore(
                    criterion=QualityCriterion.TESTS,
                    score=0.6,
                    weight=0.5,
                ),
            ],
        )
        total = score.compute_total()
        assert abs(total - 0.7) < 0.01  # (0.8 * 0.5) + (0.6 * 0.5)

    def test_empty_scores_zero_total(self):
        score = ProposalScore(proposal_id="1", source_minion="A")
        total = score.compute_total()
        assert total == 0.0

    def test_selected_default_false(self):
        score = ProposalScore(proposal_id="1", source_minion="A")
        assert not score.selected


# ─────────────────────────────────────────────────────────────
# Criterion Score Tests
# ─────────────────────────────────────────────────────────────


class TestCriterionScore:
    """Test CriterionScore model."""

    def test_score_bounds(self):
        # Valid scores
        cs = CriterionScore(
            criterion=QualityCriterion.CORRECTNESS,
            score=0.5,
        )
        assert cs.score == 0.5

    def test_all_criteria_values(self):
        criteria = list(QualityCriterion)
        assert len(criteria) == 5
        assert QualityCriterion.CORRECTNESS in criteria
        assert QualityCriterion.MINIMAL_DIFF in criteria
