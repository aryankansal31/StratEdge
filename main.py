#!/usr/bin/env python
"""
Live Trading Entry Point.
Start the trading bot in paper or live mode.
"""

import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.engine import start_trading
from src.strategies import BullCallSpreadStrategy
from src.utils import setup_logger, is_market_open, get_next_market_open
from src.config import settings


def main():
    parser = argparse.ArgumentParser(
        description="Run live trading bot"
    )
    
    parser.add_argument(
        "--mode",
        type=str,
        choices=["paper", "live"],
        default="paper",
        help="Trading mode: paper or live (default: paper)"
    )
    
    parser.add_argument(
        "--spread-width",
        type=int,
        default=None,
        help="Spread width in points"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Test configuration without starting trader"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    import logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logger = setup_logger("live_trader", level=log_level)
    
    logger.info("=" * 50)
    logger.info("Trading Bot - Live Trading")
    logger.info("=" * 50)
    
    # Safety check for live mode
    mode = args.mode.upper()
    if mode == "LIVE":
        logger.warning("⚠️  LIVE TRADING MODE - Real money at risk!")
        confirm = input("Type 'YES' to confirm: ")
        if confirm != "YES":
            logger.info("Aborted.")
            return 1
    
    logger.info(f"Mode: {mode}")
    logger.info(f"Underlying: {settings.underlying}")
    logger.info(f"Capital: ₹{settings.capital:,.2f}")
    logger.info(f"Risk: {settings.risk_pct:.1%}")
    logger.info(f"Entry Time: {settings.entry_time}")
    logger.info(f"Exit Time: {settings.exit_time}")
    
    # Check market status
    if is_market_open():
        logger.info("Market is OPEN")
    else:
        next_open = get_next_market_open()
        logger.info(f"Market is CLOSED. Next open: {next_open}")
    
    if args.dry_run:
        logger.info("Dry run completed successfully")
        return 0
    
    # Create strategy
    strategy = BullCallSpreadStrategy(
        spread_width=args.spread_width or settings.spread_width
    )
    
    logger.info(f"Strategy: {strategy.name}")
    logger.info(f"Spread Width: {strategy.spread_width}")
    
    # Start trading
    try:
        start_trading(mode=mode, strategy=strategy)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
