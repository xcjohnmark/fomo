"""High-level Momentum Strategy Engine coordinating scoring and candidate detection."""

from typing import List, Optional
from config.settings import Settings, get_settings
from models.domain import AlertCandidate, NormalizedTokenData
from strategy.classifier import SetupClassifier
from strategy.scoring import MomentumScorer


class MomentumStrategyEngine:
    """Evaluates normalized token feeds against the Quick Flip / Momentum Strategy."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()

    def evaluate_token(self, token: NormalizedTokenData) -> Optional[AlertCandidate]:
        """Evaluate a single token snapshot and return an AlertCandidate if it qualifies."""
        # 1. Hard filters to prevent dangerous execution hazards
        if token.liquidity < self.settings.MIN_LIQUIDITY_USD:
            return None

        # 2. Calculate 10-dimension deterministic score
        score_result = MomentumScorer.calculate_score(token)

        # 3. Check threshold requirement (Section 29: >= 85 for immediate alert)
        if score_result.score < self.settings.MIN_MOMENTUM_SCORE:
            return None

        # 4. Classify setup
        classification = SetupClassifier.classify(token, score_result)

        # 5. Extract reasons and risks (Rule 8)
        reasons, risks = SetupClassifier.extract_reasons_and_risks(token, score_result)

        # 6. Determine confirmation, invalidation, next action, and state
        (
            confirmation_needed,
            invalidation,
            next_action,
            conf_state,
        ) = SetupClassifier.get_confirmation_and_invalidation(token, classification)

        # 7. Formulate concise alert reason (Section 39)
        alert_reason = (
            f"5M price acceleration (+{token.change_5m:.1f}%) with "
            f"{token.buy_tx_ratio:.0f}% buy flow and {token.buyer_ratio:.0f}% buyer breadth"
        )

        return AlertCandidate(
            token=token,
            score_result=score_result,
            classification=classification,
            confirmation_state=conf_state,
            alert_reason=alert_reason,
            reasons=reasons,
            risks=risks,
            confirmation_needed=confirmation_needed,
            invalidation_criteria=invalidation,
            next_action=next_action,
        )

    def evaluate_tokens(self, tokens: List[NormalizedTokenData]) -> List[AlertCandidate]:
        """Evaluate a batch of active tokens and return all qualified candidates."""
        candidates: List[AlertCandidate] = []
        for token in tokens:
            candidate = self.evaluate_token(token)
            if candidate is not None:
                candidates.append(candidate)
        return candidates
