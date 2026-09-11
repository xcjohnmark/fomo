"""Interactive Telegram bot service implementing control commands and opportunity dispatch."""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

try:
    from telegram import InlineKeyboardMarkup, Update
    from telegram.ext import (
        Application,
        ApplicationBuilder,
        CallbackQueryHandler,
        CommandHandler,
        ContextTypes,
    )
except ImportError:
    Update = None
    Application = None
    ApplicationBuilder = None
    CallbackQueryHandler = None
    CommandHandler = None
    ContextTypes = None

from collectors.base import MarketDataProvider
from config.settings import Settings, get_settings
from models.db import TokenAlert
from models.domain import AlertCandidate, ConfirmationState, QuickFlipPlan
from services.paper_trader import PaperTraderService
from services.research_database import ResearchDatabaseService
from services.watchlist import WatchlistService
from strategy.engine import MomentumStrategyEngine
from strategy.trade_planner import QuickFlipTradePlanner
from telegram.formatter import (
    format_history_message,
    format_paper_message,
    format_scan_summary,
    format_settings_message,
    format_stats_message,
    format_status_message,
    format_telegram_alert,
    format_watchlist_message,
)
from telegram.keyboards import get_alert_keyboard, get_settings_keyboard

logger = logging.getLogger(__name__)


