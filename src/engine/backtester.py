"""
Backtesting engine.
Simulates strategy execution over historical data with detailed logging.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import pandas as pd

from ..config import settings
from ..data import historical_fetcher, instrument_manager
from ..strategies import BaseStrategy, MarketData, BullCallSpreadStrategy
from ..execution import position_manager, order_manager
from ..utils import format_currency

LOG = logging.getLogger(__name__)


def calculate_weekly_expiries(from_date: str, to_date: str, underlying: str = "NIFTY") -> List[str]:
    """
    Calculate weekly expiry dates for a given date range.
    
    NIFTY/BANKNIFTY options expire every Thursday.
    For backtesting historical periods where API doesn't have data,
    this function generates what the expiry dates would have been.
    
    Args:
        from_date: Start date in "YYYY-MM-DD" format
        to_date: End date in "YYYY-MM-DD" format  
        underlying: NIFTY or BANKNIFTY
        
    Returns:
        List of Thursday expiry dates covering the range
    """
    start = datetime.strptime(from_date, "%Y-%m-%d")
    end = datetime.strptime(to_date, "%Y-%m-%d")
    
    # Add buffer to ensure we have expiries beyond our date range
    end_buffer = end + timedelta(days=60)
    
    expiries = []
    current = start
    
    # Find next Thursday (Thursday = weekday 3)
    days_until_thursday = (3 - current.weekday()) % 7
    if days_until_thursday == 0:
        # If we're on Thursday, include it
        pass
    current = current + timedelta(days=days_until_thursday)
    
    # Generate all Thursdays (weekly expiries)
    while current <= end_buffer:
        expiries.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=7)
    
    LOG.info(f"📅 Calculated {len(expiries)} weekly expiries for backtest period")
    if expiries:
        LOG.info(f"   First 5: {expiries[:5]}")
    return expiries


class BacktestResult:
    """Container for backtest results."""
    
    def __init__(self):
        self.trades: List[Dict[str, Any]] = []
        self.daily_pnl: Dict[str, float] = {}
        self.total_pnl: float = 0.0
        self.total_trades: int = 0
        self.winning_trades: int = 0
        self.losing_trades: int = 0
        self.max_drawdown: float = 0.0
        self.sharpe_ratio: float = 0.0
    
    @property
    def win_rate(self) -> float:
        if self.total_trades == 0:
            return 0.0
        return self.winning_trades / self.total_trades
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert trades to DataFrame."""
        return pd.DataFrame(self.trades)
    
    def summary(self) -> str:
        """Generate summary string."""
        return f"""
================================================================================
                            BACKTEST SUMMARY
================================================================================
Total Trades:     {self.total_trades}
Winning Trades:   {self.winning_trades}
Losing Trades:    {self.losing_trades}
Win Rate:         {self.win_rate:.1%}
Total P&L:        {format_currency(self.total_pnl)}
Max Drawdown:     {format_currency(self.max_drawdown)}
================================================================================
"""


