import streamlit as st
import sys
import time
from pathlib import Path
import logging
import io

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.ui.components import setup_page, render_sidebar
from src.engine.live_trader import LiveTrader
from src.utils import is_market_open, get_next_market_open

@st.cache_resource
def setup_log_capture():
    """Setup logging capture that persists across reruns."""
    capture_string = io.StringIO()
    ch = logging.StreamHandler(capture_string)
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(message)s')
    ch.setFormatter(formatter)
    
    root_logger = logging.getLogger()
    # Avoid adding duplicate handlers on reload
    if not any(isinstance(h, logging.StreamHandler) and h.stream == capture_string for h in root_logger.handlers):
        root_logger.addHandler(ch)
        
    return capture_string

log_capture_string = setup_log_capture()

@st.fragment(run_every=1)
def render_live_dashboard():
    """Render the live dashboard with 1s auto-refresh."""
    try:
        if 'trader' not in st.session_state or not st.session_state.trader:
            return

        trader = st.session_state.trader
        
        # Execute one trading step
        # calling check_trading_window here ensures we process logic
        # without needing a separate thread in this simple architecture
        trader.check_trading_window()
        
        # 1. Logs
        st.caption("Live System Logs")
        st.code(log_capture_string.getvalue()[-2000:], language="text")
        
        # 2. Metrics
        # Mock metrics for now - ideally get from position_manager/trader
        pos_count = len(trader.strategy.positions) if hasattr(trader.strategy, 'positions') else 'N/A'
        last_update = time.strftime('%H:%M:%S')
        
        m1, m2 = st.columns(2)
        m1.metric("Active Positions", pos_count)
        m2.metric("Last Update", last_update)
        
    except Exception as e:
        st.error(f"Error in dashboard: {e}")

def main():
    setup_page("Live Trading", "⚡")
    render_sidebar()
    
    st.markdown("## Live Trading Monitor")
    
    # Check Market Status
    if is_market_open():
        st.success("🟢 Market is OPEN")
    else:
        next_open = get_next_market_open()
        st.warning(f"🔴 Market is CLOSED. Next Open: {next_open}")
    
    # Initialize Session State
    if 'trading_active' not in st.session_state:
        st.session_state.trading_active = False
    if 'trader' not in st.session_state:
        st.session_state.trader = None
        
    col1, col2 = st.columns(2)
    
    with col1:
        mode = st.radio("Trading Mode", ["Paper", "Live"], horizontal=True)
        underlying = st.selectbox("Underlying", ["NIFTY", "BANKNIFTY"])
        
    with col2:
        st.info(f"Status: {'🟢 Active' if st.session_state.trading_active else '🔴 Stopped'}")
        
        # Disable start button if market is closed (regardless of mode)
        disable_start = not is_market_open()
        
        if disable_start:
             st.error("Cannot start trading when market is closed.")
        
        if st.button(
            "Start Trading" if not st.session_state.trading_active else "Stop Trading",
            disabled=disable_start and not st.session_state.trading_active
        ):
            st.session_state.trading_active = not st.session_state.trading_active
            
            if st.session_state.trading_active:
                st.session_state.trader = LiveTrader(
                    underlying=underlying,
                    mode=mode.upper()
                )
                st.session_state.trader.start() # Ensure we call start() which connects stream
                st.toast(f"Started {mode} Trading for {underlying}!")
            else:
                if st.session_state.trader:
                    st.session_state.trader.stop()
                st.session_state.trader = None
                st.toast("Trading Stopped!")
            
            st.rerun()

    # Dashboard Area
    st.divider()
    
    if st.session_state.trading_active and st.session_state.trader:
        render_live_dashboard()
    else:
        st.markdown("### Waiting to start...")
        with st.expander("System Logs", expanded=True):
            st.code(log_capture_string.getvalue()[-2000:], language="text")

if __name__ == "__main__":
    main()
