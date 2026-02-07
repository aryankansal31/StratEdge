"""
Base strategy interface defining the contract for all trading strategies.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class OrderSide(Enum):
    """Order side enumeration."""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    """Order type enumeration."""
    MARKET = "MARKET"
    LIMIT = "LIMIT"


@dataclass
class Order:
    """Represents a trading order."""
    symbol: str
    exchange: str
    side: OrderSide
    quantity: int
    order_type: OrderType = OrderType.MARKET
    price: Optional[float] = None
    segment: str = "FNO"
    product: str = "INTRADAY"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert order to dictionary for API submission."""
        result = {
            "trading_symbol": self.symbol,
            "exchange": self.exchange,
            "transaction_type": self.side.value,
            "quantity": self.quantity,
            "order_type": self.order_type.value,
            "segment": self.segment,
            "product": self.product
        }
        if self.price and self.order_type == OrderType.LIMIT:
            result["price"] = self.price
        return result


@dataclass
class Position:
    """Represents an open position."""
    symbol: str
    exchange: str
    quantity: int
    entry_price: float
    entry_time: datetime
    side: OrderSide
    current_price: Optional[float] = None
    unrealized_pnl: float = 0.0
    
    @property
    def is_long(self) -> bool:
        return self.side == OrderSide.BUY
    
    @property
    def is_short(self) -> bool:
        return self.side == OrderSide.SELL


@dataclass
class MarketData:
    """Market data snapshot for strategy decision-making."""
    underlying: str
    spot_price: float
    timestamp: datetime
    option_chain: Dict[str, List[str]]
    expiries: List[str]
    current_expiry: str
    
    # Optional additional data
    vix: Optional[float] = None
    ohlcv: Optional[Dict[str, Any]] = None


class BaseStrategy(ABC):
    """
    Abstract base class for trading strategies.
    All strategies must implement these methods.
    """
    
    def __init__(self, name: str):
        self.name = name
        self.positions: List[Position] = []
    
    @abstractmethod
    def should_enter(self, market_data: MarketData) -> bool:
        """
        Determine if strategy should enter a trade.
        
        Args:
            market_data: Current market data
            
        Returns:
            True if should enter
        """
        pass
    
    @abstractmethod
    def get_entry_orders(self, market_data: MarketData) -> List[Order]:
        """
        Generate entry orders based on market data.
        
        Args:
            market_data: Current market data
            
        Returns:
            List of orders to place
        """
        pass
    
    @abstractmethod
    def should_exit(self, position: Position, market_data: MarketData) -> bool:
        """
        Determine if a position should be exited.
        
        Args:
            position: Current position
            market_data: Current market data
            
        Returns:
            True if should exit
        """
        pass
    
    @abstractmethod
    def get_exit_orders(self, position: Position, market_data: MarketData) -> List[Order]:
        """
        Generate exit orders for a position.
        
        Args:
            position: Position to exit
            market_data: Current market data
            
        Returns:
            List of orders to place
        """
        pass
    
    def on_order_filled(self, order: Order, fill_price: float) -> None:
        """Called when an order is filled. Override in subclass if needed."""
        pass
    
    def on_position_opened(self, position: Position) -> None:
        """Called when a new position is opened. Override in subclass if needed."""
        pass
    
    def on_position_closed(self, position: Position, pnl: float) -> None:
        """Called when a position is closed. Override in subclass if needed."""
        pass
