"""Unit tests for setup classification and risk/reason extraction."""

import pytest
from models.domain import NormalizedTokenData, SetupClassification
from strategy.classifier import SetupClassifier
from strategy.scoring import MomentumScorer


def test_classify_continuation(sample_strong_token: NormalizedTokenData):
    """Verify strong token is classified as Continuation or Breakout."""
    score_result = MomentumScorer.calculate_score(sample_strong_token)
    classification = SetupClassifier.classify(sample_strong_token, score_result)
    assert classification in (SetupClassification.CONTINUATION, SetupClassification.BREAKOUT)


def test_classify_exhaustion(sample_strong_token: NormalizedTokenData):
    """Verify extreme historical pump with collapsing 5m/1h is classified as Exhaustion."""
    token = sample_strong_token.model_copy(
        update={
            "change_24h": 600.0,
            "change_4h": 200.0,
            "change_1h": -15.0,
            "change_5m": -8.0,
        }
    )
    score_result = MomentumScorer.calculate_score(token)
    classification = SetupClassifier.classify(token, score_result)
    assert classification == SetupClassification.EXHAUSTION


def test_reasons_and_risks_extracted(sample_strong_token: NormalizedTokenData):
    """Verify 2-4 objective reasons and 2-4 objective risks are extracted."""
    score_result = MomentumScorer.calculate_score(sample_strong_token)
    reasons, risks = SetupClassifier.extract_reasons_and_risks(sample_strong_token, score_result)

    assert 2 <= len(reasons) <= 4
    assert 2 <= len(risks) <= 4

    # High concentration should trigger a risk item
    concentrated_token = sample_strong_token.model_copy(update={"top10_percentage": 55.0})
    _, conc_risks = SetupClassifier.extract_reasons_and_risks(concentrated_token, score_result)
    assert any("Concentration risk" in r for r in conc_risks)
