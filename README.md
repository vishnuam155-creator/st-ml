# 📈 Intraday Stock Screener & Trading System

A comprehensive **intraday stock screening and trading system** for Indian markets (NSE). This tool helps identify the best trading opportunities using **technical analysis**, **machine learning**, and **systematic risk management**.

## 🎯 Features

### Pre-Market Screener (8:45 - 9:15 AM)
- **Index Context Analysis**: Analyzes Nifty & BankNifty trends
- **Gap Filter**: Identifies stocks with 0.3-2% gaps
- **Liquidity Filter**: Filters high-volume stocks
- **News Filter**: Marks stocks with important news/events
- **Output**: 5-8 candidate stocks

### Live Market Filter (After 9:20 AM)
- **Trend Filter**: Uses 200 EMA & VWAP to identify clear trends
- **Volume & Range Filter**: Ensures sufficient momentum
- **Location Filter**: Identifies stocks near key levels
- **Output**: 3-4 final stocks for trading

### Trading Strategy Engine
- **20 EMA + 200 EMA + VWAP Trend Method**
- **BUY Setup**: Price > 200 EMA, > VWAP, pullback to 20 EMA, bullish reversal
- **SELL Setup**: Price < 200 EMA, < VWAP, pullback to 20 EMA, bearish reversal
- **Automatic Stop-Loss & Target Calculation**
- **Risk-Reward Ratio**: 1:2 or better

### Risk Management
- **1% Risk per Trade**: Capital preservation
- **Maximum 3 Trades per Day**: Prevents overtrading
- **Stop After 2 Consecutive Losses**: Protects from bad days
- **Position Sizing**: Automated based on capital and stop-loss

### Machine Learning (Optional)
- **Random Forest Model**: Predicts stock movement
- **Feature Engineering**: 15+ technical features
- **Confidence Scoring**: Ranks stocks by probability
- **Continuous Learning**: Train on historical data

## 📋 Project Structure

```
st-ml/
├── config/
│   └── config.py              # Configuration settings
├── src/
│   ├── data_fetcher.py        # Fetches stock data from NSE
│   ├── technical_indicators.py # Technical analysis indicators
│   ├── pre_market_screener.py # Pre-market screening logic
│   ├── live_market_filter.py  # Live market filtering
│   ├── trading_strategy.py    # Trading strategy implementation
│   ├── risk_manager.py        # Risk management system
│   └── ml_predictor.py        # Machine learning predictor
├── data/                      # Data storage (CSV, JSON)
├── logs/                      # Application logs
├── models/                    # Trained ML models
├── main.py                    # Main application
└── requirements.txt           # Python dependencies
```

## 🚀 Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd st-ml
```

2. **Create virtual environment (recommended)**
```bash
python -m venv venv

# On Linux/Mac
source venv/bin/activate

# On Windows
venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

## 📖 Usage

### Basic Usage

#### 1. Full Screening Workflow
Run complete pre-market screening, live filtering, and strategy analysis:

```bash
python main.py --mode full --capital 100000
```

#### 2. Pre-Market Screening Only
Screen stocks before market open:

```bash
python main.py --mode premarket
```

#### 3. Live Market Analysis
Analyze stocks during market hours:

```bash
python main.py --mode live --capital 100000
```

### Advanced Usage

#### Train ML Model (First Time Setup)
Before using ML predictions, train the model on historical data:

```bash
python main.py --mode train-ml
```

This will:
- Download historical data for Nifty 50 stocks
- Extract technical features
- Train Random Forest classifier
- Save model to `models/stock_predictor.pkl`

#### Full Screening with ML
Use ML predictions to rank stocks:

```bash
python main.py --mode full --capital 100000 --use-ml
```

### Command-Line Options

```
--mode          Screening mode (premarket, live, full, train-ml)
                Default: full

--capital       Trading capital in INR
                Default: 100000

--use-ml        Enable ML predictions for ranking
                Requires trained model
```

## 📊 Example Output

### Pre-Market Screening
```
============================================================
        PRE-MARKET SCREENER (8:45 - 9:15 AM)
============================================================

STEP 1: INDEX CONTEXT
------------------------------------------------------------
NIFTY 50:
  Trend: UPTREND
  Current Price: 19850.25
  Change: +0.75%
  Yesterday High: 19875.50
  Yesterday Low: 19725.30

STEP 2: GAP FILTER (0.3% - 2.0%)
------------------------------------------------------------
Found 12 stocks with gaps:
  ✓ RELIANCE.NS    | Gap: +1.25% | Direction: up    | Price: ₹2456.80
  ✓ TCS.NS         | Gap: +0.85% | Direction: up    | Price: ₹3542.30
  ...

FINAL PRE-MARKET CANDIDATES: 8 stocks
```

