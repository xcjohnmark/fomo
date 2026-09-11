"""Unit tests for setup classification and risk/reason extraction."""

import pytest
from models.domain import SetupClassification, TokenSnapshot
from strategy.classifier import SetupClassifier
from strategy.scoring import MomentumScorer


def test_classify_continuation(sample_strong_token: TokenSnapshot):
    """Verify strong token is classified as Continuation or Breakout."""
    score_result = MomentumScorer.calculate_score(sample_strong_token)
    classification = SetupClassifier.classify(sample_strong_token, score_result)
    assert classification in (SetupClassification.CONTINUATION, SetupClassification.BREAKOUT)


def test_classify_exhaustion(sample_strong_token: TokenSnapshot):
    """Verify extreme historical pump with collapsing 5m/1h is classified as Exhaustion."""
    token = sample_strong_token.model_copy(
        update={
            "change_24h_pct": 600.0,
            "change_4h_pct": 200.0,
            "change_1h_pct": -15.0,
            "change_5m_pct": -8.0,
        }
    )
    score_result = MomentumScorer.calculate_score(token)
    classification = SetupClassifier.classify(token, score_result)
    assert classification == SetupClassification.EXHAUSTION


def test_reasons_and_risks_extracted(sample_strong_token: TokenSnapshot):
    """Verify 2-4 objective reasons and 2-4 objective risks are extracted."""
    score_result = MomentumScorer.calculate_score(sample_strong_token)
    reasons, risks = SetupClassifier.extract_reasons_and_risks(sample_strong_token, score_result)

    assert 2 <= len(reasons) <= 4
    assert 2 <= len(risks) <= 4

    # High concentration should trigger a risk item
    concentrated_token = sample_strong_token.model_copy(update={"top10_holder_pct": 55.0})
    _, conc_risks = SetupClassifier.extract_reasons_and_risks(concentrated_token, score_result)
    assert any("Concentration risk" in r for r in conc_risks)


def test_missing_metrics_noted_in_risks(sample_strong_token: TokenSnapshot):
    """Verify missing data is explicitly called out in risks (Rule 8)."""
    token = sample_strong_token.model_copy(update={"top10_holder_pct": None})
    score_result = MomentumScorer.calculate_score(token)
    _, risks = SetupClassifier.extract_reasons_and_risks(token, score_result)
    assert any("top 10 holder concentration is UNAVAILABLE" in r for r in risks)
