"""
Order management module.
Handles order placement, tracking, and execution.
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ..api import client
from ..config import settings
from ..strategies.base import Order, OrderSide

LOG = logging.getLogger(__name__)


class OrderStatus(Enum):
    """Order status enumeration."""
    PENDING = "PENDING"
    PLACED = "PLACED"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    SIMULATED = "SIMULATED"


@dataclass
class OrderRecord:
    """Record of an order with its status and fill details."""
    order: Order
    order_id: Optional[str] = None
    status: OrderStatus = OrderStatus.PENDING
    fill_price: Optional[float] = None
    fill_quantity: int = 0
    placed_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None


class OrderManager:
    """Manages order placement and tracking."""
    
    def __init__(self):
        self._client = client
        self._orders: Dict[str, OrderRecord] = {}
        self._order_counter = 0
    
    def place_order(
        self,
        order: Order,
        slippage: float = 0.0
    ) -> OrderRecord:
        """
        Place an order through the API.
        
        Args:
            order: Order to place
            slippage: Slippage points for simulation
            
        Returns:
            OrderRecord with status
        """
        self._order_counter += 1
        record = OrderRecord(order=order, placed_at=datetime.now())
        
        try:
            if settings.mode == "PAPER":
                # Simulate order in paper mode
                record.order_id = f"PAPER_{self._order_counter}"
                record.status = OrderStatus.SIMULATED
                record.fill_quantity = order.quantity
                record.filled_at = datetime.now()
                LOG.info(f"[PAPER] Simulated order: {order.side.value} {order.quantity} {order.symbol}")
            else:
                # Place real order
                response = self._client.place_order(
                    trading_symbol=order.symbol,
                    exchange=order.exchange,
                    segment=order.segment,
                    transaction_type=order.side.value,
                    quantity=order.quantity,
                    order_type=order.order_type.value,
                    price=order.price,
                    product=order.product
                )
                
                record.order_id = response.get("order_id")
                record.status = OrderStatus.PLACED
                LOG.info(f"Placed order {record.order_id}: {order.side.value} {order.quantity} {order.symbol}")
            
            self._orders[record.order_id] = record
            
        except Exception as e:
            record.status = OrderStatus.REJECTED
            record.rejection_reason = str(e)
            LOG.error(f"Order rejected: {e}")
        
        return record
    
    def place_orders(
        self,
        orders: List[Order],
        slippage: float = 0.0
    ) -> List[OrderRecord]:
        """Place multiple orders."""
        return [self.place_order(order, slippage) for order in orders]
    
    def get_order_status(self, order_id: str) -> Optional[OrderRecord]:
        """Get order record by ID."""
        return self._orders.get(order_id)
    
    def get_all_orders(self) -> List[OrderRecord]:
        """Get all order records."""
        return list(self._orders.values())
    
    def get_filled_orders(self) -> List[OrderRecord]:
        """Get all filled orders."""
        return [
            record for record in self._orders.values()
            if record.status in (OrderStatus.FILLED, OrderStatus.SIMULATED)
        ]
    
    def refresh_order_status(self, order_id: str) -> Optional[OrderRecord]:
        """Refresh order status from API."""
        if settings.mode == "PAPER":
            return self._orders.get(order_id)
        
        record = self._orders.get(order_id)
        if not record:
            return None
        
        try:
            orders = self._client.get_orders()
            for order_data in orders:
                if order_data.get("order_id") == order_id:
                    status_str = order_data.get("status", "").upper()
                    if "COMPLETE" in status_str or "FILLED" in status_str:
                        record.status = OrderStatus.FILLED
                        record.fill_price = order_data.get("average_price")
                        record.fill_quantity = order_data.get("filled_quantity")
                        record.filled_at = datetime.now()
                    elif "CANCEL" in status_str:
                        record.status = OrderStatus.CANCELLED
                    elif "REJECT" in status_str:
                        record.status = OrderStatus.REJECTED
                        record.rejection_reason = order_data.get("rejection_reason")
                    break
        except Exception as e:
            LOG.error(f"Failed to refresh order status: {e}")
        
        return record
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        if settings.mode == "PAPER":
            record = self._orders.get(order_id)
            if record:
                record.status = OrderStatus.CANCELLED
                return True
            return False
        
        try:
            self._client.api.cancel_order(order_id=order_id)
            record = self._orders.get(order_id)
            if record:
                record.status = OrderStatus.CANCELLED
            return True
        except Exception as e:
            LOG.error(f"Failed to cancel order {order_id}: {e}")
            return False
    
    def calculate_brokerage(self, orders: List[Order]) -> float:
        """Calculate total brokerage for orders."""
        return len(orders) * settings.brokerage_per_order
    
    def clear_orders(self) -> None:
        """Clear all order records."""
        self._orders.clear()


# Global instance
order_manager = OrderManager()
