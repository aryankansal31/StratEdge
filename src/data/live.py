"""
Live market data fetching module.
Provides real-time quotes and LTP.
"""

import logging
from typing import Dict, Any, Optional, List

from ..api import client

LOG = logging.getLogger(__name__)


class LiveDataFetcher:
    """Fetch real-time market data."""
    
    def __init__(self):
        self._client = client
    
    def get_ltp(
        self,
        symbols: List[str],
        segment: str = "CASH"
    ) -> Dict[str, float]:
        """
        Get last traded prices for multiple symbols.
        
        Args:
            symbols: List of symbols in exchange_symbol format (e.g., ["NSE_NIFTY"])
            segment: Market segment
            
        Returns:
            Dictionary mapping symbol to LTP
        """
        try:
            symbol_str = ",".join(symbols)
            return self._client.get_ltp(symbols=symbol_str, segment=segment)
        except Exception as e:
            LOG.error(f"Failed to get LTP for {symbols}: {e}")
            return {}
    
    def get_quote(
        self,
        trading_symbol: str,
        exchange: str = "NSE",
        segment: str = "CASH"
    ) -> Optional[Dict[str, Any]]:
        """
        Get full market quote for an instrument.
        
        Args:
            trading_symbol: Trading symbol
            exchange: Exchange
            segment: Market segment
            
        Returns:
            Quote data or None
        """
        try:
            return self._client.get_quote(
                exchange=exchange,
                segment=segment,
                trading_symbol=trading_symbol
            )
        except Exception as e:
            LOG.error(f"Failed to get quote for {trading_symbol}: {e}")
            return None
    
    def get_option_greeks(
        self,
        trading_symbol: str,
        exchange: str = "NSE"
    ) -> Optional[Dict[str, float]]:
        """
        Get option Greeks from quote data.
        
        Args:
            trading_symbol: Option trading symbol
            exchange: Exchange
            
        Returns:
            Dictionary with delta, gamma, theta, vega, iv or None
        """
        quote = self.get_quote(
            trading_symbol=trading_symbol,
            exchange=exchange,
            segment="FNO"
        )
        
        if quote:
            return {
                "delta": quote.get("delta"),
                "gamma": quote.get("gamma"),
                "theta": quote.get("theta"),
                "vega": quote.get("vega"),
                "iv": quote.get("iv"),
                "rho": quote.get("rho")
            }
        return None
    
    def get_spot_ltp(self, underlying: str) -> Optional[float]:
        """
        Get current spot price for underlying.
        
        Args:
            underlying: Underlying symbol (e.g., "NIFTY")
            
        Returns:
            Current LTP or None
        """
        result = self.get_ltp([f"NSE_{underlying}"], segment="CASH")
        return result.get(f"NSE_{underlying}")


# Global instance
live_fetcher = LiveDataFetcher()
