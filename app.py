import streamlit as st
import sys
import os
from pathlib import Path

# Add project root to path so we can import src
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from src.ui.components import setup_page, render_sidebar

def main():
    setup_page("Home", "🏠")
    render_sidebar()

    st.markdown("""
    # Welcome to Auto Trading Bot 🤖

    This dashboard allows you to control and monitor your algorithmic trading strategies.

    ### 🚀 Quick Actions
    
    - **[🧪 Run Backtest](/Backtest)**: Test your strategies against historical data.
    - **[⚡ Live Trading](/Live_Trading)**: Monitor live positions and market status.

    ### 📊 System Status
    
    - **API Connection**: Checking... 🔄
    """)

    # Simple API Check
    try:
        from src.api.groww_client import GrowwClient
        from src.config import settings
        
        # We won't actually login here to avoid slow startup, but we check if env is loaded
        if settings.api_key and settings.api_secret:
            st.success("API Credentials Found ✅")
        else:
            st.error("API Credentials Missing ❌. Please check .env file.")
            
    except Exception as e:
        st.warning(f"Could not verify API status: {e}")

    with st.expander("ℹ️ About"):
        st.markdown("""
        **Version**: 2.0 (Modular Architecture)
        **Engine**: Python + Groww API
        **UI**: Streamlit + Plotly
        """)

if __name__ == "__main__":
    main()
