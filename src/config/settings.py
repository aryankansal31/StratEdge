"""
Configuration module for the trading bot.
Loads settings from environment variables and .env file.
"""

import os
from pathlib import Path
from typing import Literal
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)


@dataclass
class Settings:
    """Application settings loaded from environment variables."""
    
    # Groww API Credentials
    api_key: str
    api_secret: str
    
    # Trading Mode
    mode: Literal["PAPER", "LIVE"]
    
    # Risk Management
    capital: float
    risk_pct: float
    spread_width: int
    
    # Trading Schedule
    entry_time: str
    exit_time: str
    
    # Underlying Asset
    underlying: str
    
    # Backtesting Date Range
    from_date: str
    to_date: str
    
    # Constants
    lot_fallback: int = 1
    brokerage_per_order: float = 20.0
    slippage_points: float = 0.5
    
    @classmethod
    def from_env(cls) -> "Settings":
        """Load settings from environment variables."""
        return cls(
            api_key=os.getenv("GROWW_API_KEY", ""),
            api_secret=os.getenv("GROWW_API_SECRET", ""),
            mode=os.getenv("MODE", "PAPER"),
            capital=float(os.getenv("CAPITAL", "100000")),
            risk_pct=float(os.getenv("RISK_PCT", "0.02")),
            spread_width=int(os.getenv("SPREAD_WIDTH", "300")),
            entry_time=os.getenv("ENTRY_TIME", "09:25"),
            exit_time=os.getenv("EXIT_TIME", "15:20"),
            underlying=os.getenv("UNDERLYING", "NIFTY"),
            from_date=os.getenv("FROM_DATE", "2025-01-01"),
            to_date=os.getenv("TO_DATE", "2025-01-03"),
        )
    
    def validate(self) -> bool:
        """Validate required settings are present."""
        if not self.api_key:
            raise ValueError("GROWW_API_KEY is required")
        if not self.api_secret:
            raise ValueError("GROWW_API_SECRET is required")
        if self.mode not in ("PAPER", "LIVE"):
            raise ValueError("MODE must be PAPER or LIVE")
        if self.capital <= 0:
            raise ValueError("CAPITAL must be positive")
        if not (0 < self.risk_pct <= 1):
            raise ValueError("RISK_PCT must be between 0 and 1")
        return True
    
    def __repr__(self):
        """Mask sensitive data in logs."""
        return (
            f"Settings(mode='{self.mode}', "
            f"underlying='{self.underlying}', "
            f"capital={self.capital}, "
            f"risk_pct={self.risk_pct}, "
            f"api_key='****{self.api_key[-4:] if self.api_key else ''}', "
            f"api_secret='****')"
        )


# Global settings instance
settings = Settings.from_env()