class Backtester:
    """
    Backtesting engine that simulates strategy execution with detailed logging.
    """
    
    def __init__(
        self,
        strategy: Optional[BaseStrategy] = None,
        slippage: float = None,
        use_calculated_expiries: bool = True
    ):
        self.strategy = strategy or BullCallSpreadStrategy()
        self.slippage = slippage or settings.slippage_points
        self.use_calculated_expiries = use_calculated_expiries
        self._historical = historical_fetcher
        self._instruments = instrument_manager
    
    def run(
        self,
        underlying: str,
        from_date: str,
        to_date: str
    ) -> BacktestResult:
        """
        Run backtest over date range.
        
        Args:
            underlying: Underlying symbol (e.g., "NIFTY")
            from_date: Start date in "YYYY-MM-DD" format
            to_date: End date in "YYYY-MM-DD" format
            
        Returns:
            BacktestResult with all trade details
        """
        result = BacktestResult()
        position_manager.clear()
        order_manager.clear_orders()
        
        LOG.info("=" * 80)
        LOG.info("BACKTEST STARTED")
        LOG.info("=" * 80)
        LOG.info(f"Underlying: {underlying}")
        LOG.info(f"Date Range: {from_date} to {to_date}")
        LOG.info(f"Strategy: {self.strategy.name}")
        LOG.info(f"Spread Width: {self.strategy.spread_width}")
        LOG.info(f"Entry Time: {settings.entry_time}")
        LOG.info(f"Exit Time: {settings.exit_time}")
        LOG.info(f"Capital: {format_currency(settings.capital)}")
        LOG.info(f"Risk %: {settings.risk_pct:.1%}")
        LOG.info(f"Slippage: {self.slippage} points")
        LOG.info("=" * 80)
        
        # Parse dates
        start = datetime.strptime(from_date, "%Y-%m-%d")
        end = datetime.strptime(to_date, "%Y-%m-%d")
        current = start
        
        # Get expiries
        # For historical backtesting, we CALCULATE expiries based on the trading dates
        # because the API only returns future expiries from today, not historical ones
        if self.use_calculated_expiries:
            LOG.info("📅 Using CALCULATED weekly expiries (for historical backtesting)")
            expiries = calculate_weekly_expiries(from_date, to_date, underlying)
        else:
            # Try to get from API (only works for dates near current date)
            LOG.info("📅 Fetching expiries from API...")
            expiries = self._historical.get_expiries(underlying, month=1)
            if not expiries:
                LOG.warning("⚠️  No weekly expiries from API, falling back to calculated")
                expiries = calculate_weekly_expiries(from_date, to_date, underlying)
        
        if not expiries:
            LOG.error("❌ No expiries available")
            return result
        
        LOG.info(f"📅 Found {len(expiries)} expiry dates")
        LOG.info(f"   First 5 expiries: {expiries[:5]}")
        
        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            
            # Skip weekends
            if current.weekday() >= 5:
                LOG.debug(f"⏭️  {date_str}: Weekend - Skipping")
                current += timedelta(days=1)
                continue
            
            LOG.info("-" * 80)
            LOG.info(f"📆 PROCESSING DATE: {date_str}")
            LOG.info("-" * 80)
            
            try:
                trade_result = self._run_day(underlying, date_str, expiries)
                if trade_result:
                    result.trades.append(trade_result)
                    result.daily_pnl[date_str] = trade_result["pnl_after_brokerage"]
                    LOG.info(f"✅ Trade completed: P&L = {format_currency(trade_result['pnl_after_brokerage'])}")
                else:
                    LOG.info(f"⚠️  No trade executed on {date_str}")
                    
            except Exception as e:
                LOG.error(f"❌ Error on {date_str}: {e}", exc_info=True)
            
            current += timedelta(days=1)
        
        # Calculate statistics
        self._calculate_stats(result)
        
        LOG.info("=" * 80)
        LOG.info(result.summary())
        return result
    
    def _find_nearest_expiry(self, expiries: List[str], current_date: str) -> Optional[str]:
        """
        Find the NEAREST expiry that is in the future (relative to current_date).
        Prefers expiries within 7 days for weekly trading.
        
        Args:
            expiries: List of available expiry dates
            current_date: Current trading date
            
        Returns:
            Nearest expiry date or None
        """
        current = pd.Timestamp(current_date)
        
        # Filter future expiries only
        future_expiries = []
        for exp in expiries:
            exp_date = pd.Timestamp(exp)
            days_to_expiry = (exp_date - current).days
            
            # Only consider expiries that are AFTER the current trading date
            if days_to_expiry > 0:
                future_expiries.append((exp, days_to_expiry))
        
        if not future_expiries:
            return None
        
        # Sort by days to expiry and return the nearest
        future_expiries.sort(key=lambda x: x[1])
        nearest = future_expiries[0]
        
        LOG.info(f"📅 Selected expiry: {nearest[0]} ({nearest[1]} days away)")
        return nearest[0]
    
    def _run_day(
        self,
        underlying: str,
        date_str: str,
        expiries: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Run backtest for a single day with detailed logging."""
        
        # Find nearest expiry (from calculated expiries)
        nearest_expiry = self._find_nearest_expiry(expiries, date_str)
        
        if not nearest_expiry:
            LOG.warning(f"⚠️  No future expiries available for {date_str}")
            return None
        
        # Get spot price
        LOG.info(f"📊 Fetching spot price for {underlying}...")
        spot_price = self._historical.get_spot_price(underlying, date_str)
        
        if not spot_price:
            LOG.warning(f"⚠️  Could not fetch spot price for {date_str}")
            return None
        
        LOG.info(f"📊 {underlying} Spot Price: {spot_price:.2f}")
        
        # Get option chain - use the calculated expiry
        LOG.info(f"📋 Fetching option chain for expiry: {nearest_expiry}...")
        option_chain = self._historical.get_option_chain(underlying, nearest_expiry)
        
        if not option_chain.get("calls"):
            # For historical dates, option chain might not be available
            # We'll simulate by generating contract symbols
            LOG.warning(f"⚠️  No option chain from API, simulating contracts...")
            option_chain = self._simulate_option_chain(underlying, nearest_expiry, spot_price)
        
        num_calls = len(option_chain.get("calls", []))
        num_puts = len(option_chain.get("puts", []))
        LOG.info(f"📋 Option chain: {num_calls} calls, {num_puts} puts")
        
        # Create market data
        entry_time = datetime.strptime(
            f"{date_str} {settings.entry_time}:00",
            "%Y-%m-%d %H:%M:%S"
        )
        
        market_data = MarketData(
            underlying=underlying,
            spot_price=spot_price,
            timestamp=entry_time,
            option_chain=option_chain,
            expiries=expiries,
            current_expiry=nearest_expiry
        )
        
        # Check entry conditions
        LOG.info(f"🔍 Checking entry conditions at {settings.entry_time}...")
        
        if not self.strategy.should_enter(market_data):
            LOG.info(f"❌ Entry conditions not met")
            return None
        
        LOG.info(f"✅ Entry conditions met!")
        
        # Get entry orders
        entry_orders = self.strategy.get_entry_orders(market_data)
        if len(entry_orders) < 2:
            LOG.warning(f"⚠️  Insufficient entry orders generated: {len(entry_orders)}")
            return None
        
        # Get strike details
        buy_strike = self.strategy.buy_strike
        sell_strike = self.strategy.sell_strike
        
        LOG.info(f"📍 ATM Strike determined: {buy_strike}")
        LOG.info(f"📍 OTM Strike (ATM + {self.strategy.spread_width}): {sell_strike}")
        
        # Extract symbols
        buy_order = next((o for o in entry_orders if o.side.value == "BUY"), None)
        sell_order = next((o for o in entry_orders if o.side.value == "SELL"), None)
        
        if not buy_order or not sell_order:
            LOG.error("❌ Could not find buy/sell orders")
            return None
        
        LOG.info(f"📝 Buy leg: {buy_order.symbol}")
        LOG.info(f"📝 Sell leg: {sell_order.symbol}")
        
        # Calculate simulated prices based on intrinsic value + time value
        buy_intrinsic = max(0, spot_price - buy_strike)
        sell_intrinsic = max(0, spot_price - sell_strike)
        
        # Add time value (simplified approximation)
        days_to_exp = (pd.Timestamp(nearest_expiry) - pd.Timestamp(date_str)).days
        time_value_factor = max(0.01, days_to_exp / 30.0) * 0.02
        
        time_value_buy = max(10, abs(spot_price - buy_strike) * time_value_factor)
        time_value_sell = max(5, abs(spot_price - sell_strike) * time_value_factor * 0.5)
        
        buy_price = buy_intrinsic + time_value_buy
        sell_price = sell_intrinsic + time_value_sell
        
        LOG.info(f"💰 ENTRY PRICE CALCULATION:")
        LOG.info(f"   Days to expiry: {days_to_exp}")
        LOG.info(f"   Buy leg ({buy_strike}CE):")
        LOG.info(f"     - Intrinsic: {buy_intrinsic:.2f}")
        LOG.info(f"     - Time value: {time_value_buy:.2f}")
        LOG.info(f"     - Theoretical: {buy_price:.2f}")
        LOG.info(f"   Sell leg ({sell_strike}CE):")
        LOG.info(f"     - Intrinsic: {sell_intrinsic:.2f}")
        LOG.info(f"     - Time value: {time_value_sell:.2f}")
        LOG.info(f"     - Theoretical: {sell_price:.2f}")
        
        # Apply slippage
        entry_buy = buy_price + self.slippage
        entry_sell = sell_price - self.slippage
        net_debit = entry_buy - entry_sell
        
        LOG.info(f"💰 AFTER SLIPPAGE ({self.slippage} pts):")
        LOG.info(f"   Buy filled at: {entry_buy:.2f}")
        LOG.info(f"   Sell filled at: {entry_sell:.2f}")
        LOG.info(f"   Net Debit: {net_debit:.2f}")
        
        lot_size = self._instruments.get_lot_size(underlying)
        LOG.info(f"📦 Lot size: {lot_size}")
        
        # Open position
        spread = position_manager.open_spread(
            underlying=underlying,
            strategy_name=self.strategy.name,
            long_symbol=buy_order.symbol,
            short_symbol=sell_order.symbol,
            long_price=entry_buy,
            short_price=entry_sell,
            quantity=1,
            lot_size=lot_size,
            brokerage=settings.brokerage_per_order * 2
        )
        
        LOG.info(f"📈 POSITION OPENED: {spread.spread_id}")
        LOG.info(f"   Entry cost: {format_currency(spread.total_cost)}")
        
        # Simulate exit at EXIT_TIME
        LOG.info(f"⏰ Simulating exit at {settings.exit_time}...")
        
        # Simulate price movement (5% time decay for intraday)
        time_decay_factor = 0.95
        exit_buy = buy_price * time_decay_factor
        exit_sell = sell_price * time_decay_factor
        
        LOG.info(f"💰 EXIT PRICE CALCULATION (5% time decay):")
        LOG.info(f"   Buy leg exit: {exit_buy:.2f}")
        LOG.info(f"   Sell leg exit: {exit_sell:.2f}")
        LOG.info(f"   Exit Net: {exit_buy - exit_sell:.2f}")
        
        # Close position
        pnl = position_manager.close_spread(
            spread_id=spread.spread_id,
            exit_long=exit_buy,
            exit_short=exit_sell,
            brokerage=settings.brokerage_per_order * 2
        )
        
        total_brokerage = settings.brokerage_per_order * 4
        gross_pnl = pnl + total_brokerage
        
        LOG.info(f"📉 POSITION CLOSED:")
        LOG.info(f"   Gross P&L: {format_currency(gross_pnl)}")
        LOG.info(f"   Brokerage: {format_currency(total_brokerage)}")
        LOG.info(f"   Net P&L: {format_currency(pnl)}")
        
        return {
            "date": date_str,
            "entry_time": entry_time,
            "expiry": nearest_expiry,
            "days_to_expiry": days_to_exp,
            "underlying": underlying,
            "spot_price": spot_price,
            "buy_strike": buy_strike,
            "sell_strike": sell_strike,
            "buy_symbol": buy_order.symbol if buy_order else "",
            "sell_symbol": sell_order.symbol if sell_order else "",
            "entry_buy": entry_buy,
            "entry_sell": entry_sell,
            "entry_net_debit": net_debit,
            "exit_buy": exit_buy,
            "exit_sell": exit_sell,
            "exit_net_debit": exit_buy - exit_sell,
            "lot_size": lot_size,
            "gross_pnl": gross_pnl,
            "brokerage": total_brokerage,
            "pnl_after_brokerage": pnl
        }
    
    def _simulate_option_chain(
        self, 
        underlying: str, 
        expiry: str, 
        spot_price: float
    ) -> Dict[str, List[str]]:
        """
        Simulate option chain for historical dates where API data isn't available.
        Generates strike prices around the spot price.
        """
        # Round spot to nearest 50
        base_strike = round(spot_price / 50) * 50
        
        # Generate strikes from -500 to +500 around ATM
        strikes = [base_strike + (i * 50) for i in range(-10, 11)]
        
        # Format expiry for symbol (e.g., "2025-01-02" -> "02Jan25")
        exp_date = datetime.strptime(expiry, "%Y-%m-%d")
        exp_str = exp_date.strftime("%d%b%y")
        
        calls = [f"NSE-{underlying}-{exp_str}-{strike}-CE" for strike in strikes]
        puts = [f"NSE-{underlying}-{exp_str}-{strike}-PE" for strike in strikes]
        
        return {"calls": calls, "puts": puts}
    
    def _calculate_stats(self, result: BacktestResult) -> None:
        """Calculate backtest statistics."""
        if not result.trades:
            return
        
        result.total_trades = len(result.trades)
        result.total_pnl = sum(t["pnl_after_brokerage"] for t in result.trades)
        
        result.winning_trades = sum(
            1 for t in result.trades if t["pnl_after_brokerage"] > 0
        )
        result.losing_trades = sum(
            1 for t in result.trades if t["pnl_after_brokerage"] < 0
        )
        
        # Calculate max drawdown
        cumulative = 0.0
        peak = 0.0
        for trade in result.trades:
            cumulative += trade["pnl_after_brokerage"]
            peak = max(peak, cumulative)
            drawdown = peak - cumulative
            result.max_drawdown = max(result.max_drawdown, drawdown)


# Convenience function
def run_backtest(
    underlying: str = None,
    from_date: str = None,
    to_date: str = None,
    strategy: Optional[BaseStrategy] = None,
    use_calculated_expiries: bool = True
) -> BacktestResult:
    """
    Run a backtest with default settings.
    
    Args:
        underlying: Underlying symbol (default from settings)
        from_date: Start date (default from settings)
        to_date: End date (default from settings)
        strategy: Strategy to test (default BullCallSpread)
        use_calculated_expiries: Use calculated weekly expiries (True for historical data)
        
    Returns:
        BacktestResult
    """
    backtester = Backtester(strategy=strategy, use_calculated_expiries=use_calculated_expiries)
    return backtester.run(
        underlying=underlying or settings.underlying,
        from_date=from_date or settings.from_date,
        to_date=to_date or settings.to_date
    )
