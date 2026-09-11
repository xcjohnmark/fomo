"""CLI research tool to export strategy calls and print empirical expectancy reports."""

import argparse
import asyncio
from pathlib import Path
import sys

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from database.session import async_session_factory, close_db, get_engine, init_db
from services.research_database import ResearchDatabaseService


def print_summary_report(stats: dict, show_all_breakdowns: bool = False) -> None:
    """Print clean ASCII summary of empirical expectancy, core metrics, and research findings."""
    print("\n" + "=" * 68)
    print("MOMENTUM / QUICK FLIP RESEARCH DATABASE REPORT")
    print("=" * 68)
    print("CORE PERFORMANCE METRICS:")
    print(f"  Total Strategic Calls Logged : {stats.get('total_calls', 0)}")
    print(f"  Resolved Closed Calls        : {stats.get('resolved_calls', 0)}")
    print(f"  Win Rate / Loss Rate         : {stats.get('win_rate', 0.0):.1f}% / {stats.get('loss_rate', 0.0):.1f}%")
    print(f"  Average Winner / Loser       : +{stats.get('avg_win', 0.0):.1f}% / -{stats.get('avg_loss', 0.0):.1f}%")
    print(f"  Median Winner / Loser        : +{stats.get('median_win', 0.0):.1f}% / -{stats.get('median_loss', 0.0):.1f}%")
    print(f"  Mathematical Expectancy (E)  : {stats.get('overall_expectancy', 0.0):+.2f}% per call")
    print(f"  Profit Factor                : {stats.get('profit_factor', 0.0):.2f}")
    print(f"  Avg / Median Holding Time    : {stats.get('avg_holding_time_min', 0.0):.1f}m / {stats.get('median_holding_time_min', 0.0):.1f}m")
    print(f"  Target-Hit / Inval / Timeout : {stats.get('target_hit_rate', 0.0):.1f}% / {stats.get('invalidation_rate', 0.0):.1f}% / {stats.get('timeout_rate', 0.0):.1f}%")
    print(f"  Max Favorable Excursion (MFE): Avg +{stats.get('avg_mfe', 0.0):.1f}% | Peak +{stats.get('max_mfe', 0.0):.1f}%")
    print(f"  Max Adverse Excursion (MAE)  : Avg {stats.get('avg_mae', 0.0):.1f}% | Peak {stats.get('max_mae', 0.0):.1f}%")
    print(f"  Maximum Drawdown             : {stats.get('max_drawdown', 0.0):.1f}%")
    print("-" * 68)
    print("Performance by Momentum Score Tier:")
    for tier, s in stats.get("by_score_bracket", {}).items():
        calls = s.get("calls", 0)
        wr = s.get("win_rate", 0.0)
        exp = s.get("expectancy", 0.0)
        mfe = s.get("avg_mfe", 0.0)
        print(f"  - {tier:<22}: {calls:>3} calls | Win Rate: {wr:>5.1f}% | E: {exp:>+6.2f}% | Avg MFE: +{mfe:.1f}%")

    print("-" * 68)
    print("Performance by Market Cap Tier:")
    for tier, s in stats.get("by_market_cap_bracket", {}).items():
        calls = s.get("calls", 0)
        wr = s.get("win_rate", 0.0)
        exp = s.get("expectancy", 0.0)
        print(f"  - {tier:<22}: {calls:>3} calls | Win Rate: {wr:>5.1f}% | E: {exp:>+6.2f}%")

    if show_all_breakdowns and "breakdowns" in stats:
        breakdowns = stats["breakdowns"]
        dim_labels = {
            "liquidity": "Liquidity Tiers",
            "volume": "5-Minute Volume Surge",
            "momentum_5m": "5-Minute Momentum",
            "momentum_1h": "1-Hour Momentum",
            "token_age": "Token Age at Entry",
            "top10_concentration": "Top-10 Concentration",
            "buyer_seller_ratio": "Buyer / Seller Breadth",
            "buy_sell_ratio": "Buy / Sell Transaction Flow",
            "time_of_day": "Trading Sessions (UTC)",
            "day_of_week": "Day of Week",
            "market_conditions": "Market Conditions / Regimes",
        }
        for dim_key, dim_name in dim_labels.items():
            if dim_key in breakdowns:
                print("-" * 68)
                print(f"Performance by {dim_name}:")
                for cohort_name, s in breakdowns[dim_key].items():
                    calls = s.get("calls", 0)
                    wr = s.get("win_rate", 0.0)
                    exp = s.get("expectancy", 0.0)
                    print(f"  - {cohort_name:<26}: {calls:>3} calls | Win Rate: {wr:>5.1f}% | E: {exp:>+6.2f}%")

    print("=" * 68 + "\n")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Export research dataset and calculate expectancy.")
    parser.add_argument("--format", choices=["csv", "json"], default="csv", help="Export file format")
    parser.add_argument("--output", type=str, default=None, help="Output file path (default: data/research_calls.<format>)")
    parser.add_argument("--summary", action="store_true", help="Print empirical research report to console")
    parser.add_argument("--breakdowns", action="store_true", help="Include all 13 multi-dimensional breakdowns in summary")
    parser.add_argument("--limit", type=int, default=10000, help="Maximum records to export")
    args = parser.parse_args()

    engine = get_engine()
    await init_db(engine)
    session_factory = async_session_factory(engine)

    research_db = ResearchDatabaseService(session_factory=session_factory)

    try:
        stats = await research_db.compute_empirical_expectancy()

        if args.summary or args.output is None:
            print_summary_report(stats, show_all_breakdowns=args.breakdowns)

        if args.output or not args.summary:
            out_path = args.output or f"data/research_calls.{args.format}"
            if args.format == "csv":
                exported_path = await research_db.export_to_csv(out_path, limit=args.limit)
            else:
                exported_path = await research_db.export_to_json(out_path, limit=args.limit)
            print(f"Successfully exported research records to {exported_path}")

    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
