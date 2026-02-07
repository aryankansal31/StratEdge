"""
Live trading engine.
Executes strategies in real-time with paper or live mode.
"""

import logging
import time
import schedule
from typing import Optional
from datetime import datetime

from ..config import settings
from ..api import client
from ..data import live_fetcher, historical_fetcher, instrument_manager
from ..strategies import BaseStrategy, MarketData, BullCallSpreadStrategy
from ..execution import order_manager, position_manager
from ..utils import is_market_open, get_next_market_open, format_currency

LOG = logging.getLogger(__name__)


class LiveTrader:
    """
    Live trading engine that executes strategies in real-time.
    Supports both paper and live trading modes.
    """
    
    def __init__(
        self,
        strategy: Optional[BaseStrategy] = None,
        mode: str = None,
        underlying: str = None
    ):
        self.strategy = strategy or BullCallSpreadStrategy()
        self.mode = mode or settings.mode
        self.underlying = underlying or settings.underlying
        self._running = False
        self._client = client
        
    def start(self) -> None:
        """Start the live trading engine."""
        LOG.info(f"Starting live trader in {self.mode} mode")
        self._running = True
        
        # Schedule entry and exit checks
        schedule.every().second.do(self.check_trading_window)
        
        LOG.info(f"Strategy: {self.strategy.name}")
        LOG.info(f"Underlying: {settings.underlying}")
        LOG.info(f"Entry Time: {settings.entry_time}")
        LOG.info(f"Exit Time: {settings.exit_time}")
        
        try:
            while self._running:
                self.run_step()
                time.sleep(1)
        except KeyboardInterrupt:
            LOG.info("Received shutdown signal")
            self.stop()

    def run_step(self) -> None:
        """Run a single iteration of the trading loop."""
        schedule.run_pending()
    
    def stop(self) -> None:
        """Stop the trading engine."""
        self._running = False
        LOG.info("Live trader stopped")
        
        # Close any open positions
        if position_manager.has_open_positions():
            LOG.warning("Closing open positions on shutdown")
            self._force_close_positions()
        
        # Print summary
        stats = position_manager.get_stats()
        LOG.info(f"Session Summary: {stats}")
    
    def check_trading_window(self) -> None:
        """Check if we should enter or exit trades."""
        now = datetime.now()
        
        if not is_market_open(now):
            return
        
        # Get current market data
        market_data = self._get_market_data(now)
        if not market_data:
            return
        
        # Check for entry
        if not position_manager.has_open_positions():
            if self.strategy.should_enter(market_data):
                self._execute_entry(market_data)
        
        # Check for exit
        for position in position_manager.get_open_positions():
            # Pass the actual position (SpreadPosition) to the strategy
            if self.strategy.should_exit(position, market_data):
                self._execute_exit(position, market_data)
    
    def _get_market_data(self, timestamp: datetime) -> Optional[MarketData]:
        """Fetch current market data."""
        try:
            underlying = self.underlying
            
            # Get spot price
            spot = live_fetcher.get_spot_ltp(underlying)
            if not spot:
                return None
            
            # Get expiries
            expiries = historical_fetcher.get_expiries(underlying)
            if not expiries:
                return None
            
            # Find nearest expiry
            today = timestamp.strftime("%Y-%m-%d")
            future_expiries = [e for e in expiries if e > today]
            if not future_expiries:
                return None
            
            nearest_expiry = min(future_expiries)
            
            # Get option chain
            option_chain = historical_fetcher.get_option_chain(underlying, nearest_expiry)
            
            return MarketData(
                underlying=underlying,
                spot_price=spot,
                timestamp=timestamp,
                option_chain=option_chain,
                expiries=expiries,
                current_expiry=nearest_expiry
            )
            
        except Exception as e:
            LOG.error(f"Failed to get market data: {e}")
            return None
    
    def _execute_entry(self, market_data: MarketData) -> None:
        """Execute entry orders."""
        LOG.info("Executing entry...")
        
        orders = self.strategy.get_entry_orders(market_data)
        if not orders:
            LOG.warning("No entry orders generated")
            return
        
        # Place orders
        records = order_manager.place_orders(orders, slippage=settings.slippage_points)
        
        # Get fill prices
        buy_record = next((r for r in records if r.order.side.value == "BUY"), None)
        sell_record = next((r for r in records if r.order.side.value == "SELL"), None)
        
        if not buy_record or not sell_record:
            LOG.error("Failed to place both legs")
            return
        
        # In paper mode, simulate fill prices
        if self.mode == "PAPER":
            buy_strike = self.strategy.buy_strike
            sell_strike = self.strategy.sell_strike
            
            buy_price = max(10, market_data.spot_price - buy_strike) + 20
            sell_price = max(5, market_data.spot_price - sell_strike) + 10
            
            buy_record.fill_price = buy_price + settings.slippage_points
            sell_record.fill_price = sell_price - settings.slippage_points
        
        # Open position
        lot_size = instrument_manager.get_lot_size(market_data.underlying)
        
        position_manager.open_spread(
            underlying=market_data.underlying,
            strategy_name=self.strategy.name,
            long_symbol=buy_record.order.symbol,
            short_symbol=sell_record.order.symbol,
            long_price=buy_record.fill_price or 0,
            short_price=sell_record.fill_price or 0,
            quantity=1,
            lot_size=lot_size,
            brokerage=settings.brokerage_per_order * 2
        )
        
        LOG.info(f"Entry executed: {self.strategy.buy_strike}CE/{self.strategy.sell_strike}CE")
    
    def _execute_exit(self, position, market_data: MarketData) -> None:
        """Execute exit orders."""
        LOG.info(f"Executing exit for {position.spread_id}...")
        
        # Pass the position object to generate exit orders with correct symbols
        orders = self.strategy.get_exit_orders(position, market_data)
        if not orders:
            LOG.warning("No exit orders generated")
            return
        
        # Place orders
        records = order_manager.place_orders(orders, slippage=settings.slippage_points)
        
        # Get fill prices (simulated in paper mode)
        sell_record = next((r for r in records if r.order.side.value == "SELL"), None)
        buy_record = next((r for r in records if r.order.side.value == "BUY"), None)
        
        exit_long = position.long_price * 0.95  # Simulate time decay
        exit_short = position.short_price * 0.95
        
        # Close position
        pnl = position_manager.close_spread(
            spread_id=position.spread_id,
            exit_long=exit_long,
            exit_short=exit_short,
            brokerage=settings.brokerage_per_order * 2
        )
        
        LOG.info(f"Exit executed: P&L = {format_currency(pnl)}")
    
    def _force_close_positions(self) -> None:
        """Force close all open positions."""
        for position in position_manager.get_open_positions():
            try:
                # Use last known prices
                position_manager.close_spread(
                    spread_id=position.spread_id,
                    exit_long=position.long_price,
                    exit_short=position.short_price,
                    brokerage=settings.brokerage_per_order * 2
                )
                LOG.info(f"Force closed {position.spread_id}")
            except Exception as e:
                LOG.error(f"Failed to force close {position.spread_id}: {e}")


def start_trading(
    mode: str = None,
    strategy: Optional[BaseStrategy] = None
) -> None:
    """
    Start live trading.
    
    Args:
        mode: PAPER or LIVE (default from settings)
        strategy: Strategy to run (default BullCallSpread)
    """
    trader = LiveTrader(strategy=strategy, mode=mode)
    trader.start()
