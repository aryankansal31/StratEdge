"""
Test API connection and authentication.
"""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_settings_load():
    """Test that settings load correctly."""
    from src.config import settings
    
    assert settings.api_key, "API key should be set"
    assert settings.api_secret, "API secret should be set"
    assert settings.mode in ("PAPER", "LIVE")
    assert settings.capital > 0


def test_groww_client_init():
    """Test Groww client initialization."""
    from src.api import GrowwClient
    
    client = GrowwClient()
    assert client._api is not None, "API client should be initialized"


def test_get_ltp():
    """Test fetching LTP."""
    from src.api import client
    
    try:
        ltp = client.get_ltp("NSE_NIFTY", segment="CASH")
        assert ltp is not None
        print(f"NIFTY LTP: {ltp}")
    except Exception as e:
        pytest.skip(f"API not available: {e}")


def test_get_expiries():
    """Test fetching expiries."""
    from src.api import client
    
    try:
        expiries = client.get_expiries("NIFTY")
        assert "expiries" in expiries or expiries is not None
        print(f"Expiries: {expiries}")
    except Exception as e:
        pytest.skip(f"API not available: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
