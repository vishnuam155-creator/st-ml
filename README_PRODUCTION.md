# Production Intraday Stock Screener

A **modular, production-ready** intraday stock screening and signal generation system for Nifty 50 stocks, implementing a systematic 20/200 EMA + VWAP trading strategy with comprehensive risk management.

## 🎯 Features

### Complete Workflow
1. **Pre-Market Screening** (8:45-9:15 AM)
   - Index context analysis (Nifty/BankNifty trend using 50/200 EMA)
   - Gap filter (0.3-2.0% gaps, aligned with index)
   - Liquidity filter (high volume, active pre-open)
   - News tagging (earnings, events)
   - Output: 5-8 scored candidates

2. **Live Market Filtering** (After 9:20 AM)
   - Trend confirmation (200 EMA + VWAP on 5-min)
   - Volume surge detection
   - Range validation (min 0.8-1%)
   - Location analysis (key levels, opening range)
   - Output: 3-4 final candidates

3. **Signal Generation**
   - BUY: Price > 200 EMA & VWAP + pullback to 20 EMA + bullish reversal
   - SELL: Price < 200 EMA & VWAP + pullback to 20 EMA + bearish reversal
   - Automatic stop-loss (ATR-based) and target calculation (1:2 R:R)
   - Quality scoring (0-100)

4. **Risk Management**
   - 1% risk per trade (automated position sizing)
   - Max 3 trades per day
   - Stop after 2 consecutive losses
   - Real-time P&L tracking

5. **Backtesting Engine**
   - Historical simulation
   - Performance metrics (win rate, Sharpe ratio, max drawdown)
   - Trade-by-trade analysis
   - Daily P&L tracking

## 📋 Installation

### Prerequisites
- Python 3.8+
- pip

### Setup

```bash
# Clone repository
git clone <repository-url>
cd st-ml

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Generate sample data
python scripts/generate_sample_data.py
```

## 🚀 Quick Start

### 1. Generate Sample Data (First Time)

```bash
python scripts/generate_sample_data.py
```

This creates sample minute and daily OHLCV data in `data/sample/`.

### 2. Run Screener

```bash
# Full screening workflow
python -m production.cli.main screen \
  --date 2024-01-15 \
  --mode full \
  --capital 100000 \
  --output results.json

# Pre-market only
python -m production.cli.main screen \
  --date 2024-01-15 \
  --mode premarket

# Live market only (requires pre-market data)
python -m production.cli.main screen \
  --date 2024-01-15 \
  --mode live \
  --capital 100000
```

### 3. Run Backtest

```bash
python -m production.cli.main backtest \
  --start 2024-01-01 \
  --end 2024-01-31 \
  --capital 100000 \
  --output backtest_results.json
```

### 4. Validate Data

```bash
python -m production.cli.main validate-data
```

## 📊 Data Format

### Minute Data Format

File: `data/sample/minute/SYMBOL_minute.csv`

```csv
timestamp,open,high,low,close,volume
2024-01-15 09:15:00,2450.50,2455.00,2448.00,2453.25,125000
2024-01-15 09:16:00,2453.00,2458.75,2452.50,2457.00,98500
...
```

### Daily Data Format

File: `data/sample/daily/SYMBOL_daily.csv`

```csv
date,open,high,low,close,volume
2024-01-10,2445.00,2468.50,2442.00,2465.75,8500000
2024-01-11,2467.00,2475.25,2461.50,2470.00,7200000
...
```

### News Data Format

File: `data/sample/news.csv`

```csv
date,symbol,event_type,description
2024-01-15,RELIANCE.NS,earnings,Q3 Results
2024-01-16,TCS.NS,dividend,Dividend Announcement
```

## ⚙️ Configuration

Edit `config/screener_config.yaml` to customize parameters:

```yaml
# Pre-Market Parameters
pre_market:
  gap:
    min_percent: 0.3  # Minimum gap %
    max_percent: 2.0  # Maximum gap %
  liquidity:
    min_avg_volume: 100000
  max_candidates: 8

# Live Market Parameters
live_market:
  interval: "5m"  # Candle interval
  ema_fast: 20
  ema_slow: 200
  volume:
    min_ratio: 1.0  # Minimum volume vs average
  range:
    min_percent: 0.8  # Minimum daily range %
  max_candidates: 4

# Signal Parameters
signals:
  buy:
    require_above_200ema: true
    require_above_vwap: true
    pullback_to_20ema_percent: 0.5
    min_volume_ratio: 1.0

# Risk Management
risk:
  capital: 100000
  risk_per_trade_percent: 1.0  # Risk 1% per trade
  max_trades_per_day: 3
  max_consecutive_losses: 2
  stop_loss:
    method: "atr"
    atr_multiplier: 1.5
  target:
    risk_reward_ratio: 2.0
```

## 📦 Package Structure

```
production/
├── __init__.py
├── data_ingest/           # Data loading and validation
│   ├── csv_loader.py      # CSV data loader
│   └── data_validator.py  # Data integrity checks
├── indicators/            # Technical indicators
│   ├── ema.py            # Exponential Moving Average
│   ├── vwap.py           # Volume Weighted Average Price
│   └── atr.py            # Average True Range
├── screener/             # Screening modules
│   ├── pre_market.py     # Pre-market screener
│   └── live_market.py    # Live market filter
├── signal_engine/        # Signal generation
│   └── signals.py        # BUY/SELL signal detection
├── risk_manager/         # Risk management
│   └── position_sizing.py # Position sizing and P&L tracking
├── backtester/           # Backtesting engine
│   └── engine.py         # Historical simulation
└── cli/                  # Command-line interface
    └── main.py           # CLI entry point
```

