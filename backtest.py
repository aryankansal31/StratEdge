#!/usr/bin/env python
"""
Backtest Entry Point.
Run backtesting with configurable parameters.
"""

import argparse
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import settings


def main():
    parser = argparse.ArgumentParser(
        description="Run trading strategy backtest"
    )
    
    parser.add_argument(
        "--underlying",
        type=str,
        default=None,
        help="Underlying symbol (default: from settings)"
    )
    
    parser.add_argument(
        "--from-date",
        type=str,
        default=None,
        help="Start date in YYYY-MM-DD format"
    )
    
    parser.add_argument(
        "--to-date",
        type=str,
        default=None,
        help="End date in YYYY-MM-DD format"
    )
    
    parser.add_argument(
        "--spread-width",
        type=int,
        default=300,
        help="Spread width in points (default: 300)"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        default="backtest_results.csv",
        help="Output CSV file for results"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging (show all details)"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode (shows API calls)"
    )
    
    args = parser.parse_args()
    
    # Setup logging BEFORE importing other modules
    from src.utils.logger import setup_logger
    
    # Determine log level
    if args.debug:
        log_level = logging.DEBUG
    elif args.verbose:
        log_level = logging.INFO
    else:
        log_level = logging.WARNING
    
    # Setup main logger
    logger = setup_logger("backtest", level=log_level, verbose=args.verbose or args.debug)
    
    # Also configure module loggers to use same level
    for module in ["src.engine.backtester", "src.data.historical", "src.strategies", "src.execution"]:
        mod_logger = logging.getLogger(module)
        mod_logger.setLevel(log_level)
        # Add console handler if not present
        if not mod_logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(log_level)
            handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s", datefmt="%H:%M:%S"))
            mod_logger.addHandler(handler)
    
    # Now import the rest
    from src.engine import run_backtest
    from src.strategies import BullCallSpreadStrategy
    
    logger.info("=" * 70)
    logger.info("                    TRADING BOT BACKTEST")
    logger.info("=" * 70)
    
    # Create strategy with custom spread width
    strategy = BullCallSpreadStrategy(spread_width=args.spread_width)
    
    # Run backtest
    result = run_backtest(
        underlying=args.underlying,
        from_date=args.from_date,
        to_date=args.to_date,
        strategy=strategy
    )
    
    # Save results
    if result.trades:
        df = result.to_dataframe()
        df.to_csv(args.output, index=False)
        logger.info(f"📁 Results saved to {args.output}")
    else:
        logger.warning("⚠️  No trades executed - no results saved")
    
    # Print summary
    print(result.summary())
    
    return 0 if result.total_pnl >= 0 else 1


if __name__ == "__main__":
    sys.exit(main())
