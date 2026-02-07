# Trading Bot - Strategy Automation & Testing

An automated trading bot for Indian markets using the Groww API. Designed primarily for **high-fidelity strategy testing** in live market conditions using Paper Trading before deployment to real capital.

## Features

- **High-Fidelity Paper Trading** - Test strategies in real-time using live WebSocket data without financial risk.
- **Strategy Validation Engine** - Robust framework to verify entry/exit conditions for options strategies.
- **Backtesting Suite** - Validate ideas on historical OHLCV data.
- **WebSocket Streaming** - Sub-second market data updates for precise simulation.
- **Modular Options Framework** - Support for multi-leg strategies like Bull Call Spreads.
- **Streamlit Data Viewer** - Interactive GUI for viewing historical stock data and charts.

## Project Structure

```
Test_bot/
├── src/
│   ├── api/           # Groww API client wrapper
│   ├── config/        # Configuration management
│   ├── data/          # Data fetching (historical + live)
│   ├── engine/        # Backtesting and live trading engines
│   ├── execution/     # Order and position management
│   ├── strategies/    # Trading strategies
│   ├── ui/            # Streamlit UI components
│   └── utils/         # Utilities and helpers
├── pages/             # Streamlit multi-page app pages
├── tests/             # Unit and integration tests
├── logs/              # Application logs
├── groww docs/        # Groww API documentation
├── app.py             # Main Streamlit application
├── backtest.py        # Backtesting script
├── main.py            # Live/Paper trading script
└── requirements.txt   # Python dependencies
```

## Setup

1. **Create virtual environment:**
   ```bash
   python -m venv trading_env
   .\trading_env\Scripts\activate  # Windows
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure credentials:**
   - Copy `.env.example` to `.env`
   - Add your Groww API credentials

## Usage

### Streamlit Web Interface (Recommended)
```bash
streamlit run app.py
```
Access the web interface with:
- Backtesting page
- Live trading page
- Interactive data visualization

### Command Line Interface

**Backtesting:**
```bash
python backtest.py --underlying NIFTY --from-date 2025-01-01 --to-date 2025-01-10
```

**Paper Trading:**
```bash
python main.py --mode paper
```

**Live Trading:**
```bash
python main.py --mode live
```

## Configuration

Edit `.env` file (copy from `.env.example`):
- `GROWW_API_KEY` - Your Groww API key
- `GROWW_API_SECRET` - Your TOTP secret
- `MODE` - PAPER or LIVE
- `CAPITAL` - Trading capital (default: 100000)
- `RISK_PCT` - Risk percentage per trade (default: 0.02)
- `SPREAD_WIDTH` - Options spread width in points (default: 300)
- `UNDERLYING` - Trading symbol (default: NIFTY)
- `ENTRY_TIME` - Entry time in HH:MM format (default: 09:25)
- `EXIT_TIME` - Exit time in HH:MM format (default: 15:20)

## Strategies

The bot uses a pluggable strategy framework. Default strategy is Bull Call Spread:
- Entry at 09:25 IST
- Exit at 15:20 IST
- ATM + configured spread width

## Web Interface

The bot includes a comprehensive Streamlit web interface:

### Features
- **Multi-page Application**: Separate pages for backtesting and live trading
- **Interactive Backtesting**: Configure and run backtests with visual results
- **Live Trading Dashboard**: Monitor positions and P&L in real-time
- **Stock Data Viewer**: Historical data visualization with candlestick charts
- **Configuration Management**: Edit settings through the UI

### Pages
1. **Home** (`app.py`) - Overview and quick start
2. **Backtest** (`pages/1_Backtest.py`) - Strategy backtesting interface
3. **Live Trading** (`pages/2_Live_Trading.py`) - Real-time trading dashboard

## Development

### Testing
```bash
python -m pytest tests/
```

### Logs
Application logs are stored in `logs/` directory with daily rotation.

## Additional Resources

- **API Documentation**: See `groww docs/` for Groww API references
- **Archive**: Old implementations stored in `_archive/` directory
