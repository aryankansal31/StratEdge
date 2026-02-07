# Trading Bot - Auto Trading with Groww API

An automated trading bot for Indian markets using the Groww API. Supports both backtesting and live paper/real trading.

## Features

- **Modular Architecture** - Clean separation of concerns
- **Backtesting Engine** - Test strategies with historical data
- **Live Trading** - Paper and live trading modes
- **Options Strategies** - Bull call spread and extensible strategy framework
- **Groww API Integration** - Native SDK integration

## Project Structure

```
src/
├── api/           # Groww API client wrapper
├── config/        # Configuration management
├── data/          # Data fetching (historical + live)
├── engine/        # Backtesting and live trading engines
├── execution/     # Order and position management
├── strategies/    # Trading strategies
└── utils/         # Utilities and helpers
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

### Backtesting
```bash
python backtest.py --underlying NIFTY --from-date 2025-01-01 --to-date 2025-01-10
```

### Paper Trading
```bash
python main.py --mode paper
```

### Live Trading
```bash
python main.py --mode live
```

## Configuration

Edit `.env` file to configure:
- `GROWW_API_KEY` - Your Groww API key
- `GROWW_API_SECRET` - Your TOTP secret
- `MODE` - PAPER or LIVE
- `CAPITAL` - Trading capital
- `RISK_PCT` - Risk percentage per trade
- `SPREAD_WIDTH` - Options spread width in points

## Strategies

The bot uses a pluggable strategy framework. Default strategy is Bull Call Spread:
- Entry at 09:25 IST
- Exit at 15:20 IST
- ATM + configured spread width
