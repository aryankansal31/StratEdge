import streamlit as st
import sys
import os
from pathlib import Path

# Add project root to path so we can import src
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from src.ui.components import setup_page, render_sidebar

def main():
    setup_page("Home Dashboard", "🏠")
    render_sidebar()

    # Hero Section
    st.markdown("""
        <div style='padding: 2rem 0; text-align: left;'>
            <p style='color: #94a3b8; font-size: 1.2rem; margin-bottom: 0.5rem;'>Welcome back, Trader</p>
            <h2 style='margin-top: 0;'>Your Command Center for Algorithmic Excellence</h2>
        </div>
    """, unsafe_allow_html=True)

    # Action Cards
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
            <div style='background: linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(37, 99, 235, 0.1) 100%); padding: 1.5rem; border-radius: 12px; border: 1px solid rgba(59, 130, 246, 0.2);'>
                <h3 style='color: #60a5fa;'>🧪 Backtesting Suite</h3>
                <p style='color: #94a3b8;'>Validate your strategies against historical market data with precision.</p>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Launch Backtester", key="btn_backtest", use_container_width=True):
            st.switch_page("pages/1_Backtest.py")

    with col2:
        st.markdown("""
            <div style='background: linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(5, 150, 105, 0.1) 100%); padding: 1.5rem; border-radius: 12px; border: 1px solid rgba(16, 185, 129, 0.2);'>
                <h3 style='color: #34d399;'>⚡ Live Monitor</h3>
                <p style='color: #94a3b8;'>Deploy strategies to live markets with real-time WebSocket streaming.</p>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Enter Live Terminal", key="btn_live", use_container_width=True):
            st.switch_page("pages/2_Live_Trading.py")

    st.markdown("---")

    # System Overview
    st.markdown("### 📊 System Overview")
    
    c1, c2, c3 = st.columns(3)
    
    # 1. API Status
    try:
        from src.api.groww_client import GrowwClient
        from src.config import settings
        
        if settings.api_key and settings.api_secret:
            c1.success("**Groww API**\n\nConnected ✅")
        else:
            c1.error("**Groww API**\n\nDisconnected ❌")
    except:
        c1.warning("**Groww API**\n\nStatus Unknown ⚠️")

    # 2. Market Status
    from src.utils import is_market_open
    if is_market_open():
        c2.success("**Market Status**\n\nOPEN 🟢")
    else:
        c2.info("**Market Status**\n\nCLOSED 🔴")

    # 3. Mode
    from src.config import settings
    c3.info(f"**Execution Mode**\n\n{settings.mode.upper()} 🛠️")

    st.markdown("---")
    
    with st.expander("📝 Implementation Notes"):
        st.markdown("""
            - **Engine**: Modular Python Architecture
            - **Data**: Groww WebSocket Feed (Real-time)
            - **Logic**: Pluggable Strategy Classes
            - **Interface**: Streamlit Fragmented UI
        """)

if __name__ == "__main__":
    main()
