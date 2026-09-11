"""CLI research tool to export strategy calls and print empirical expectancy reports."""

import argparse
import asyncio
from pathlib import Path
import sys

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from database.session import async_session_factory, close_db, get_engine, init_db
from services.research_database import ResearchDatabaseService


def print_summary_report(stats: dict) -> None:
    """Print clean ASCII summary of empirical expectancy and research findings."""
    print("\n" + "=" * 62)
    print("MOMENTUM / QUICK FLIP RESEARCH DATABASE REPORT")
    print("=" * 62)
    print(f"Total Strategic Calls Logged : {stats['total_calls']}")
    print(f"Resolved Closed Calls        : {stats['resolved_calls']}")
    print(f"Empirical Win Rate           : {stats['win_rate']:.1f}%")
    print(f"Mathematical Expectancy (E)  : {stats['overall_expectancy']:+.2f}% per call")
    print(f"Profit Factor                : {stats['profit_factor']:.2f}")
    print(f"Average Return on Win        : +{stats.get('avg_win_pct', 0.0):.1f}%")
    print(f"Average Loss on Stop         : -{stats.get('avg_loss_pct', 0.0):.1f}%")
    print("-" * 62)
    print("Performance by Momentum Score Tier:")
    for tier, s in stats.get("by_score_bracket", {}).items():
        calls = s["calls"]
        wr = s["win_rate"]
        exp = s["expectancy"]
        mfe = s["avg_mfe"]
        print(f"  - {tier:<14}: {calls:>3} calls | Win Rate: {wr:>5.1f}% | E: {exp:>+6.2f}% | Avg MFE: +{mfe:.1f}%")

    print("-" * 62)
    print("Performance by Market Cap Tier:")
    for tier, s in stats.get("by_market_cap_bracket", {}).items():
        calls = s["calls"]
        wr = s["win_rate"]
        exp = s["expectancy"]
        print(f"  - {tier:<14}: {calls:>3} calls | Win Rate: {wr:>5.1f}% | E: {exp:>+6.2f}%")
    print("=" * 62 + "\n")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Export research dataset and calculate expectancy.")
    parser.add_argument("--format", choices=["csv", "json"], default="csv", help="Export file format")
    parser.add_argument("--output", type=str, default=None, help="Output file path (default: data/research_calls.<format>)")
    parser.add_argument("--summary", action="store_true", help="Print empirical research report to console")
    parser.add_argument("--limit", type=int, default=10000, help="Maximum records to export")
    args = parser.parse_args()

    engine = get_engine()
    await init_db(engine)
    session_factory = async_session_factory(engine)

    research_db = ResearchDatabaseService(session_factory=session_factory)

    try:
        stats = await research_db.compute_empirical_expectancy()

        if args.summary or args.output is None:
            print_summary_report(stats)

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
