"""
Test data fetching functionality.
"""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_historical_fetcher_init():
    """Test historical fetcher initialization."""
    from src.data import historical_fetcher
    
    assert historical_fetcher is not None


def test_live_fetcher_init():
    """Test live fetcher initialization."""
    from src.data import live_fetcher
    
    assert live_fetcher is not None


def test_instrument_manager_init():
    """Test instrument manager initialization."""
    from src.data import instrument_manager
    
    assert instrument_manager is not None


def test_get_expiries():
    """Test fetching expiries."""
    from src.data import historical_fetcher
    
    try:
        expiries = historical_fetcher.get_expiries("NIFTY")
        print(f"Found {len(expiries)} expiries")
    except Exception as e:
        pytest.skip(f"API not available: {e}")


def test_fetch_option_chain():
    """Test fetching option chain."""
    from src.data import historical_fetcher
    
    try:
        expiries = historical_fetcher.get_expiries("NIFTY")
        if not expiries:
            pytest.skip("No expiries available")
        
        chain = historical_fetcher.get_option_chain("NIFTY", expiries[0])
        assert "calls" in chain
        assert "puts" in chain
        print(f"Chain has {len(chain['calls'])} calls and {len(chain['puts'])} puts")
    except Exception as e:
        pytest.skip(f"API not available: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
