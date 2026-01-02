"""
Visibility Doctor CLI

Usage:
    visibility-doctor analyze https://airbnb.com/rooms/12345
    visibility-doctor analyze 12345 --output report.json
    vdoc analyze 12345 --no-market --quiet
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from .doctor import VisibilityDoctor


def create_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser"""
    parser = argparse.ArgumentParser(
        prog="visibility-doctor",
        description="🏥 Visibility Doctor - Airbnb listing visibility analyzer",
        epilog="Example: visibility-doctor analyze https://airbnb.com/rooms/12345"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Analyze command
    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Analyze a listing's visibility"
    )
    analyze_parser.add_argument(
        "listing",
        help="Airbnb listing URL or ID"
    )
    analyze_parser.add_argument(
        "-o", "--output",
        help="Output file path (JSON)",
        type=Path
    )
    analyze_parser.add_argument(
        "--currency",
        default="EUR",
        help="Currency for prices (default: EUR)"
    )
    analyze_parser.add_argument(
        "--radius",
        type=float,
        default=5.0,
        help="Market radius in km (default: 5.0)"
    )
    analyze_parser.add_argument(
        "--max-competitors",
        type=int,
        default=20,
        help="Max competitors to analyze (default: 20)"
    )
    analyze_parser.add_argument(
        "--no-market",
        action="store_true",
        help="Skip market comparison"
    )
    analyze_parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress progress output"
    )
    analyze_parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON to stdout"
    )
    
    # Version command
    parser.add_argument(
        "-v", "--version",
        action="version",
        version="%(prog)s 1.0.0"
    )
    
    return parser


async def run_analyze(args) -> int:
    """Run the analyze command"""
    try:
        async with VisibilityDoctor(
            currency=args.currency,
            market_radius_km=args.radius,
            max_competitors=args.max_competitors,
        ) as doctor:
            result = await doctor.analyze(
                args.listing,
                compare_market=not args.no_market,
                verbose=not args.quiet and not args.json,
            )
        
        # Output as JSON if requested
        if args.json:
            print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        
        # Save to file if requested
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)
            if not args.quiet:
                print(f"\n✅ Report saved to: {args.output}")
        
        # Print quick wins if not quiet
        if not args.quiet and not args.json and result.quick_wins_count > 0:
            print("\n⚡ QUICK WINS RECOMMANDÉS")
            print("─" * 40)
            for qw in result.action_plan.get("quick_wins", [])[:5]:
                print(f"  • {qw['title']} (+{qw['impact_percent']:.0f}%)")
        
        return 0
        
    except ValueError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        return 1


def main():
    """Main entry point"""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    if args.command == "analyze":
        return asyncio.run(run_analyze(args))
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
