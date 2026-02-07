"""
Groww API Client wrapper providing unified interface for all API operations.
Handles authentication, connection management, and error handling.
"""

import logging
from typing import Optional, Dict, Any, List
import pyotp
from growwapi import GrowwAPI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..config import settings

LOG = logging.getLogger(__name__)


class GrowwClient:
    """Singleton wrapper for Groww API client with automatic authentication."""
    
    _instance: Optional["GrowwClient"] = None
    _api: Optional[GrowwAPI] = None
    
    # Exchange and segment constants
    EXCHANGE_NSE = "NSE"
    EXCHANGE_BSE = "BSE"
    SEGMENT_CASH = "CASH"
    SEGMENT_FNO = "FNO"
    
    def __new__(cls) -> "GrowwClient":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._api is None:
            self._api = self._create_client()
    
    def _create_client(self) -> GrowwAPI:
        """Initialize and authenticate Groww API client."""
        try:
            # Generate TOTP for authentication
            totp_gen = pyotp.TOTP(settings.api_secret)
            totp = totp_gen.now()
            
            # Get access token
            access_token = GrowwAPI.get_access_token(
                api_key=settings.api_key, 
                totp=totp
            )
            
            # Initialize client
            client = GrowwAPI(access_token)
            LOG.info("Groww API client initialized successfully")
            return client
            
        except Exception as e:
            LOG.error(f"Failed to initialize Groww API client: {e}")
            raise RuntimeError(f"Groww API authentication failed: {e}") from e
    
    def refresh_token(self) -> None:
        """Refresh the API client authentication."""
        self._api = self._create_client()
        LOG.info("Groww API token refreshed")
    
    # ==================== Market Data APIs ====================
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_ltp(self, symbols: str, segment: str = "CASH") -> Dict[str, float]:
        """
        Get last traded price for instruments.
        
        Args:
            symbols: Comma-separated exchange_trading_symbols (e.g., "NSE_NIFTY")
            segment: Market segment (CASH, FNO)
            
        Returns:
            Dictionary mapping symbol to LTP
        """
        try:
            return self._api.get_ltp(
                exchange_trading_symbols=symbols,
                segment=segment
            )
        except Exception as e:
            LOG.error(f"Failed to get LTP for {symbols}: {e}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_quote(self, exchange: str, segment: str, trading_symbol: str) -> Dict[str, Any]:
        """
        Get full market quote for an instrument.
        
        Args:
            exchange: Exchange (NSE, BSE)
            segment: Market segment
            trading_symbol: Trading symbol
            
        Returns:
            Quote data including bid/ask, OHLC, etc.
        """
        try:
            return self._api.get_quote(
                exchange=exchange,
                segment=segment,
                trading_symbol=trading_symbol
            )
        except Exception as e:
            LOG.error(f"Failed to get quote for {trading_symbol}: {e}")
            raise
    
    # ==================== Historical Data APIs ====================
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_historical_candles(
        self,
        groww_symbol: str,
        start_time: str,
        end_time: str,
        candle_interval: str = "5minute",
        exchange: str = "NSE",
        segment: str = "CASH"
    ) -> Dict[str, Any]:
        """
        Get historical candle data using the new API.
        
        Args:
            groww_symbol: Groww symbol (e.g., "NSE-RELIANCE")
            start_time: Start time in "yyyy-MM-dd HH:mm:ss" format
            end_time: End time in "yyyy-MM-dd HH:mm:ss" format
            candle_interval: Candle interval (1minute, 5minute, 15minute, etc.)
            exchange: Exchange
            segment: Market segment
            
        Returns:
            Dictionary with candles array
        """
        try:
            return self._api.get_historical_candles(
                exchange=exchange,
                segment=segment,
                groww_symbol=groww_symbol,
                start_time=start_time,
                end_time=end_time,
                candle_interval=candle_interval
            )
        except Exception as e:
            LOG.error(f"Failed to get historical candles for {groww_symbol}: {e}")
            raise
    
    def get_historical_candle_data(
        self,
        trading_symbol: str,
        exchange: str,
        segment: str,
        start_time: str,
        end_time: str,
        interval_in_minutes: int = 5
    ) -> Dict[str, Any]:
        """
        Get historical candle data using legacy API (deprecated but available).
        """
        try:
            return self._api.get_historical_candle_data(
                trading_symbol=trading_symbol,
                exchange=exchange,
                segment=segment,
                start_time=start_time,
                end_time=end_time,
                interval_in_minutes=interval_in_minutes
            )
        except Exception as e:
            LOG.error(f"Failed to get historical data for {trading_symbol}: {e}")
            raise
    
    # ==================== Instruments APIs ====================
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_all_instruments(self):
        """
        Get all available instruments as a DataFrame.
        """
        try:
            return self._api.get_all_instruments()
        except Exception as e:
            LOG.error(f"Failed to get instruments: {e}")
            raise
    
    def get_instrument_by_symbol(self, groww_symbol: str) -> Dict[str, Any]:
        """
        Get instrument details by Groww symbol.
        """
        try:
            return self._api.get_instrument_by_groww_symbol(groww_symbol=groww_symbol)
        except Exception as e:
            LOG.error(f"Failed to get instrument {groww_symbol}: {e}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_expiries(
        self,
        underlying_symbol: str,
        exchange: str = "NSE",
        year: Optional[int] = None,
        month: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get available expiry dates for derivatives.
        """
        try:
            kwargs = {
                "exchange": exchange,
                "underlying_symbol": underlying_symbol
            }
            if year:
                kwargs["year"] = year
            if month:
                kwargs["month"] = month
            return self._api.get_expiries(**kwargs)
        except Exception as e:
            LOG.error(f"Failed to get expiries for {underlying_symbol}: {e}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_contracts(
        self,
        underlying_symbol: str,
        expiry_date: str,
        exchange: str = "NSE"
    ) -> Dict[str, Any]:
        """
        Get available contracts for a given expiry.
        """
        try:
            return self._api.get_contracts(
                exchange=exchange,
                underlying_symbol=underlying_symbol,
                expiry_date=expiry_date
            )
        except Exception as e:
            LOG.error(f"Failed to get contracts for {underlying_symbol} {expiry_date}: {e}")
            raise
    
    # ==================== Order APIs ====================
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def place_order(
        self,
        trading_symbol: str,
        exchange: str,
        segment: str,
        transaction_type: str,
        quantity: int,
        order_type: str = "MARKET",
        price: Optional[float] = None,
        product: str = "INTRADAY"
    ) -> Dict[str, Any]:
        """
        Place a new order.
        """
        if settings.mode == "PAPER":
            LOG.info(f"[PAPER] Would place order: {transaction_type} {quantity} {trading_symbol}")
            return {"order_id": "PAPER_ORDER", "status": "SIMULATED"}
        
        try:
            order_params = {
                "trading_symbol": trading_symbol,
                "exchange": exchange,
                "segment": segment,
                "transaction_type": transaction_type,
                "quantity": quantity,
                "order_type": order_type,
                "product": product
            }
            if price and order_type == "LIMIT":
                order_params["price"] = price
                
            return self._api.place_order(**order_params)
        except Exception as e:
            LOG.error(f"Failed to place order for {trading_symbol}: {e}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_orders(self) -> List[Dict[str, Any]]:
        """Get all orders for the day."""
        try:
            return self._api.get_orders()
        except Exception as e:
            LOG.error(f"Failed to get orders: {e}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions."""
        try:
            return self._api.get_positions()
        except Exception as e:
            LOG.error(f"Failed to get positions: {e}")
            raise
    
    @property
    def api(self) -> GrowwAPI:
        """Direct access to underlying API client if needed."""
        return self._api


# Global client instance
client = GrowwClient()
