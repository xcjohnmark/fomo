"""Formats alert candidates and bot command responses strictly adhering to Section 13 standards."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from models.domain import AlertCandidate, ConfirmationState, QuickFlipPlan


def fmt_compact_usd(val: Optional[float]) -> str:
    """Format USD currency compactly (e.g. $180K, $1.5M, $450)."""
    if val is None:
        return "N/A"
    abs_val = abs(val)
    if abs_val >= 1_000_000_000:
        return f"${val / 1_000_000_000:.1f}B"
    if abs_val >= 1_000_000:
        return f"${val / 1_000_000:.1f}M"
    if abs_val >= 1_000:
        return f"${val / 1_000:.0f}K"
    return f"${val:,.0f}"


def fmt_price(val: Optional[float]) -> str:
    """Format unit token price with high decimal precision."""
    if val is None:
        return "N/A"
    if val < 0.00001:
        return f"${val:.8f}"
    if val < 0.01:
        return f"${val:.6f}"
    return f"${val:.4f}"


def fmt_pct(val: Optional[float]) -> str:
    """Format percentage with explicit +/- sign."""
    if val is None:
        return "N/A"
    sign = "+" if val > 0 else ""
    return f"{sign}{val:.1f}%"


def fmt_val(val: Any, default: str = "N/A") -> str:
    """Format generic integer or string metric safely without inventing data."""
    if val is None:
        return default
    return str(val)


def format_telegram_alert(
    candidate: AlertCandidate, plan: Optional[QuickFlipPlan] = None
) -> str:
    """Format an alert candidate into the standardized Section 13 Quick Flip Setup template."""
    token = candidate.token
    trade_plan = plan or candidate.plan
    score = candidate.score_result.score

    # Coin symbol & CA
    symbol = token.symbol or "UNKNOWN"
    ca = token.token_address

    # Confirmation Status
    status_str = candidate.confirmation_state.value
    if candidate.confirmation_state == ConfirmationState.CONFIRMED:
        status_str = "CONFIRMED"

    # Core Metrics
    mc_str = fmt_compact_usd(token.market_cap_usd)
    liq_str = fmt_compact_usd(token.liquidity_usd)
    p5m = fmt_pct(token.change_5m_pct)
    p1h = fmt_pct(token.change_1h_pct)
    p4h = fmt_pct(token.change_4h_pct)

    # Volume State
    vol_state = "ACCELERATING"
    if token.volume_5m_usd and token.volume_1h_usd:
        expected_5m = token.volume_1h_usd / 12.0
        if token.volume_5m_usd > expected_5m * 1.5:
            vol_state = "ACCELERATING"
        elif token.volume_5m_usd > expected_5m:
            vol_state = "EXPANDING"
        else:
            vol_state = "NORMAL"

    # Participation & Flow
    buyers_str = fmt_val(token.buyers)
    sellers_str = fmt_val(token.sellers)
    buys_str = fmt_val(token.buys)
    sells_str = fmt_val(token.sells)

    # Entry Zone
    if trade_plan and trade_plan.entry_zone and token.market_cap_usd and trade_plan.entry_price:
        ratio_low = trade_plan.entry_zone.low / trade_plan.entry_price
        ratio_high = trade_plan.entry_zone.high / trade_plan.entry_price
        entry_mc_low = token.market_cap_usd * ratio_low
        entry_mc_high = token.market_cap_usd * ratio_high
        entry_zone_str = f"{fmt_compact_usd(entry_mc_low)}–{fmt_compact_usd(entry_mc_high)} MC"
    elif token.market_cap_usd:
        entry_zone_str = f"{fmt_compact_usd(token.market_cap_usd * 0.98)}–{fmt_compact_usd(token.market_cap_usd * 1.02)} MC"
    else:
        entry_zone_str = "Market Spot / Structure Level"

    # Target Zone & Potential
    if trade_plan and trade_plan.target_market_cap:
        target_mc_low = trade_plan.target_market_cap * 0.95
        target_mc_high = trade_plan.target_market_cap * 1.10
        target_str = f"{fmt_compact_usd(target_mc_low)}–{fmt_compact_usd(target_mc_high)} MC"
        pot_low = (trade_plan.target_percentage or 20.0) * 0.8
        pot_high = (trade_plan.target_percentage or 35.0) * 1.2
        potential_str = f"Potential: +{pot_low:.0f}% to +{pot_high:.0f}%"
    elif token.market_cap_usd:
        target_str = f"{fmt_compact_usd(token.market_cap_usd * 1.2)}–{fmt_compact_usd(token.market_cap_usd * 1.5)} MC"
        potential_str = "Potential: +20% to +50%"
    else:
        target_str = "Structure Expansion Zone"
        potential_str = "Potential: +15% to +35%"

    # Invalidation Level
    if trade_plan and trade_plan.invalidation_market_cap:
        invalidation_str = f"Below {fmt_compact_usd(trade_plan.invalidation_market_cap)} MC"
    elif token.market_cap_usd:
        invalidation_str = f"Below {fmt_compact_usd(token.market_cap_usd * 0.92)} MC"
    else:
        invalidation_str = "Below local 5M swing base"

    # Expected Hold
    if trade_plan and trade_plan.expected_holding_minutes:
        hold_low = max(10, trade_plan.expected_holding_minutes - 10)
        hold_high = trade_plan.expected_holding_minutes + 25
        hold_str = f"{hold_low}–{hold_high} min"
    else:
        hold_str = "15–45 min"

    # Why Rationale (2-5 factual bullets)
    reasons = candidate.reasons or [
        "5M momentum accelerating",
        "Volume expanding",
        "Buyers dominating sellers",
        "Liquidity acceptable",
        "Participation increasing",
    ]
    why_lines = "\n".join(f"• {r}" for r in reasons[:5])

    # Risks (2-4 factual bullets)
    risks = candidate.risks or [
        "High short-term volatility",
        f"Top-holder concentration: {fmt_pct(token.top10_holder_pct)}",
        "Setup becomes weaker if volume collapses",
    ]
    risks_lines = "\n".join(f"• {r}" for r in risks[:4])

    # Plan
    plan_lines = (
        "Quick momentum flip.\n"
        "Not a long-term hold.\n"
        "Take profit into strength."
    )

    message = (
        "⚡ QUICK FLIP SETUP\n\n"
        f"${symbol}\n"
        f"CA: {ca}\n\n"
        f"Momentum Score: {score:.0f}/100\n"
        f"Status: {status_str}\n\n"
        f"MC: {mc_str}\n"
        f"Liquidity: {liq_str}\n"
        f"5M: {p5m}\n"
        f"1H: {p1h}\n"
        f"4H: {p4h}\n\n"
        f"Volume: {vol_state}\n"
        f"Buyers/Sellers: {buyers_str} / {sellers_str}\n"
        f"Buys/Sells: {buys_str} / {sells_str}\n\n"
        "ENTRY ZONE\n"
        f"{entry_zone_str}\n\n"
        "TARGET\n"
        f"{target_str}\n"
        f"{potential_str}\n\n"
        "INVALIDATION\n"
        f"{invalidation_str}\n\n"
        "EXPECTED HOLD\n"
        f"{hold_str}\n\n"
        "WHY\n"
        f"{why_lines}\n\n"
        "RISKS\n"
        f"{risks_lines}\n\n"
        "PLAN\n"
        f"{plan_lines}"
    )

    return message


def format_status_message(status: Dict[str, Any]) -> str:
    """Format /status command system health and operational metrics."""
    db_state = "CONNECTED" if status.get("database_connected") else "DISCONNECTED"
    collector_state = "ACTIVE" if status.get("collector_healthy") else "DEGRADED"
    notifier_state = "ACTIVE" if status.get("telegram_configured") else "DRY-RUN"
    paused = "PAUSED" if status.get("alerts_paused") else "ACTIVE"

    return (
        "📊 SYSTEM OPERATIONAL STATUS\n"
        "============================\n"
        f"• Database: {db_state}\n"
        f"• Data Feed: {collector_state} ({status.get('provider_source', 'mock')})\n"
        f"• Dispatcher: {notifier_state}\n"
        f"• Alerts State: {paused}\n"
        f"• Min Score Cutoff: {status.get('min_score', 85)}/100\n"
        f"• Min Liquidity: {fmt_compact_usd(status.get('min_liquidity', 10000))}\n"
        f"• Watched Tokens: {status.get('watchlist_count', 0)}\n"
        f"• Open Paper Trades: {status.get('open_paper_trades', 0)}\n"
        f"• System Uptime: {status.get('uptime', 'Active')}\n"
        "============================"
    )


def format_scan_summary(candidates: List[AlertCandidate]) -> str:
    """Format on-demand /scan command output."""
    if not candidates:
        return (
            "🔍 SCAN COMPLETED\n\n"
            "No tokens currently meet the momentum and liquidity threshold (Score >= 85, Liquidity >= $10K).\n"
            "The system remains in monitoring mode."
        )

    lines = [f"🔍 SCAN COMPLETED — Found {len(candidates)} Qualified Setup(s):\n"]
    for c in candidates[:5]:
        token = c.token
        sym = token.symbol or token.token_address[:8]
        score = c.score_result.score
        mc = fmt_compact_usd(token.market_cap_usd)
        p5m = fmt_pct(token.change_5m_pct)
        lines.append(f"• ${sym} | Score: {score:.0f}/100 | MC: {mc} | 5M: {p5m}")

    lines.append("\nDetailed setup alerts dispatched above.")
    return "\n".join(lines)


def format_history_message(alerts: List[Dict[str, Any]]) -> str:
    """Format /history command recent alerts list, supporting tripartite research records."""
    if not alerts:
        return "📜 ALERT HISTORY\n\nNo historical calls recorded in research database yet."

    lines = ["📜 RESEARCH DATABASE — CALL HISTORY\n"]
    for a in alerts[:6]:
        if "what_did_we_see" in a and "what_actually_happened" in a:
            seen = a["what_did_we_see"]
            pred = a["what_was_predicted"]
            out = a["what_actually_happened"]
            call_id = a.get("call_id", "")
            short_id = f"CALL {call_id[-6:]}: " if call_id else "CALL: "
            sym = a.get("symbol") or "UNKNOWN"
            res_str = out.get("result") or "PENDING"
            ret = out.get("return_percentage")
            ret_str = f" ({fmt_pct(ret)})" if ret is not None else ""

            lines.append(
                f"🔹 {short_id}${sym}\n"
                f"  • Seen: Score {seen.get('score', 0):.0f} | MC {fmt_compact_usd(seen.get('entry_market_cap_usd'))} | Liq {fmt_compact_usd(seen.get('liquidity_usd'))} | 5M {fmt_pct(seen.get('change_5m_pct'))}\n"
                f"  • Predicted: Target {fmt_pct(pred.get('target_percentage'))} ({fmt_compact_usd(pred.get('target_market_cap'))}) | Inv <{fmt_compact_usd(pred.get('invalidation_market_cap'))}\n"
                f"  • Outcome: {res_str}{ret_str} [{out.get('outcome_status', 'RECORDED')}]\n"
            )
        else:
            sym = a.get("symbol") or a.get("token_address", "UNKNOWN")[:8]
            score = a.get("score", 0)
            mc = fmt_compact_usd(a.get("market_cap"))
            status = a.get("outcome_status", "RECORDED")
            result = a.get("result")
            pnl = a.get("pnl_pct") if a.get("pnl_pct") is not None else a.get("return_percentage")
            pnl_str = f" ({fmt_pct(pnl)})" if pnl is not None else ""
            res_str = f" | {result}" if result else ""
            created = a.get("created_at", "")
            if isinstance(created, datetime):
                created_str = created.strftime("%H:%M UTC")
            else:
                created_str = str(created)[:16]

            lines.append(f"• [{created_str}] ${sym} — Score: {score:.0f} | MC: {mc} | {status}{res_str}{pnl_str}")

    return "\n".join(lines).strip()


def format_stats_message(stats: Dict[str, Any]) -> str:
    """Format /stats command performance and research metrics including empirical expectancy."""
    # Research DB Expectancy metrics if available
    research_metrics = stats.get("research_database")
    if research_metrics:
        total_calls = research_metrics.get("total_calls", 0)
        resolved_calls = research_metrics.get("resolved_calls", 0)
        win_rate = research_metrics.get("empirical_win_rate", 0.0)
        expectancy = research_metrics.get("mathematical_expectancy_pct", 0.0)
        pf = research_metrics.get("profit_factor", 0.0)
        avg_win = research_metrics.get("avg_win_pct", 0.0)
        avg_loss = research_metrics.get("avg_loss_pct", 0.0)

        lines = [
            "📈 RESEARCH DATABASE & EXPECTANCY",
            "==============================",
            f"• Total Calls Logged: {total_calls}",
            f"• Resolved Closed Calls: {resolved_calls}",
            f"• Empirical Win Rate: {win_rate:.1f}%",
            f"• Mathematical Expectancy (E): {fmt_pct(expectancy)} per call",
            f"• Profit Factor: {pf:.2f}",
            f"• Avg Win: +{avg_win:.1f}% | Avg Loss: -{avg_loss:.1f}%",
            "------------------------------",
            "Score Tier Expectancy:",
        ]

        by_tier = research_metrics.get("by_score_tier", {})
        if by_tier:
            for tier, tdata in by_tier.items():
                t_wr = tdata.get("win_rate", 0.0)
                t_exp = tdata.get("expectancy_pct", 0.0)
                t_calls = tdata.get("resolved_calls", 0)
                lines.append(f"  • {tier}: WR {t_wr:.1f}% | E: {fmt_pct(t_exp)} ({t_calls} calls)")
        else:
            lines.append("  • Insufficient data for score tier segmentation.")

        # Also add paper trading metrics if present
        paper_total = stats.get("total_trades", 0)
        if paper_total > 0:
            p_wins = stats.get("winning_trades", 0)
            p_losses = stats.get("losing_trades", 0)
            p_wr = (p_wins / paper_total * 100) if paper_total > 0 else 0.0
            lines.extend([
                "------------------------------",
                "Simulated Paper Trades:",
                f"• Executed: {paper_total} | Wins: {p_wins} | Losses: {p_losses}",
                f"• Paper Win Rate: {p_wr:.1f}% | PF: {stats.get('profit_factor', 0.0):.2f}",
            ])

        lines.extend([
            "==============================",
            "Note: Zero hindsight bias. Pure empirical verification.",
        ])
        return "\n".join(lines)

    # Standard fallback if only paper trade stats are provided
    total = stats.get("total_trades", 0)
    wins = stats.get("winning_trades", 0)
    losses = stats.get("losing_trades", 0)
    win_rate = (wins / total * 100) if total > 0 else 0.0
    avg_gain = stats.get("avg_gain_pct", 0.0)
    avg_loss = stats.get("avg_loss_pct", 0.0)
    profit_factor = stats.get("profit_factor", 0.0)
    pf_str = f"{profit_factor:.2f}" if profit_factor is not None else "N/A"

    return (
        "📈 RESEARCH & PERFORMANCE STATS\n"
        "==============================\n"
        f"• Total Observed Setups: {stats.get('total_alerts', 0)}\n"
        f"• Paper Trades Executed: {total}\n"
        f"• Wins / Losses: {wins} / {losses}\n"
        f"• Win Rate: {win_rate:.1f}%\n"
        f"• Avg Gain on Win: +{avg_gain:.1f}%\n"
        f"• Avg Loss on Stop: {avg_loss:.1f}%\n"
        f"• Profit Factor: {pf_str}\n"
        f"• Invalidation Accuracy: {stats.get('invalidation_rate', 0.0):.1f}%\n"
        "==============================\n"
        "Note: Based on deterministic strategy execution."
    )


def format_paper_message(paper_data: Dict[str, Any]) -> str:
    """Format /paper command active simulated positions and recent exits."""
    open_trades = paper_data.get("open_trades", [])
    recent_closed = paper_data.get("recent_closed", [])

    lines = ["📝 SIMULATED PAPER TRADING\n"]

    lines.append(f"Active Positions: {len(open_trades)}")
    if open_trades:
        for t in open_trades:
            sym = t.get("symbol") or t.get("token_address", "")[:8]
            entry_mc = fmt_compact_usd(t.get("entry_market_cap"))
            target_mc = fmt_compact_usd(t.get("target_market_cap"))
            stop_mc = fmt_compact_usd(t.get("invalidation_market_cap"))
            pnl = t.get("unrealized_pnl_pct", 0.0)
            lines.append(
                f"• ${sym} | Entry: {entry_mc} | Target: {target_mc} | Stop: {stop_mc} | PnL: {fmt_pct(pnl)}"
            )
    else:
        lines.append("• No open positions.")

    lines.append("\nRecent Closed:")
    if recent_closed:
        for c in recent_closed[:5]:
            sym = c.get("symbol") or c.get("token_address", "")[:8]
            pnl = c.get("pnl_pct", 0.0)
            reason = c.get("status", "CLOSED")
            lines.append(f"• ${sym}: {fmt_pct(pnl)} ({reason})")
    else:
        lines.append("• No closed trades yet.")

    return "\n".join(lines)


def format_settings_message(settings_data: Dict[str, Any]) -> str:
    """Format /settings command configuration view."""
    min_score = settings_data.get("min_score", 85)
    min_liq = fmt_compact_usd(settings_data.get("min_liquidity", 10000))
    dry_run = "ENABLED" if settings_data.get("dry_run") else "DISABLED"
    alerts_paused = "PAUSED" if settings_data.get("alerts_paused") else "ACTIVE"
    chain = settings_data.get("chain", "solana").upper()

    return (
        "⚙️ SYSTEM SETTINGS\n"
        "=================\n"
        f"• Target Chain: {chain}\n"
        f"• Momentum Score Cutoff: {min_score}/100\n"
        f"• Minimum Liquidity: {min_liq}\n"
        f"• Alert Dispatching: {alerts_paused}\n"
        f"• Dry-Run Mode: {dry_run}\n"
        "=================\n"
        "Use inline controls below to adjust parameters."
    )


def format_watchlist_message(tokens: List[Dict[str, Any]]) -> str:
    """Format /watch list command output."""
    if not tokens:
        return "👀 WATCHLIST\n\nYour watchlist is currently empty.\nUse /watch <token_address> or click [Watch] on an alert."

    lines = [f"👀 WATCHLIST ({len(tokens)} tokens)\n"]
    for t in tokens:
        sym = t.get("symbol") or t.get("token_address", "")[:8]
        addr = t.get("token_address", "")
        lines.append(f"• ${sym}: `{addr}`")

    lines.append("\nUse /unwatch <token_address> to remove a token.")
    return "\n".join(lines)

