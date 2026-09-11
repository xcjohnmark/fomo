"""High-level Momentum Strategy Engine coordinating scoring, history analysis, and candidate detection."""

from typing import List, Optional, Union
from config.settings import Settings, get_settings
from models.domain import (
    AlertCandidate,
    ConfirmationState,
    MomentumAnalysis,
    ScoreTier,
    TokenSnapshot,
)
from strategy.classifier import SetupClassifier
from strategy.history_analyzer import HistoryAnalyzer
from strategy.scoring import MomentumScorer, get_score_tier


class MomentumStrategyEngine:
    """Evaluates normalized TokenSnapshot feeds and history against the Quick Flip / Momentum Strategy."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()

    def analyze(self, history: Union[TokenSnapshot, List[TokenSnapshot]]) -> MomentumAnalysis:
        """Analyze a TokenSnapshot or chronological snapshot history and return a complete MomentumAnalysis."""
        if isinstance(history, TokenSnapshot):
            history_list = [history]
        else:
            history_list = list(history)

        if not history_list:
            raise ValueError("Cannot analyze empty token snapshot history.")

        # 1. Analyze historical trends and multi-metric agreement
        trends = HistoryAnalyzer.analyze(history_list)
        current = sorted(history_list, key=lambda s: s.timestamp)[-1]

        # 2. Calculate 10-dimension deterministic score
        score_result = MomentumScorer.calculate_score(current, trends)
        score_tier = get_score_tier(score_result.score)

        # 3. Classify setup
        classification = SetupClassifier.classify(current, score_result, trends)

        # 4. Determine confirmation state (CONFIRMED, DEVELOPING, WEAKENING, INVALIDATED)
        setup_state = SetupClassifier.determine_confirmation_state(
            current, score_result, classification, trends
        )

        # 5. Extract 2-4 objective factual reasons and 2-4 objective factual warnings
        reasons, warnings = SetupClassifier.extract_reasons_and_risks(
            current, score_result, trends
        )

        # 6. Extract confirmation requirements, invalidation criteria, and next action
        (
            confirmation_needed,
            invalidation_conditions,
            next_action,
        ) = SetupClassifier.get_confirmation_and_invalidation(
            current, classification, setup_state, trends
        )

        return MomentumAnalysis(
            token_address=current.token_address,
            symbol=current.symbol,
            timestamp=current.timestamp,
            score=score_result.score,
            score_breakdown=score_result.breakdown.to_dict(),
            score_tier=score_tier,
            classification=classification,
            setup_state=setup_state,
            reasons=reasons,
            warnings=warnings,
            confirmation_needed=confirmation_needed,
            invalidation_conditions=invalidation_conditions,
            next_action=next_action,
            is_overextended=trends.is_overextended,
            raw_breakdown=score_result.breakdown,
        )

    def evaluate_token(self, token: TokenSnapshot) -> Optional[AlertCandidate]:
        """Evaluate a single TokenSnapshot and return an AlertCandidate if it qualifies."""
        # 1. Hard filters to prevent dangerous execution hazards
        if token.liquidity_usd is not None and token.liquidity_usd < self.settings.MIN_LIQUIDITY_USD:
            return None

        # 2. Run deterministic analysis
        analysis = self.analyze(token)

        # 3. Check threshold requirement (Section 29: >= 85 for immediate alert)
        if analysis.score < self.settings.MIN_MOMENTUM_SCORE:
            return None

        # 4. Reject invalidated or weakening setups
        if analysis.setup_state in (ConfirmationState.INVALIDATED, ConfirmationState.WEAKENING):
            return None

        # 5. Reconstruct ScoreResult for compatibility
        score_result = MomentumScorer.calculate_score(token)

        # 6. Formulate concise alert reason (Section 39)
        p5m = f"+{token.change_5m_pct:.1f}%" if token.change_5m_pct is not None else "N/A"
        flow = f"{token.buy_tx_ratio:.0f}% buy flow" if token.buy_tx_ratio is not None else "Flow N/A"
        breadth = f"{token.buyer_ratio:.0f}% buyer breadth" if token.buyer_ratio is not None else "Breadth N/A"
        alert_reason = f"5M price acceleration ({p5m}) with {flow} and {breadth}"

        # 7. Generate QuickFlipPlan
        from strategy.trade_planner import QuickFlipTradePlanner
        plan = QuickFlipTradePlanner.generate_plan(analysis, token)

        return AlertCandidate(
            token=token,
            score_result=score_result,
            classification=analysis.classification,
            confirmation_state=analysis.setup_state,
            alert_reason=alert_reason,
            reasons=analysis.reasons,
            risks=analysis.warnings,
            confirmation_needed="; ".join(analysis.confirmation_needed),
            invalidation_criteria="; ".join(analysis.invalidation_conditions),
            next_action=analysis.next_action,
            analysis=analysis,
            plan=plan,
        )

    def plan_trade(
        self, history: Union[TokenSnapshot, List[TokenSnapshot]]
    ) -> QuickFlipPlan:
        """Analyze setup and construct an actionable QuickFlipPlan."""
        from strategy.trade_planner import QuickFlipTradePlanner

        analysis = self.analyze(history)
        return QuickFlipTradePlanner.generate_plan(analysis, history)

    def evaluate_tokens(self, tokens: List[TokenSnapshot]) -> List[AlertCandidate]:
        """Evaluate a batch of active tokens and return all qualified candidates."""
        candidates: List[AlertCandidate] = []
        for token in tokens:
            candidate = self.evaluate_token(token)
            if candidate is not None:
                candidates.append(candidate)
        return candidates
