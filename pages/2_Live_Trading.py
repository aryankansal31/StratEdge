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
from src.execution.position_manager import position_manager
from src.utils import is_market_open, get_next_market_open, format_currency

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
        trader.check_trading_window()
        
        # 1. P&L Overview
        open_positions = position_manager.get_open_positions()
        total_mtm = sum(p.mtm for p in open_positions)
        realized_pnl = position_manager.get_total_realized_pnl()
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Live MTM", format_currency(total_mtm), delta=f"{total_mtm:.2f}")
        m2.metric("Realized P&L", format_currency(realized_pnl))
        m3.metric("Total P&L", format_currency(total_mtm + realized_pnl))

        st.markdown("---")

        # 2. Position Details
        if open_positions:
            st.markdown("### 🎯 Active Positions")
            for pos in open_positions:
                st.markdown(f"""
                    <div style='background: rgba(30, 41, 59, 0.4); padding: 1rem; border-radius: 12px; border: 1px solid rgba(0, 204, 150, 0.2); margin-bottom: 1rem;'>
                        <div style='display: flex; justify-content: space-between; align-items: center;'>
                            <h4 style='margin: 0; color: #00CC96;'>{pos.strategy_name}</h4>
                            <span style='font-size: 0.8rem; color: #94a3b8;'>{pos.spread_id}</span>
                        </div>
                        <div style='display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1rem; margin-top: 1rem;'>
                            <div>
                                <p style='margin:0; font-size: 0.7rem; color: #64748b;'>LONG LEG</p>
                                <p style='margin:0; font-weight: 600;'>{pos.long_symbol}</p>
                                <p style='margin:0; color: #94a3b8;'>{pos.long_price:.2f} → {pos.current_long_price:.2f}</p>
                            </div>
                            <div>
                                <p style='margin:0; font-size: 0.7rem; color: #64748b;'>SHORT LEG</p>
                                <p style='margin:0; font-weight: 600;'>{pos.short_symbol}</p>
                                <p style='margin:0; color: #94a3b8;'>{pos.short_price:.2f} → {pos.current_short_price:.2f}</p>
                            </div>
                            <div style='text-align: right;'>
                                <p style='margin:0; font-size: 0.7rem; color: #64748b;'>LEG MTM</p>
                                <p style='margin:0; font-weight: 700; color: {"#00CC96" if pos.mtm >= 0 else "#EF553B"};'>{pos.mtm:+.2f}</p>
                            </div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Searching for entry signal...")
            
        # 3. Logs
        with st.expander("🔍 Terminal Logs"):
            st.code(log_capture_string.getvalue()[-2000:], language="text")
        
    except Exception as e:
        st.error(f"Dashboard Error: {e}")

def main():
    setup_page("Live Terminal", "⚡")
    render_sidebar()
    
    # Check Market Status
    if is_market_open():
        st.markdown("""
            <div style='background: rgba(0, 204, 150, 0.1); padding: 0.5rem 1rem; border-radius: 8px; border: 1px solid rgba(0, 204, 150, 0.2);'>
                <span style='color: #00CC96; font-weight: 600;'>🟢 Market is OPEN</span>
            </div>
        """, unsafe_allow_html=True)
    else:
        next_open = get_next_market_open()
        st.markdown(f"""
            <div style='background: rgba(239, 85, 59, 0.1); padding: 0.5rem 1rem; border-radius: 8px; border: 1px solid rgba(239, 85, 59, 0.2);'>
                <span style='color: #EF553B; font-weight: 600;'>🔴 Market is CLOSED. Next Open: {next_open}</span>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Initialize Session State
    if 'trading_active' not in st.session_state:
        st.session_state.trading_active = False
    if 'trader' not in st.session_state:
        st.session_state.trader = None
        
    # Controls in a nice container
    with st.container():
        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            mode = st.radio("Mode", ["Paper", "Live"], horizontal=True)
        with c2:
            underlying = st.selectbox("Symbol", ["NIFTY", "BANKNIFTY"])
        with c3:
            st.markdown("<p style='margin:0; font-size: 0.8rem; color: #94a3b8;'>ENGINE CONTROL</p>", unsafe_allow_html=True)
            # Disable start button if market is closed (regardless of mode)
            disable_start = not is_market_open()
            
            if st.button(
                "🏁 START ENGINE" if not st.session_state.trading_active else "🛑 STOP ENGINE",
                disabled=disable_start and not st.session_state.trading_active,
                use_container_width=True
            ):
                st.session_state.trading_active = not st.session_state.trading_active
                
                if st.session_state.trading_active:
                    st.session_state.trader = LiveTrader(
                        underlying=underlying,
                        mode=mode.upper()
                    )
                    st.session_state.trader.start()
                    st.toast(f"Strategic Deployment: {underlying}")
                else:
                    if st.session_state.trader:
                        st.session_state.trader.stop()
                    st.session_state.trader = None
                    st.toast("Deployment Terminated")
                
                st.rerun()

    if disable_start and not st.session_state.trading_active:
         st.warning("Live deployment restricted: Market is Currently Closed.")

    # Dashboard Area
    st.divider()
    
    if st.session_state.trading_active and st.session_state.trader:
        render_live_dashboard()
    else:
        st.markdown("""
            <div style='text-align: center; padding: 4rem 1rem; background: rgba(30, 41, 59, 0.2); border-radius: 12px; border: 1px dashed rgba(255, 255, 255, 0.1);'>
                <h3 style='color: #475569;'>Terminal Standby</h3>
                <p style='color: #64748b;'>Select symbol and start engine to begin live monitoring.</p>
            </div>
        """, unsafe_allow_html=True)
        with st.expander("Previous Session Logs"):
            st.code(log_capture_string.getvalue()[-2000:], language="text")

if __name__ == "__main__":
    main()
