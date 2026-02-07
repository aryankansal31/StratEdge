"""
Historical data fetching module.
Provides methods to fetch OHLCV candle data and option chains.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import pandas as pd

from ..api import client
from ..config import settings

LOG = logging.getLogger(__name__)


class HistoricalDataFetcher:
    """Fetch and process historical market data."""
    
    def __init__(self):
        self._client = client
        self._cache: Dict[str, pd.DataFrame] = {}
    
    def get_candles(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "5minute",
        exchange: str = "NSE",
        segment: str = "CASH"
    ) -> pd.DataFrame:
        """
        Fetch historical candle data.
        
        Args:
            symbol: Groww symbol (e.g., "NSE-NIFTY")
            start_date: Start date in "YYYY-MM-DD" format
            end_date: End date in "YYYY-MM-DD" format
            interval: Candle interval (1minute, 5minute, 15minute, etc.)
            exchange: Exchange
            segment: Market segment
            
        Returns:
            DataFrame with OHLCV data
        """
        cache_key = f"{symbol}_{start_date}_{end_date}_{interval}"
        if cache_key in self._cache:
            LOG.debug(f"📦 Cache hit for {symbol}")
            return self._cache[cache_key]
        
        try:
            start_time = f"{start_date} 09:15:00"
            end_time = f"{end_date} 15:30:00"
            
            LOG.debug(f"🌐 API call: get_historical_candles({symbol}, {start_time} to {end_time})")
            
            response = self._client.get_historical_candles(
                groww_symbol=symbol,
                start_time=start_time,
                end_time=end_time,
                candle_interval=interval,
                exchange=exchange,
                segment=segment
            )
            
            if response and "candles" in response and response["candles"]:
                df = pd.DataFrame(
                    response["candles"],
                    columns=["timestamp", "open", "high", "low", "close", "volume", "oi"]
                )
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                df.set_index("timestamp", inplace=True)
                
                self._cache[cache_key] = df
                LOG.debug(f"📊 Fetched {len(df)} candles for {symbol}")
                return df
            
            LOG.debug(f"⚠️  No candle data in response for {symbol}")
            return pd.DataFrame()
            
        except Exception as e:
            LOG.debug(f"❌ Failed to fetch candles for {symbol}: {e}")
            return pd.DataFrame()
    
    def get_option_chain(
        self,
        underlying: str,
        expiry_date: str,
        exchange: str = "NSE"
    ) -> Dict[str, List[str]]:
        """
        Fetch option chain for a specific expiry.
        
        Args:
            underlying: Underlying symbol (e.g., "NIFTY")
            expiry_date: Expiry date in "YYYY-MM-DD" format
            exchange: Exchange
            
        Returns:
            Dictionary with 'calls' and 'puts' lists of contract symbols
        """
        try:
            LOG.debug(f"🌐 API call: get_contracts({underlying}, expiry={expiry_date})")
            
            contracts = self._client.get_contracts(
                underlying_symbol=underlying,
                expiry_date=expiry_date,
                exchange=exchange
            )
            
            if not contracts or "contracts" not in contracts:
                LOG.debug(f"⚠️  No contracts found for {underlying} expiry {expiry_date}")
                return {"calls": [], "puts": []}
            
            all_contracts = contracts["contracts"]
            calls = [c for c in all_contracts if c.endswith("CE")]
            puts = [c for c in all_contracts if c.endswith("PE")]
            
            LOG.debug(f"📋 Found {len(calls)} CE and {len(puts)} PE contracts")
            
            # Log sample contracts for debugging
            if calls:
                LOG.debug(f"   Sample calls: {calls[:3]}")
            if puts:
                LOG.debug(f"   Sample puts: {puts[:3]}")
            
            return {"calls": calls, "puts": puts}
            
        except Exception as e:
            LOG.error(f"❌ Failed to get option chain for {underlying}: {e}")
            return {"calls": [], "puts": []}
    
    def get_expiries(
        self,
        underlying: str,
        exchange: str = "NSE",
        month: Optional[int] = None
    ) -> List[str]:
        """
        Get available expiry dates.
        
        Args:
            underlying: Underlying symbol
            exchange: Exchange
            month: Optional month filter
            
        Returns:
            List of expiry dates in "YYYY-MM-DD" format, sorted ascending
        """
        try:
            LOG.debug(f"🌐 API call: get_expiries({underlying})")
            
            response = self._client.get_expiries(
                underlying_symbol=underlying,
                exchange=exchange,
                month=month
            )
            
            if response and "expiries" in response:
                expiries = response["expiries"]
                # Sort expiries in ascending order
                expiries = sorted(expiries)
                LOG.debug(f"📅 Found {len(expiries)} expiries")
                LOG.debug(f"   Nearest 5: {expiries[:5]}")
                return expiries
            
            LOG.debug(f"⚠️  No expiries in response")
            return []
            
        except Exception as e:
            LOG.error(f"❌ Failed to get expiries for {underlying}: {e}")
            return []
    
    def get_spot_price(
        self,
        symbol: str,
        date: str
    ) -> Optional[float]:
        """
        Get spot price for a symbol on a specific date.
        
        Args:
            symbol: Symbol (e.g., "NIFTY")
            date: Date in "YYYY-MM-DD" format
            
        Returns:
            Closing price or None
        """
        LOG.debug(f"📊 Fetching spot price for {symbol} on {date}")
        
        candles = self.get_candles(
            symbol=f"NSE-{symbol}",
            start_date=date,
            end_date=date,
            interval="5minute"
        )
        
        if not candles.empty:
            price = float(candles.iloc[-1]["close"])
            LOG.debug(f"📊 Got historical spot price: {price:.2f}")
            return price
        
        # Fallback to LTP
        try:
            LOG.debug(f"📊 Falling back to LTP...")
            ltp_data = self._client.get_ltp(
                symbols=f"NSE_{symbol}",
                segment="CASH"
            )
            if ltp_data and f"NSE_{symbol}" in ltp_data:
                price = float(ltp_data[f"NSE_{symbol}"])
                LOG.debug(f"📊 Got LTP: {price:.2f}")
                return price
        except Exception as e:
            LOG.debug(f"⚠️  LTP fetch failed: {e}")
        
        LOG.warning(f"❌ Could not get spot price for {symbol} on {date}")
        return None
    
    def clear_cache(self) -> None:
        """Clear the data cache."""
        self._cache.clear()
        LOG.debug("🗑️  Historical data cache cleared")


# Global instance
historical_fetcher = HistoricalDataFetcher()
