"""
Bull Call Spread Strategy Implementation.
Buys ATM call and sells OTM call at specified spread width.
"""

import logging
from typing import List, Optional, Any
from datetime import datetime

from .base import (
    BaseStrategy, Order, Position, MarketData,
    OrderSide, OrderType
)
from ..config import settings
from ..utils import parse_time, find_atm_strike, compute_max_contracts
from ..data import instrument_manager

LOG = logging.getLogger(__name__)


class BullCallSpreadStrategy(BaseStrategy):
    """
    Bull Call Spread Strategy.
    
    - Entry: Buy ATM CE, Sell ATM + spread_width CE
    - Entry Time: Configurable (default 09:25)
    - Exit Time: Configurable (default 15:20)
    - Risk: Limited to net debit
    """
    
    def __init__(
        self,
        spread_width: int = None,
        entry_time: str = None,
        exit_time: str = None,
        capital: float = None,
        risk_pct: float = None
    ):
        super().__init__(name="BullCallSpread")
        
        self.spread_width = spread_width or settings.spread_width
        self.entry_time = entry_time or settings.entry_time
        self.exit_time = exit_time or settings.exit_time
        self.capital = capital or settings.capital
        self.risk_pct = risk_pct or settings.risk_pct
        
        self._entry_hour, self._entry_min = parse_time(self.entry_time)
        self._exit_hour, self._exit_min = parse_time(self.exit_time)
        
        self._entered_today = False
        self._current_date: Optional[str] = None
        
        # Leg details
        self.buy_symbol: Optional[str] = None
        self.sell_symbol: Optional[str] = None
        self.buy_strike: Optional[float] = None
        self.sell_strike: Optional[float] = None
        self.lot_size: int = 1
    
    def _is_entry_time(self, timestamp: datetime) -> bool:
        """Check if current time is entry time."""
        return (
            timestamp.hour == self._entry_hour and
            timestamp.minute >= self._entry_min and
            timestamp.minute < self._entry_min + 5
        )
    
    def _is_exit_time(self, timestamp: datetime) -> bool:
        """Check if current time is exit time."""
        return (
            timestamp.hour == self._exit_hour and
            timestamp.minute >= self._exit_min
        ) or timestamp.hour > self._exit_hour
    
    def _reset_for_new_day(self, date_str: str) -> None:
        """Reset strategy state for new trading day."""
        if self._current_date != date_str:
            self._current_date = date_str
            self._entered_today = False
            self.buy_symbol = None
            self.sell_symbol = None
    
    def should_enter(self, market_data: MarketData) -> bool:
        """Check entry conditions."""
        date_str = market_data.timestamp.strftime("%Y-%m-%d")
        self._reset_for_new_day(date_str)
        
        if self._entered_today:
            return False
        
        if not self._is_entry_time(market_data.timestamp):
            return False
        
        if not market_data.spot_price or market_data.spot_price <= 0:
            LOG.warning("Invalid spot price for entry")
            return False
        
        if not market_data.option_chain.get("calls"):
            LOG.warning("No options available in chain")
            return False
        
        return True
    
    def get_entry_orders(self, market_data: MarketData) -> List[Order]:
        """Generate entry orders for bull call spread."""
        orders = []
        
        # Get available strikes from option chain
        calls = market_data.option_chain.get("calls", [])
        strikes = set()
        for contract in calls:
            parts = contract.split("-")
            if len(parts) >= 4:
                try:
                    strikes.add(float(parts[3]))
                except ValueError:
                    continue
        
        if not strikes:
            LOG.error("Could not extract strikes from option chain")
            return orders
        
        # Find ATM and OTM strikes
        strikes_list = sorted(list(strikes))
        self.buy_strike = find_atm_strike(market_data.spot_price, strikes_list)
        self.sell_strike = self.buy_strike + self.spread_width
        
        # Find closest available sell strike
        if self.sell_strike not in strikes:
            available_higher = [s for s in strikes_list if s > self.buy_strike]
            if available_higher:
                self.sell_strike = min(available_higher, key=lambda s: abs(s - (self.buy_strike + self.spread_width)))
        
        # Find contract symbols
        self.buy_symbol = instrument_manager.find_option_in_contracts(
            calls, self.buy_strike, "CE"
        )
        self.sell_symbol = instrument_manager.find_option_in_contracts(
            calls, self.sell_strike, "CE"
        )
        
        if not self.buy_symbol or not self.sell_symbol:
            LOG.error(f"Could not find contracts for strikes {self.buy_strike}/{self.sell_strike}")
            return orders
        
        # Get lot size
        self.lot_size = instrument_manager.get_lot_size(market_data.underlying)
        
        # Create orders
        orders.append(Order(
            symbol=self.buy_symbol,
            exchange="NSE",
            side=OrderSide.BUY,
            quantity=self.lot_size,
            order_type=OrderType.MARKET,
            segment="FNO"
        ))
        
        orders.append(Order(
            symbol=self.sell_symbol,
            exchange="NSE",
            side=OrderSide.SELL,
            quantity=self.lot_size,
            order_type=OrderType.MARKET,
            segment="FNO"
        ))
        
        self._entered_today = True
        LOG.info(f"Generated entry orders: Buy {self.buy_strike}CE, Sell {self.sell_strike}CE")
        
        return orders
    
    def should_exit(self, position: Position, market_data: MarketData) -> bool:
        """Check exit conditions - exit at exit time."""
        return self._is_exit_time(market_data.timestamp)
    
    def get_exit_orders(self, position: Any, market_data: MarketData) -> List[Order]:
        """Generate exit orders to close the spread."""
        orders = []
        
        # Extract symbols from the position object (SpreadPosition)
        # We rely on the position object passed from position_manager
        buy_symbol = getattr(position, "long_symbol", self.buy_symbol)
        sell_symbol = getattr(position, "short_symbol", self.sell_symbol)
        
        if not buy_symbol or not sell_symbol:
            LOG.error("Cannot generate exit orders: Symbols missing in position")
            return orders
        
        # Sell the long leg
        orders.append(Order(
            symbol=buy_symbol,
            exchange="NSE",
            side=OrderSide.SELL,  # Sell to close long
            quantity=self.lot_size,
            order_type=OrderType.MARKET,
            segment="FNO"
        ))
        
        # Buy the short leg
        orders.append(Order(
            symbol=sell_symbol,
            exchange="NSE",
            side=OrderSide.BUY,  # Buy to close short
            quantity=self.lot_size,
            order_type=OrderType.MARKET,
            segment="FNO"
        ))
        
        LOG.info(f"Generated exit orders for {buy_symbol} & {sell_symbol}")
        return orders
    
    def calculate_max_contracts(self, net_debit: float) -> int:
        """Calculate max contracts based on capital and risk."""
        return compute_max_contracts(
            capital=self.capital,
            risk_pct=self.risk_pct,
            net_debit=net_debit,
            lot_size=self.lot_size
        )