class TelegramBotService:
    """Manages the interactive Telegram bot, command dispatching, and callback interactions."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        paper_trader: Optional[PaperTraderService] = None,
        watchlist: Optional[WatchlistService] = None,
        session_factory: Optional[async_sessionmaker[AsyncSession]] = None,
        collector: Optional[MarketDataProvider] = None,
        strategy_engine: Optional[MomentumStrategyEngine] = None,
    ):
        self.settings = settings or get_settings()
        self.paper_trader = paper_trader or PaperTraderService(session_factory=session_factory)
        self.watchlist = watchlist or WatchlistService(session_factory=session_factory)
        self.session_factory = session_factory
        self.collector = collector
        self.strategy_engine = strategy_engine or MomentumStrategyEngine(settings=self.settings)

        self.alerts_paused: bool = False
        self.min_score: float = float(self.settings.MIN_MOMENTUM_SCORE)
        self.min_liquidity: float = float(self.settings.MIN_LIQUIDITY_USD)

        self._app: Optional[Application] = None
        self._start_time = datetime.now(timezone.utc)

    def is_configured(self) -> bool:
        """Return True if bot token is present and ApplicationBuilder is available."""
        return bool(
            self.settings.TELEGRAM_BOT_TOKEN
            and not self.settings.DRY_RUN
            and ApplicationBuilder is not None
        )

    def build_application(self) -> Optional[Application]:
        """Construct python-telegram-bot Application instance with registered handlers."""
        if not self.is_configured():
            logger.info("TelegramBotService running in DRY-RUN mode (no live application built).")
            return None

        app = ApplicationBuilder().token(self.settings.TELEGRAM_BOT_TOKEN).build()

        # Command Handlers
        app.add_handler(CommandHandler("start", self.start_command))
        app.add_handler(CommandHandler("status", self.status_command))
        app.add_handler(CommandHandler("scan", self.scan_command))
        app.add_handler(CommandHandler("watch", self.watch_command))
        app.add_handler(CommandHandler("unwatch", self.unwatch_command))
        app.add_handler(CommandHandler("history", self.history_command))
        app.add_handler(CommandHandler("stats", self.stats_command))
        app.add_handler(CommandHandler("paper", self.paper_command))
        app.add_handler(CommandHandler("settings", self.settings_command))

        # Interactive Button Callback Handler
        app.add_handler(CallbackQueryHandler(self.button_callback))

        self._app = app
        return app

    # =====================================================================
    # Bot Command Handlers
    # =====================================================================

    async def start_command(self, update: Any, context: Any) -> str:
        """Handle /start command with welcome overview and commands guide."""
        welcome_text = (
            "⚡ FOMO MOMENTUM RESEARCH BOT\n"
            "============================\n"
            "Real-time Pump.fun / Solana micro-structure research and Quick Flip alert engine.\n\n"
            "Available Commands:\n"
            "• /scan — Trigger on-demand market scan & analysis\n"
            "• /status — Check database, data feed, and bot health\n"
            "• /watch <token_ca> — Add token to priority monitor\n"
            "• /unwatch <token_ca> — Remove token from watchlist\n"
            "• /history — View recent recorded alerts & outcomes\n"
            "• /stats — View strategy win rate, avg gain & metrics\n"
            "• /paper — View simulated open trades & PnL\n"
            "• /settings — Inspect and adjust operational cutoffs\n\n"
            "Risk Policy:\n"
            "• Analytical, objective setups only.\n"
            "• Never chase extended moves or illiquid pools.\n"
            "• Not financial advice."
        )
        if update and update.effective_message:
            await update.effective_message.reply_text(welcome_text)
        return welcome_text

    async def status_command(self, update: Any, context: Any) -> str:
        """Handle /status command showing system metrics."""
        open_trades = await self.paper_trader.get_open_trades()
        watchlist_tokens = await self.watchlist.get_watchlist()

        uptime_seconds = int((datetime.now(timezone.utc) - self._start_time).total_seconds())
        hours, remainder = divmod(uptime_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{hours}h {minutes}m {seconds}s"

        status_data = {
            "database_connected": self.session_factory is not None,
            "collector_healthy": self.collector is not None,
            "provider_source": "composite" if self.collector else "mock",
            "telegram_configured": self.is_configured(),
            "alerts_paused": self.alerts_paused,
            "min_score": self.min_score,
            "min_liquidity": self.min_liquidity,
            "watchlist_count": len(watchlist_tokens),
            "open_paper_trades": len(open_trades),
            "uptime": uptime_str,
        }

        text = format_status_message(status_data)
        if update and update.effective_message:
            await update.effective_message.reply_text(text)
        return text

    async def scan_command(self, update: Any, context: Any) -> str:
        """Handle /scan command executing on-demand discovery, scoring, and alerting."""
        if not self.collector:
            text = "⚠️ Scanner collector is currently not attached."
            if update and update.effective_message:
                await update.effective_message.reply_text(text)
            return text

        if update and update.effective_message:
            await update.effective_message.reply_text("🔎 Scanning active market pairs for momentum setups...")

        tokens = await self.collector.fetch_active_tokens()
        candidates: List[AlertCandidate] = []

        for token in tokens:
            if token.liquidity_usd is not None and token.liquidity_usd < self.min_liquidity:
                continue

            analysis = self.strategy_engine.analyze(token)
            if analysis.score >= self.min_score and analysis.setup_state not in (
                ConfirmationState.INVALIDATED,
                ConfirmationState.WEAKENING,
            ):
                plan = QuickFlipTradePlanner.generate_plan(analysis, token)
                candidate = AlertCandidate(
                    token=token,
                    score_result=self.strategy_engine.scorer.calculate_score(token),
                    classification=analysis.classification,
                    confirmation_state=analysis.setup_state,
                    alert_reason=f"Scan score: {analysis.score:.0f}",
                    reasons=analysis.reasons,
                    risks=analysis.warnings,
                    confirmation_needed="; ".join(analysis.confirmation_needed),
                    invalidation_criteria="; ".join(analysis.invalidation_conditions),
                    next_action=analysis.next_action,
                    analysis=analysis,
                    plan=plan,
                )
                candidates.append(candidate)

        # Send individual setup cards if found
        if update and update.effective_message and candidates:
            for c in candidates[:3]:
                card_text = format_telegram_alert(c)
                markup = get_alert_keyboard(c.token.token_address, chain=c.token.chain)
                await update.effective_message.reply_text(card_text, reply_markup=markup)

        summary_text = format_scan_summary(candidates)
        if update and update.effective_message:
            await update.effective_message.reply_text(summary_text)
        return summary_text

    async def watch_command(self, update: Any, context: Any) -> str:
        """Handle /watch <token_ca> command."""
        args = context.args if context and hasattr(context, "args") else []
        if not args:
            tokens = await self.watchlist.get_watchlist()
            text = format_watchlist_message(tokens)
            if update and update.effective_message:
                await update.effective_message.reply_text(text)
            return text

        token_address = args[0].strip()
        symbol = args[1].strip() if len(args) > 1 else None
        await self.watchlist.add_token(token_address, symbol=symbol)
        text = f"✅ Added `{token_address}` to your watchlist."
        if update and update.effective_message:
            await update.effective_message.reply_text(text)
        return text

    async def unwatch_command(self, update: Any, context: Any) -> str:
        """Handle /unwatch <token_ca> command."""
        args = context.args if context and hasattr(context, "args") else []
        if not args:
            text = "Usage: /unwatch <token_address>"
            if update and update.effective_message:
                await update.effective_message.reply_text(text)
            return text

        token_address = args[0].strip()
        removed = await self.watchlist.remove_token(token_address)
        if removed:
            text = f"🗑️ Removed `{token_address}` from your watchlist."
        else:
            text = f"Token `{token_address}` was not found in your watchlist."

        if update and update.effective_message:
            await update.effective_message.reply_text(text)
        return text

    async def history_command(self, update: Any, context: Any) -> str:
        """Handle /history command displaying historical recorded alerts and research calls."""
        alerts_data: List[Dict[str, Any]] = []
        if self.session_factory:
            research_service = ResearchDatabaseService(self.session_factory)
            tripartite_records = await research_service.get_tripartite_records(limit=10)
            if tripartite_records:
                alerts_data = tripartite_records
            else:
                async with self.session_factory() as session:
                    stmt = select(TokenAlert).order_by(desc(TokenAlert.id)).limit(10)
                    res = await session.execute(stmt)
                    for a in res.scalars().all():
                        alerts_data.append(
                            {
                                "symbol": a.symbol,
                                "token_address": a.token_address,
                                "score": a.momentum_score,
                                "market_cap": a.market_cap,
                                "outcome_status": a.confirmation_state,
                                "created_at": a.created_at,
                            }
                        )

        text = format_history_message(alerts_data)
        if update and update.effective_message:
            await update.effective_message.reply_text(text)
        return text

    async def stats_command(self, update: Any, context: Any) -> str:
        """Handle /stats command showing empirical expectancy and performance metrics."""
        paper_stats = await self.paper_trader.get_performance_stats()

        total_alerts = 0
        research_metrics = None
        if self.session_factory:
            research_service = ResearchDatabaseService(self.session_factory)
            exp_data = await research_service.compute_empirical_expectancy()
            if exp_data.get("total_calls", 0) > 0:
                research_metrics = exp_data

            async with self.session_factory() as session:
                stmt = select(TokenAlert)
                res = await session.execute(stmt)
                total_alerts = len(list(res.scalars().all()))

        stats_payload = {
            "total_alerts": total_alerts,
            "total_trades": paper_stats["total_trades"],
            "winning_trades": paper_stats["winning_trades"],
            "losing_trades": paper_stats["losing_trades"],
            "avg_gain_pct": paper_stats["avg_gain_pct"],
            "avg_loss_pct": paper_stats["avg_loss_pct"],
            "profit_factor": paper_stats["profit_factor"],
            "invalidation_rate": paper_stats["invalidation_rate"],
            "research_database": research_metrics,
        }

        text = format_stats_message(stats_payload)
        if update and update.effective_message:
            await update.effective_message.reply_text(text)
        return text

    async def paper_command(self, update: Any, context: Any) -> str:
        """Handle /paper command displaying simulated trades and performance."""
        open_trades = await self.paper_trader.get_open_trades()
        recent_closed = await self.paper_trader.get_recent_closed(limit=5)

        paper_payload = {
            "open_trades": open_trades,
            "recent_closed": recent_closed,
        }

        text = format_paper_message(paper_payload)
        if update and update.effective_message:
            await update.effective_message.reply_text(text)
        return text

    async def settings_command(self, update: Any, context: Any) -> str:
        """Handle /settings command showing operational configuration."""
        settings_payload = {
            "chain": "solana",
            "min_score": self.min_score,
            "min_liquidity": self.min_liquidity,
            "dry_run": self.settings.DRY_RUN or not self.is_configured(),
            "alerts_paused": self.alerts_paused,
        }

        text = format_settings_message(settings_payload)
        markup = get_settings_keyboard(settings_payload)
        if update and update.effective_message:
            await update.effective_message.reply_text(text, reply_markup=markup)
        return text

    # =====================================================================
    # Interactive Callback Handlers
    # =====================================================================

    async def button_callback(self, update: Any, context: Any) -> str:
        """Process interactive button callbacks (watch, paper, ignore, settings)."""
        query = update.callback_query if update else None
        if not query or not query.data:
            return "No data"

        data = query.data
        action, _, param = data.partition(":")

        if action == "watch":
            token_address = param
            await self.watchlist.add_token(token_address)
            await query.answer(f"Added {token_address[:8]}... to Watchlist!")
            return "watched"

        elif action == "paper":
            token_address = param
            now = datetime.now(timezone.utc)
            # Fetch current live spot snapshot
            snapshot = None
            if self.collector:
                snapshot = await self.collector.fetch_token_snapshot(token_address)

            entry_price = snapshot.price_usd if snapshot and snapshot.price_usd else 0.0001
            entry_mc = snapshot.market_cap_usd if snapshot and snapshot.market_cap_usd else 100_000.0
            symbol = snapshot.symbol if snapshot and snapshot.symbol else "TOKEN"

            target_price = entry_price * 1.25
            target_mc = entry_mc * 1.25
            invalidation_price = entry_price * 0.92
            invalidation_mc = entry_mc * 0.92

            trade = await self.paper_trader.open_trade(
                token_address=token_address,
                symbol=symbol,
                entry_price=entry_price,
                entry_market_cap=entry_mc,
                target_price=target_price,
                target_market_cap=target_mc,
                invalidation_price=invalidation_price,
                invalidation_market_cap=invalidation_mc,
                expected_holding_minutes=25,
                entry_timestamp=now,
            )

            await query.answer(f"📝 Paper Trade executed for ${symbol}!")

            # Send execution card
            mc_str = f"${entry_mc:,.0f}" if entry_mc else "N/A"
            target_mc_str = f"${target_mc:,.0f}" if target_mc else "N/A"
            inval_mc_str = f"${invalidation_mc:,.0f}" if invalidation_mc else "N/A"
            exec_card = (
                "📝 PAPER TRADE EXECUTED\n"
                "=======================\n"
                f"${symbol}\n"
                f"Entry Price: ${entry_price:.8f}\n"
                f"Entry MC: {mc_str}\n"
                f"Entry Time: {now.strftime('%H:%M:%S UTC')}\n\n"
                f"Target: {target_mc_str} MC (+25.0%)\n"
                f"Invalidation: Below {inval_mc_str} MC (-8.0%)\n"
                "Status: MONITORING ACTIVE\n"
                "======================="
            )
            if update and getattr(update, "effective_message", None):
                reply_fn = getattr(update.effective_message, "reply_text", None)
                if callable(reply_fn):
                    resp = reply_fn(exec_card)
                    if hasattr(resp, "__await__"):
                        await resp

            return "paper_opened"

        elif action == "ignore":
            token_address = param
            await query.answer("Setup ignored.")
            try:
                await query.edit_message_reply_markup(reply_markup=None)
            except Exception:
                pass
            return "ignored"

        elif action == "settings":
            if param == "toggle_pause":
                self.alerts_paused = not self.alerts_paused
                status = "PAUSED" if self.alerts_paused else "RESUMED"
                await query.answer(f"Alerts {status}!")
            elif param == "score_down":
                self.min_score = max(50.0, self.min_score - 5.0)
                await query.answer(f"Min Score: {self.min_score:.0f}")
            elif param == "score_up":
                self.min_score = min(95.0, self.min_score + 5.0)
                await query.answer(f"Min Score: {self.min_score:.0f}")

            # Refresh settings message
            settings_payload = {
                "chain": "solana",
                "min_score": self.min_score,
                "min_liquidity": self.min_liquidity,
                "dry_run": self.settings.DRY_RUN or not self.is_configured(),
                "alerts_paused": self.alerts_paused,
            }
            try:
                await query.edit_message_text(
                    format_settings_message(settings_payload),
                    reply_markup=get_settings_keyboard(settings_payload),
                )
            except Exception:
                pass
            return "settings_updated"

        await query.answer()
        return "ok"
