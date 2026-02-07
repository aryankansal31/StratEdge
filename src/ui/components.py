import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import List, Optional

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
    st.title(f"{icon} {title}")

def render_sidebar():
    """
    Render common sidebar elements.
    """
    with st.sidebar:
        st.header("🤖 Auto Trading Bot")
        st.markdown("---")
        
        # We can add global status indicators here later
        st.info("System Status: 🟢 Ready")
        
        st.markdown("---")
        st.caption("Developed with ❤️ by Your AI Assistant")

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
