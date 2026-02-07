"""
Position management module.
Tracks open positions and calculates P&L.
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from ..strategies.base import Position, OrderSide
from ..config import settings

LOG = logging.getLogger(__name__)


@dataclass
class SpreadPosition:
    """Represents a spread position with multiple legs."""
    spread_id: str
    underlying: str
    strategy_name: str
    
    # Leg details
    long_symbol: str
    short_symbol: str
    long_price: float
    short_price: float
    quantity: int
    lot_size: int
    
    # Timing
    entry_time: datetime
    exit_time: Optional[datetime] = None
    
    # P&L
    exit_long_price: float = 0.0
    exit_short_price: float = 0.0
    realized_pnl: float = 0.0
    brokerage: float = 0.0
    
    @property
    def net_debit(self) -> float:
        """Net debit per lot at entry."""
        return self.long_price - self.short_price
    
    @property
    def total_cost(self) -> float:
        """Total cost of position."""
        return self.net_debit * self.quantity * self.lot_size
    
    @property
    def is_open(self) -> bool:
        """Check if position is still open."""
        return self.exit_time is None
    
    def close(
        self,
        exit_long: float,
        exit_short: float,
        brokerage: float = 0.0
    ) -> float:
        """
        Close the position and calculate P&L.
        
        Args:
            exit_long: Exit price for long leg
            exit_short: Exit price for short leg
            brokerage: Total brokerage for exit
            
        Returns:
            Net P&L after brokerage
        """
        self.exit_time = datetime.now()
        self.exit_long_price = exit_long
        self.exit_short_price = exit_short
        self.brokerage += brokerage
        
        # Calculate P&L
        entry_value = (self.long_price - self.short_price) * self.quantity * self.lot_size
        exit_value = (exit_long - exit_short) * self.quantity * self.lot_size
        
        # For bull call spread, profit = exit_value - entry_value
        gross_pnl = exit_value - entry_value
        self.realized_pnl = gross_pnl - self.brokerage
        
        return self.realized_pnl
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for reporting."""
        return {
            "spread_id": self.spread_id,
            "underlying": self.underlying,
            "strategy": self.strategy_name,
            "long_symbol": self.long_symbol,
            "short_symbol": self.short_symbol,
            "entry_long": self.long_price,
            "entry_short": self.short_price,
            "net_debit": self.net_debit,
            "quantity": self.quantity,
            "lot_size": self.lot_size,
            "entry_time": self.entry_time.isoformat(),
            "exit_time": self.exit_time.isoformat() if self.exit_time else None,
            "exit_long": self.exit_long_price,
            "exit_short": self.exit_short_price,
            "realized_pnl": self.realized_pnl,
            "brokerage": self.brokerage,
        }


class PositionManager:
    """Manages trading positions."""
    
    def __init__(self):
        self._positions: Dict[str, SpreadPosition] = {}
        self._closed_positions: List[SpreadPosition] = []
        self._position_counter = 0
    
    def open_spread(
        self,
        underlying: str,
        strategy_name: str,
        long_symbol: str,
        short_symbol: str,
        long_price: float,
        short_price: float,
        quantity: int,
        lot_size: int,
        brokerage: float = 0.0
    ) -> SpreadPosition:
        """
        Open a new spread position.
        
        Args:
            underlying: Underlying symbol
            strategy_name: Name of the strategy
            long_symbol: Long leg symbol
            short_symbol: Short leg symbol
            long_price: Long leg entry price
            short_price: Short leg entry price
            quantity: Number of spreads
            lot_size: Lot size per spread
            brokerage: Entry brokerage
            
        Returns:
            New SpreadPosition
        """
        self._position_counter += 1
        spread_id = f"SPREAD_{self._position_counter}"
        
        position = SpreadPosition(
            spread_id=spread_id,
            underlying=underlying,
            strategy_name=strategy_name,
            long_symbol=long_symbol,
            short_symbol=short_symbol,
            long_price=long_price,
            short_price=short_price,
            quantity=quantity,
            lot_size=lot_size,
            entry_time=datetime.now(),
            brokerage=brokerage
        )
        
        self._positions[spread_id] = position
        LOG.info(f"Opened spread {spread_id}: {long_symbol}/{short_symbol} @ {long_price:.2f}/{short_price:.2f}")
        
        return position
    
    def close_spread(
        self,
        spread_id: str,
        exit_long: float,
        exit_short: float,
        brokerage: float = 0.0
    ) -> Optional[float]:
        """
        Close a spread position.
        
        Args:
            spread_id: ID of spread to close
            exit_long: Exit price for long leg
            exit_short: Exit price for short leg
            brokerage: Exit brokerage
            
        Returns:
            Realized P&L or None if not found
        """
        position = self._positions.get(spread_id)
        if not position:
            LOG.warning(f"Spread {spread_id} not found")
            return None
        
        pnl = position.close(exit_long, exit_short, brokerage)
        
        del self._positions[spread_id]
        self._closed_positions.append(position)
        
        LOG.info(f"Closed spread {spread_id}: P&L = {pnl:.2f}")
        return pnl
    
    def get_open_positions(self) -> List[SpreadPosition]:
        """Get all open positions."""
        return list(self._positions.values())
    
    def get_closed_positions(self) -> List[SpreadPosition]:
        """Get all closed positions."""
        return self._closed_positions.copy()
    
    def get_position(self, spread_id: str) -> Optional[SpreadPosition]:
        """Get position by ID."""
        return self._positions.get(spread_id)
    
    def get_total_realized_pnl(self) -> float:
        """Get total realized P&L from closed positions."""
        return sum(p.realized_pnl for p in self._closed_positions)
    
    def get_total_exposure(self) -> float:
        """Get total capital at risk in open positions."""
        return sum(p.total_cost for p in self._positions.values())
    
    def has_open_positions(self) -> bool:
        """Check if there are open positions."""
        return len(self._positions) > 0
    
    def get_stats(self) -> Dict:
        """Get position statistics."""
        closed = self._closed_positions
        if not closed:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "avg_pnl": 0.0
            }
        
        winners = [p for p in closed if p.realized_pnl > 0]
        losers = [p for p in closed if p.realized_pnl < 0]
        total_pnl = sum(p.realized_pnl for p in closed)
        
        return {
            "total_trades": len(closed),
            "winning_trades": len(winners),
            "losing_trades": len(losers),
            "win_rate": len(winners) / len(closed) if closed else 0.0,
            "total_pnl": total_pnl,
            "avg_pnl": total_pnl / len(closed) if closed else 0.0
        }
    
    def clear(self) -> None:
        """Clear all positions."""
        self._positions.clear()
        self._closed_positions.clear()


# Global instance
position_manager = PositionManager()
