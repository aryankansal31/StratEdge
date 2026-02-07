"""
Instrument management module.
Handles loading, caching, and querying instrument data.
"""

import logging
from typing import Optional, List, Dict, Any
from pathlib import Path
import pandas as pd

from ..api import client
from ..utils import find_atm_strike, extract_strike_from_symbol

LOG = logging.getLogger(__name__)


class InstrumentManager:
    """Manage instrument data with caching and querying capabilities."""
    
    def __init__(self):
        self._client = client
        self._instruments_df: Optional[pd.DataFrame] = None
        self._loaded = False
    
    def load_instruments(self, force_reload: bool = False) -> pd.DataFrame:
        """
        Load all instruments from API.
        
        Args:
            force_reload: Force reload even if cached
            
        Returns:
            DataFrame with instrument details
        """
        if self._loaded and not force_reload:
            return self._instruments_df
        
        try:
            self._instruments_df = self._client.get_all_instruments()
            self._loaded = True
            LOG.info(f"Loaded {len(self._instruments_df)} instruments")
            return self._instruments_df
        except Exception as e:
            LOG.error(f"Failed to load instruments: {e}")
            return pd.DataFrame()
    
    def get_options(
        self,
        underlying: str,
        option_type: Optional[str] = None,
        expiry: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Filter options by underlying, type, and expiry.
        
        Args:
            underlying: Underlying symbol (e.g., "NIFTY")
            option_type: "CE" or "PE" (None for both)
            expiry: Expiry date in standard format (None for all)
            
        Returns:
            Filtered DataFrame
        """
        df = self.load_instruments()
        if df.empty:
            return df
        
        mask = df["underlying_symbol"] == underlying
        
        if option_type:
            mask &= df["instrument_type"] == option_type
        else:
            mask &= df["instrument_type"].isin(["CE", "PE"])
        
        if expiry:
            mask &= df["expiry_date"] == expiry
        
        return df[mask].copy()
    
    def find_option_by_strike(
        self,
        underlying: str,
        strike: float,
        option_type: str,
        expiry: str
    ) -> Optional[Dict[str, Any]]:
        """
        Find specific option contract.
        
        Args:
            underlying: Underlying symbol
            strike: Strike price
            option_type: "CE" or "PE"
            expiry: Expiry date
            
        Returns:
            Option details or None
        """
        options = self.get_options(
            underlying=underlying,
            option_type=option_type,
            expiry=expiry
        )
        
        if options.empty:
            return None
        
        match = options[options["strike_price"] == strike]
        if not match.empty:
            return match.iloc[0].to_dict()
        
        return None
    
    def get_atm_options(
        self,
        underlying: str,
        spot_price: float,
        expiry: str
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        Get ATM call and put options.
        
        Args:
            underlying: Underlying symbol
            spot_price: Current spot price
            expiry: Expiry date
            
        Returns:
            Dictionary with 'call' and 'put' option details
        """
        options = self.get_options(underlying=underlying, expiry=expiry)
        if options.empty:
            return {"call": None, "put": None}
        
        strikes = options["strike_price"].unique().tolist()
        atm_strike = find_atm_strike(spot_price, strikes)
        
        return {
            "call": self.find_option_by_strike(underlying, atm_strike, "CE", expiry),
            "put": self.find_option_by_strike(underlying, atm_strike, "PE", expiry)
        }
    
    def get_available_strikes(
        self,
        underlying: str,
        expiry: str,
        option_type: str = "CE"
    ) -> List[float]:
        """
        Get all available strikes for an underlying and expiry.
        
        Args:
            underlying: Underlying symbol
            expiry: Expiry date
            option_type: Option type to filter
            
        Returns:
            Sorted list of strikes
        """
        options = self.get_options(
            underlying=underlying,
            option_type=option_type,
            expiry=expiry
        )
        
        if options.empty:
            return []
        
        return sorted(options["strike_price"].unique().tolist())
    
    def get_lot_size(self, underlying: str) -> int:
        """
        Get lot size for underlying.
        
        Args:
            underlying: Underlying symbol
            
        Returns:
            Lot size (default 1 if not found)
        """
        df = self.load_instruments()
        if df.empty:
            return 1
        
        match = df[df["underlying_symbol"] == underlying]
        if not match.empty and "lot_size" in match.columns:
            return int(match.iloc[0]["lot_size"])
        
        return 1
    
    def find_option_in_contracts(
        self,
        contracts: List[str],
        strike: float,
        option_type: str
    ) -> Optional[str]:
        """
        Find option symbol from contracts list.
        
        Args:
            contracts: List of contract symbols
            strike: Target strike
            option_type: "CE" or "PE"
            
        Returns:
            Matching contract symbol or None
        """
        for contract in contracts:
            if not contract.endswith(option_type):
                continue
            
            contract_strike = extract_strike_from_symbol(contract)
            if contract_strike == strike:
                return contract
        
        return None


# Global instance
instrument_manager = InstrumentManager()
