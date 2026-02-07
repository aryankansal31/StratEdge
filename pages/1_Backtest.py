import streamlit as st
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime, timedelta
import io
import logging

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.ui.components import setup_page, render_sidebar, plot_equity_curve, plot_pnl_distribution
from src.engine.backtester import run_backtest


# Setup Logging Capture
log_capture_string = io.StringIO()
ch = logging.StreamHandler(log_capture_string)
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)

# Attach to root logger
root_logger = logging.getLogger()
root_logger.addHandler(ch)

def main():
    setup_page("Backtest", "🧪")
    render_sidebar()
    
    st.markdown("### 🛠️ Strategy Setup")
    
    with st.container():
        with st.form("backtest_config"):
            col1, col2 = st.columns(2)
            
            with col1:
                underlying = st.selectbox("Underlying Symbol", ["NIFTY", "BANKNIFTY"], index=0)
                capital = st.number_input("Starting Capital (₹)", value=100000.0, step=10000.0)
                
            with col2:
                # Default to last 30 days
                default_start = datetime.now() - timedelta(days=30)
                default_end = datetime.now()
                
                start_date = st.date_input("Analysis Start Date", value=default_start)
                end_date = st.date_input("Analysis End Date", value=default_end)
                
            # Strategy and Options
            c3, c4 = st.columns(2)
            with c3:
                strategy = st.selectbox("Strategy Architecture", ["Bull Call Spread", "Iron Condor (Coming Soon)"])
            with c4:
                use_calc_expiries = st.checkbox("High-Fidelity Weekly Expiries", value=True, help="Calculates theoretical expiry dates for historical accuracy")
            
            st.markdown("<br>", unsafe_allow_html=True)
            submitted = st.form_submit_button("🚀 Execute Strategic Analysis", use_container_width=True)
        
    if submitted:
        st.divider()
        
        # Clear previous logs
        log_capture_string.truncate(0)
        log_capture_string.seek(0)
        
        with st.status("🔬 Performing Quantitative Analysis...", expanded=True) as status:
            try:
                # Convert dates to string format required by backtester
                from_str = start_date.strftime("%Y-%m-%d")
                to_str = end_date.strftime("%Y-%m-%d")
                
                st.write(f"📡 Fetching historical OHLCV for {underlying}...")
                
                # Run Backtest
                result_obj = run_backtest(
                    underlying=underlying,
                    from_date=from_str,
                    to_date=to_str,
                    use_calculated_expiries=use_calc_expiries
                )
                df_results = result_obj.to_dataframe()
                
                status.update(label="✅ Analysis Complete!", state="complete", expanded=False)
                
                if df_results.empty:
                    st.warning("No trades generated for the selected parameters.")
                else:
                    if 'pnl_after_brokerage' in df_results.columns:
                        df_results['pnl'] = df_results['pnl_after_brokerage']
                    
                    st.success(f"Strategic model generated {len(df_results)} trades.")
                    
                    # Performance Metrics Dashboard
                    st.markdown("### 📊 Performance Metrics")
                    
                    total_pnl = df_results['pnl'].sum()
                    win_rate = (len(df_results[df_results['pnl'] > 0]) / len(df_results)) * 100
                    max_loss = df_results['pnl'].min()
                    profit_factor = abs(df_results[df_results['pnl'] > 0]['pnl'].sum() / df_results[df_results['pnl'] < 0]['pnl'].sum()) if not df_results[df_results['pnl'] < 0].empty else 0
                    
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Net Cumulative P&L", format_currency(total_pnl), delta=f"{total_pnl:,.2f}")
                    m2.metric("Strategic Win Rate", f"{win_rate:.1f}%")
                    m3.metric("Total Executions", len(df_results))
                    m4.metric("Risk Event (Max Loss)", format_currency(max_loss))
                    
                    # Specialized Analysis Tabs
                    st.markdown("<br>", unsafe_allow_html=True)
                    tab1, tab2, tab3 = st.tabs(["📈 Equity Growth", "📊 P&L Distribution", "📝 Execution Journal"])
                    
                    with tab1:
                        plot_equity_curve(df_results, initial_capital=capital)
                        
                    with tab2:
                        plot_pnl_distribution(df_results)
                        
                    with tab3:
                        st.dataframe(df_results.style.format({
                            'pnl': '₹{:.2f}',
                            'entry_price': '{:.2f}',
                            'exit_price': '{:.2f}'
                        }), use_container_width=True)
                    
            except Exception as e:
                st.error(f"An error occurred during backtest: {str(e)}")
                st.exception(e)
                
            finally:
                # Show Logs
                with st.expander("View Execution Logs"):
                    st.code(log_capture_string.getvalue())

if __name__ == "__main__":
    main()