### Trading Plan
```
============================================================
📋 DETAILED TRADING PLANS
============================================================

1. RELIANCE.NS - BUY SETUP
------------------------------------------------------------
   Setup Quality: 85/100
   Reversal Pattern: hammer

   Entry Details:
      Entry Price: ₹2456.80
      Stop Loss: ₹2440.50
      Target: ₹2489.40
      Risk:Reward = 1:2.0

   Position Sizing (Capital: ₹100,000):
      Quantity: 37 shares
      Position Value: ₹90,901.60
      Risk Amount: ₹1,000.00 (1.0%)
      Potential Profit: ₹2,000.00

   ✅ TRADE APPROVED
```

## 🎓 Trading Strategy Explained

### The 20 EMA + 200 EMA + VWAP Method

#### BUY Setup (Long Trade)
1. **Trend Confirmation**: Price must be above 200 EMA (uptrend)
2. **Intraday Strength**: Price must be above VWAP
3. **Entry Trigger**: Price pulls back to 20 EMA
4. **Confirmation**: Bullish reversal candle pattern
5. **Volume**: Higher than average volume

#### SELL Setup (Short Trade)
1. **Trend Confirmation**: Price must be below 200 EMA (downtrend)
2. **Intraday Weakness**: Price must be below VWAP
3. **Entry Trigger**: Price pulls back to 20 EMA
4. **Confirmation**: Bearish reversal candle pattern
5. **Volume**: Higher than average volume

#### Risk Management
- **Stop-Loss**: 1.5x ATR below entry (BUY) or above entry (SELL)
- **Target**: 2x the risk amount (1:2 risk-reward)
- **Position Size**: Calculated to risk exactly 1% of capital

## ⚙️ Configuration

Edit `config/config.py` to customize:

```python
TRADING_CONFIG = {
    # Gap filter
    'gap_min_pct': 0.3,
    'gap_max_pct': 2.0,

    # Volume filter
    'volume_lookback_days': 20,

    # Candidate limits
    'pre_market_candidates': 8,
    'live_market_candidates': 4,

    # Technical indicators
    'ema_fast': 20,
    'ema_slow': 200,

    # Risk management
    'risk_per_trade_pct': 1.0,
    'max_trades_per_day': 3,
    'max_consecutive_losses': 2,
}
```

## 🔧 Customization

### Add New Stocks
Edit `NIFTY_50_STOCKS` list in `config/config.py`:

```python
NIFTY_50_STOCKS = [
    'RELIANCE.NS',
    'TCS.NS',
    # Add your stocks here
    'NEWSTOCK.NS',
]
```

### Modify Trading Strategy
Edit detection logic in `src/trading_strategy.py`:

```python
def detect_buy_setup(self, data: pd.DataFrame):
    # Customize entry conditions here
    ...
```

### Add New Indicators
Add new indicators in `src/technical_indicators.py`:

```python
@staticmethod
def calculate_custom_indicator(data: pd.DataFrame):
    # Your indicator calculation
    return indicator_values
```

## 📈 Performance Tips

1. **Use ML for Better Results**: Train ML model monthly for best predictions
2. **Backtest Your Strategy**: Test on historical data before live trading
3. **Monitor Market Conditions**: Adapt filters based on market volatility
4. **Keep Learning**: Review trades and refine your approach

## 🛡️ Risk Disclaimer

**IMPORTANT**: This tool is for **educational and research purposes only**.

- **Not Financial Advice**: This is NOT investment advice
- **Use at Your Own Risk**: Trading involves substantial risk of loss
- **Paper Trade First**: Test thoroughly before using real money
- **Consult Professionals**: Always consult with a licensed financial advisor

The developers are not responsible for any trading losses incurred using this tool.

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 📧 Support

For issues or questions:
- Open an issue on GitHub
- Check existing documentation
- Review the code comments

## 🎯 Roadmap

Future enhancements:
- [ ] Backtesting framework
- [ ] Real-time alerts (Telegram/Email)
- [ ] Web dashboard
- [ ] Options strategy integration
- [ ] Multiple timeframe analysis
- [ ] Sector rotation analysis

## 🙏 Acknowledgments

- **yfinance**: For stock data
- **pandas-ta**: For technical indicators
- **scikit-learn**: For machine learning

---

**Happy Trading! 📈**

Remember: The best trade is the one you don't take if conditions aren't perfect.
