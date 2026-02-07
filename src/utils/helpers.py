"""
Common utility functions for the trading bot.
"""

import math
from datetime import datetime, timedelta
from typing import List, Tuple, Optional


def round_to_strike(price: float, step: int = 50) -> int:
    """
    Round price to nearest strike price.
    
    Args:
        price: Current price
        step: Strike step (default 50 for NIFTY)
        
    Returns:
        Nearest strike price
    """
    return round(price / step) * step


def find_atm_strike(spot_price: float, strikes: List[float]) -> float:
    """
    Find at-the-money strike from available strikes.
    
    Args:
        spot_price: Current spot price
        strikes: List of available strikes
        
    Returns:
        ATM strike price
    """
    if not strikes:
        raise ValueError("No strikes provided")
    return min(strikes, key=lambda s: abs(s - spot_price))


def compute_max_contracts(
    capital: float,
    risk_pct: float,
    net_debit: float,
    lot_size: int,
    brokerage_per_order: float = 20.0,
    orders_required: int = 2
) -> int:
    """
    Compute maximum number of contracts based on risk parameters.
    
    Args:
        capital: Total trading capital
        risk_pct: Risk percentage (0-1)
        net_debit: Net debit per spread
        lot_size: Lot size of contract
        brokerage_per_order: Brokerage per order
        orders_required: Number of orders for the trade
        
    Returns:
        Maximum contracts to trade
    """
    if net_debit <= 0 or lot_size <= 0:
        return 0
    
    risk_amount = capital * risk_pct
    per_contract_risk = net_debit * lot_size
    total_brokerage = brokerage_per_order * orders_required
    
    max_contracts = math.floor((risk_amount - total_brokerage) / per_contract_risk)
    return max(0, max_contracts)


def parse_time(time_str: str) -> Tuple[int, int]:
    """
    Parse time string to hour and minute.
    
    Args:
        time_str: Time in "HH:MM" format
        
    Returns:
        Tuple of (hour, minute)
    """
    parts = time_str.split(":")
    return int(parts[0]), int(parts[1])


def is_market_open(current_time: Optional[datetime] = None) -> bool:
    """
    Check if market is open (9:15 AM to 3:30 PM IST on weekdays).
    
    Args:
        current_time: Time to check (defaults to now)
        
    Returns:
        True if market is open
    """
    if current_time is None:
        current_time = datetime.now()
    
    # Check weekday (0 = Monday, 6 = Sunday)
    if current_time.weekday() >= 5:
        return False
    
    # Market hours: 9:15 to 15:30
    market_open = current_time.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close = current_time.replace(hour=15, minute=30, second=0, microsecond=0)
    
    return market_open <= current_time <= market_close


def get_next_market_open(current_time: Optional[datetime] = None) -> datetime:
    """
    Get the next market opening time.
    
    Args:
        current_time: Reference time (defaults to now)
        
    Returns:
        Next market opening datetime
    """
    if current_time is None:
        current_time = datetime.now()
    
    next_open = current_time.replace(hour=9, minute=15, second=0, microsecond=0)
    
    # If past today's opening, move to next day
    if current_time.time() >= datetime.strptime("09:15", "%H:%M").time():
        next_open += timedelta(days=1)
    
    # Skip weekends
    while next_open.weekday() >= 5:
        next_open += timedelta(days=1)
    
    return next_open


def format_currency(amount: float) -> str:
    """Format amount as Indian currency."""
    return f"₹{amount:,.2f}"


def extract_strike_from_symbol(symbol: str) -> Optional[float]:
    """
    Extract strike price from option symbol.
    
    Args:
        symbol: Option trading symbol (e.g., "NSE-NIFTY-02Jan25-24000-CE")
        
    Returns:
        Strike price or None
    """
    try:
        parts = symbol.split("-")
        if len(parts) >= 4:
            return float(parts[3])
    except (ValueError, IndexError):
        pass
    return None


def is_call_option(symbol: str) -> bool:
    """Check if symbol is a call option."""
    return symbol.upper().endswith("CE")


def is_put_option(symbol: str) -> bool:
    """Check if symbol is a put option."""
    return symbol.upper().endswith("PE")