## 🔧 Usage Examples

### Example 1: Screen for Today

```python
from datetime import datetime
from production.screener import PreMarketScreener, LiveMarketFilter
from production.signal_engine import SignalGenerator
import yaml

# Load config
with open('config/screener_config.yaml') as f:
    config = yaml.safe_load(f)

# Date
date = datetime(2024, 1, 15)

# Pre-market screening
screener = PreMarketScreener(config)
candidates = screener.run_screening(date)

# Live market filtering
live_filter = LiveMarketFilter(config)
final_candidates = live_filter.run_filtering(candidates, date)

# Generate signals
signal_gen = SignalGenerator(config)
signals = signal_gen.generate_signals(final_candidates)

# Print signals
for signal in signals:
    print(f"{signal['symbol']}: {signal['type']} @ {signal['entry']:.2f}")
    print(f"  SL: {signal['stop_loss']:.2f}, Target: {signal['target']:.2f}")
    print(f"  Score: {signal['score']:.0f}/100")
```

### Example 2: Calculate Position Size

```python
from production.risk_manager import PositionSizer

capital = 100000
entry = 2450.00
stop_loss = 2435.50

position = PositionSizer.calculate_position_size(
    capital=capital,
    entry_price=entry,
    stop_loss=stop_loss,
    risk_percent=1.0
)

print(f"Quantity: {position['quantity']}")
print(f"Position Value: ₹{position['position_value']:,.2f}")
print(f"Risk Amount: ₹{position['risk_amount']:,.2f}")
```

### Example 3: Run Backtest Programmatically

```python
from datetime import datetime
from production.backtester import BacktestEngine
import yaml

# Load config
with open('config/screener_config.yaml') as f:
    config = yaml.safe_load(f)

# Run backtest
backtester = BacktestEngine(config)
results = backtester.run_backtest(
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 1, 31),
    initial_capital=100000
)

# Print results
summary = results['summary']
print(f"Total Trades: {summary['total_trades']}")
print(f"Win Rate: {summary['win_rate']:.2f}%")
print(f"Total P&L: ₹{summary['total_pnl']:,.2f}")
print(f"Max Drawdown: ₹{results['max_drawdown']:,.2f}")
```

## 📈 Expected Output

### Screening Output

```json
{
  "pre_market_candidates": [
    {
      "symbol": "RELIANCE.NS",
      "gap_pct": 1.25,
      "aligned_with_index": true,
      "avg_volume": 8500000,
      "has_news": false,
      "score": 85.5
    }
  ],
  "live_market_candidates": [
    {
      "symbol": "RELIANCE.NS",
      "trend": "bullish",
      "ema_200": 2400.50,
      "vwap": 2445.75,
      "current_price_live": 2453.25,
      "volume_ratio": 1.35,
      "today_range_pct": 1.02
    }
  ],
  "signals": [
    {
      "symbol": "RELIANCE.NS",
      "type": "BUY",
      "entry": 2453.25,
      "stop_loss": 2440.50,
      "target": 2478.75,
      "score": 92,
      "position": {
        "quantity": 38,
        "risk_amount": 1000,
        "potential_profit": 2000
      }
    }
  ]
}
```

### Backtest Output

```
==============================================================
BACKTEST RESULTS
==============================================================
Total Days: 21
Trading Days: 15
Total Trades: 32
Win Rate: 62.50%
Total P&L: ₹12,450.00 (+12.45%)
Max Drawdown: ₹3,200.00
Sharpe Ratio: 1.85
==============================================================
```

## 🧪 Testing

Run unit tests:

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/unit/test_ema.py

# Run with coverage
pytest --cov=production tests/
```

## 📊 Performance Metrics

The backtester calculates:

- **Win Rate**: Percentage of winning trades
- **Total P&L**: Absolute and percentage returns
- **Average P&L**: Per trade
- **Max Drawdown**: Largest peak-to-trough decline
- **Sharpe Ratio**: Risk-adjusted returns
- **Daily P&L**: Day-by-day breakdown

## 🔒 Risk Disclaimer

**IMPORTANT**: This is a **research and educational** tool.

- NOT financial advice
- No guarantee of profits
- Trading involves substantial risk
- Past performance ≠ future results
- Always paper trade first
- Consult a licensed financial advisor

The developers are NOT responsible for trading losses.

## 🛠️ Extending the System

### Add Custom Indicator

```python
# production/indicators/custom.py
class CustomIndicator:
    @staticmethod
    def calculate(data, period):
        # Your calculation
        return result
```

### Add Custom Filter

```python
# In pre_market.py or live_market.py
def apply_custom_filter(self, stocks):
    # Your filtering logic
    return filtered_stocks
```

### Add Custom Signal Pattern

```python
# In signals.py
def detect_custom_pattern(self, data):
    # Your pattern detection
    return pattern_info
```

## 📝 Development

### Code Style

- Type hints throughout
- Comprehensive docstrings
- PEP 8 compliant
- Logging for debugging

### Best Practices

- Modular design
- Configuration-driven
- Error handling
- Input validation
- Timezone-aware

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Write tests
4. Submit pull request

## 📄 License

MIT License

## 🙏 Acknowledgments

Built with:
- pandas, numpy (data manipulation)
- PyYAML (configuration)
- pytest (testing)

---

**Production Ready** ✅ | **Well Documented** ✅ | **Tested** ✅ | **Extensible** ✅

For questions or issues, please open a GitHub issue.
