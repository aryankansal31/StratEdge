import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import List, Optional

def apply_custom_style():
    """Inject custom CSS for a premium look."""
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        
        * {
            font-family: 'Inter', sans-serif !important;
        }
        
        /* Main Container Styling */
        .main {
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            color: #f8fafc;
        }
        
        /* Sidebar Styling */
        [data-testid="stSidebar"] {
            background-color: rgba(15, 23, 42, 0.95) !important;
            border-right: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        /* Glassmorphism Effect for Containers */
        .stMetric, .stAlert, .block-container div[data-testid="stVerticalBlock"] > div {
            background: rgba(30, 41, 59, 0.7);
            backdrop-filter: blur(8px);
            border-radius: 12px;
            padding: 1rem;
            border: 1px solid rgba(255, 255, 255, 0.1);
            transition: transform 0.2s ease-in-out;
        }
        
        .stMetric:hover {
            transform: translateY(-2px);
            border: 1px solid rgba(0, 204, 150, 0.3);
        }
        
        /* Custom Button Styling */
        .stButton > button {
            border-radius: 8px !important;
            background: linear-gradient(90deg, #00CC96 0%, #00f2fe 100%) !important;
            color: #0f172a !important;
            font-weight: 700 !important;
            border: none !important;
            padding: 0.5rem 2rem !important;
            transition: all 0.3s ease !important;
        }
        
        .stButton > button:hover {
            box-shadow: 0 4px 15px rgba(0, 204, 150, 0.4) !important;
            transform: scale(1.02);
        }
        
        /* Metric Label Color */
        [data-testid="stMetricLabel"] {
            color: #94a3b8 !important;
            font-size: 0.9rem !important;
        }
        
        /* Metric Value Color */
        [data-testid="stMetricValue"] {
            color: #ffffff !important;
            font-weight: 700 !important;
        }
        
        /* Sidebar Links Styling */
        .stSidebar a {
            color: #f1f5f9 !important;
            text-decoration: none !important;
            border-radius: 8px !important;
            padding: 0.4rem !important;
        }
        
        .stSidebar a:hover {
            background: rgba(255, 255, 255, 0.05) !important;
        }

        /* Divider */
        hr {
            margin: 1.5rem 0 !important;
            border: 0 !important;
            border-top: 1px solid rgba(255, 255, 255, 0.1) !important;
        }
        </style>
    """, unsafe_allow_html=True)

def setup_page(title: str, icon: str = "📈"):
    """
    Common page setup configuration.
    """
    st.set_page_config(
        page_title=f"Trading Bot - {title}",
        page_icon=icon,
        layout="wide",
        initial_sidebar_state="expanded"
    )
    apply_custom_style()
    
    # Custom Header with Gradient Text
    st.markdown(f"""
        <h1 style='background: linear-gradient(90deg, #ffffff 0%, #94a3b8 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>
            {icon} {title}
        </h1>
    """, unsafe_allow_html=True)

def render_metric_card(label: str, value: str, delta: Optional[str] = None):
    """Render a styled metric card."""
    st.metric(label=label, value=value, delta=delta)

def render_sidebar():
    """
    Render common sidebar elements.
    """
    with st.sidebar:
        st.markdown(f"""
            <div style='text-align: center; padding: 1rem 0;'>
                <h2 style='margin: 0;'>🤖 Trading Bot</h2>
                <p style='color: #64748b; font-size: 0.8rem;'>Precision Algorithm Suite</p>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Navigation
        st.markdown("### 🧭 Navigation")
        st.page_link("app.py", label="Home Dashboard", icon="🏠")
        st.page_link("pages/1_Backtest.py", label="Backtesting Suite", icon="🧪")
        st.page_link("pages/2_Live_Trading.py", label="Live Monitor", icon="⚡")
        
        st.markdown("---")
        
        # System Info
        st.markdown("### ⚙️ System Status")
        st.success("🟢 Ready")
        
        st.markdown("---")
        st.caption("Developed for Professional Trading")

def plot_equity_curve(df_trades: pd.DataFrame, initial_capital: float = 100000.0):
    """
    Plot cumulative P&L equity curve using Plotly.
    """
    if df_trades.empty:
        st.warning("No trades to plot.")
        return

    df = df_trades.copy()
    # Ensure date is datetime
    if 'entry_time' in df.columns:
        df['date'] = pd.to_datetime(df['entry_time'])
    elif 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
    else:
        # Fallback if entry_time is missing (should not happen with new structure)
        st.error("Trade data missing 'entry_time' or 'date' column for plotting.")
        return
        
    df = df.sort_values('date')
    df['cumulative_pnl'] = df['pnl'].cumsum()
    df['equity'] = initial_capital + df['cumulative_pnl']

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['date'], 
        y=df['equity'],
        mode='lines+markers',
        name='Equity',
        line=dict(color='#00CC96', width=2)
    ))

    fig.update_layout(
        title='Equity Curve',
        xaxis_title='Date',
        yaxis_title='Capital (₹)',
        template='plotly_dark',
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)

def plot_pnl_distribution(df_trades: pd.DataFrame):
    """
    Plot daily P&L distribution.
    """
    if df_trades.empty:
        return

    fig = go.Figure()
    
    # Color bars based on profit/loss
    colors = ['#EF553B' if x < 0 else '#00CC96' for x in df_trades['pnl']]
    
    fig.add_trace(go.Bar(
        x=df_trades.index, # Trade number for now, could be date
        y=df_trades['pnl'],
        marker_color=colors,
        name='Trade P&L'
    ))

    fig.update_layout(
        title='Trade P&L Distribution',
        xaxis_title='Trade #',
        yaxis_title='P&L (₹)',
        template='plotly_dark',
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)
