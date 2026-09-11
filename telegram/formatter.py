"""Formats alert candidates into the Section 67 Agent Output Standard."""

from models.domain import AlertCandidate


def format_telegram_alert(candidate: AlertCandidate) -> str:
    """Format an alert candidate matching Section 67 specification.

    Strict Rule: If a metric is None, represent it as N/A or UNKNOWN.
    Never display fake or estimated numbers.
    """
    token = candidate.token
    score = candidate.score_result.score

    # Format helpers
    def fmt_pct(val):
        if val is None:
            return "N/A"
        return f"{'+' if val > 0 else ''}{val:.1f}%"

    def fmt_usd(val):
        if val is None:
            return "N/A"
        return f"${val:,.0f}"

    def fmt_price(val):
        if val is None:
            return "N/A"
        return f"${val:.8f}"

    def fmt_val(val, default="UNKNOWN"):
        if val is None:
            return default
        return str(val)

    why_lines = "\n".join(f"• {reason}" for reason in candidate.reasons)
    risks_lines = "\n".join(f"• {risk}" for risk in candidate.risks)

    liq_ratio_str = f" ({token.liquidity_ratio:.1f}%)" if token.liquidity_ratio is not None else ""

    message = (
        "========================================\n"
        "🚨 MOMENTUM SETUP DETECTED\n"
        "========================================\n\n"
        f"COIN: ${token.symbol or 'UNKNOWN'}\n"
        f"MINT: {token.token_address}\n"
        f"SOURCE: {token.provider_source}\n"
        f"AGE: {token.token_age_formatted or 'UNKNOWN'}\n\n"
        "MARKET:\n"
        f"MC: {fmt_usd(token.market_cap_usd)}\n"
        f"PRICE: {fmt_price(token.price_usd)}\n"
        f"LIQUIDITY: {fmt_usd(token.liquidity_usd)}{liq_ratio_str}\n\n"
        "MOMENTUM:\n"
        f"5M: {fmt_pct(token.change_5m_pct)}\n"
        f"1H: {fmt_pct(token.change_1h_pct)}\n"
        f"4H: {fmt_pct(token.change_4h_pct)}\n"
        f"24H: {fmt_pct(token.change_24h_pct)}\n\n"
        "VOLUME:\n"
        f"5M: {fmt_usd(token.volume_5m_usd)}\n"
        f"1H: {fmt_usd(token.volume_1h_usd)}\n"
        f"24H: {fmt_usd(token.volume_24h_usd)}\n\n"
        "FLOW:\n"
        f"BUYS: {fmt_val(token.buys, 'N/A')}\n"
        f"SELLS: {fmt_val(token.sells, 'N/A')}\n"
        f"BUYERS: {fmt_val(token.buyers, 'N/A')}\n"
        f"SELLERS: {fmt_val(token.sellers, 'N/A')}\n\n"
        "PARTICIPATION:\n"
        f"HOLDERS: {fmt_val(token.holders_count, 'N/A')}\n"
        f"TOP 10%: {fmt_pct(token.top10_holder_pct)}\n\n"
        f"TRADER ACTIVITY: {token.trader_activity_summary or 'UNKNOWN'}\n"
        f"NARRATIVE: {token.narrative or 'UNKNOWN'}\n\n"
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
