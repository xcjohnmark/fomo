"""Formats alert candidates into the Section 67 Agent Output Standard."""

from models.domain import AlertCandidate


def format_telegram_alert(candidate: AlertCandidate) -> str:
    """Format an alert candidate matching Section 67 specification."""
    token = candidate.token
    score = candidate.score_result.score

    why_lines = "\n".join(f"• {reason}" for reason in candidate.reasons)
    risks_lines = "\n".join(f"• {risk}" for risk in candidate.risks)

    message = (
        "========================================\n"
        "🚨 MOMENTUM SETUP DETECTED\n"
        "========================================\n\n"
        f"COIN: ${token.token}\n"
        f"MINT: {token.token_address}\n"
        f"AGE: {token.age}\n\n"
        "MARKET:\n"
        f"MC: ${token.market_cap:,.0f}\n"
        f"PRICE: ${token.price:.8f}\n"
        f"LIQUIDITY: ${token.liquidity:,.0f} ({token.liquidity_ratio:.1f}%)\n\n"
        "MOMENTUM:\n"
        f"5M: {'+' if token.change_5m > 0 else ''}{token.change_5m:.1f}%\n"
        f"1H: {'+' if token.change_1h > 0 else ''}{token.change_1h:.1f}%\n"
        f"4H: {'+' if token.change_4h > 0 else ''}{token.change_4h:.1f}%\n"
        f"24H: {'+' if token.change_24h > 0 else ''}{token.change_24h:.1f}%\n\n"
        "VOLUME:\n"
        f"5M: ${token.volume_5m:,.0f}\n"
        f"1H: ${token.volume_1h:,.0f}\n"
        f"24H: ${token.volume_24h:,.0f}\n\n"
        "FLOW:\n"
        f"BUYS: {token.buys}\n"
        f"SELLS: {token.sells}\n"
        f"BUYERS: {token.buyers}\n"
        f"SELLERS: {token.sellers}\n\n"
        "PARTICIPATION:\n"
        f"HOLDERS: {token.holders:,}\n"
        f"TOP 10%: {token.top10_percentage:.1f}%\n\n"
        f"TRADER ACTIVITY: {token.trader_activity}\n"
        f"NARRATIVE: {token.narrative}\n\n"
        f"MOMENTUM SCORE: {score:.0f}/100\n\n"
        f"CLASSIFICATION:\n{candidate.classification.value}\n\n"
        f"STATUS:\n{candidate.confirmation_state.value}\n\n"
        "WHY:\n"
        f"{why_lines}\n\n"
        "RISKS:\n"
        f"{risks_lines}\n\n"
        "CONFIRMATION NEEDED:\n"
        f"{candidate.confirmation_needed}\n\n"
        "INVALIDATION:\n"
        f"{candidate.invalidation_criteria}\n\n"
        "NEXT ACTION:\n"
        f"{candidate.next_action}\n"
        "========================================"
    )

    return message
