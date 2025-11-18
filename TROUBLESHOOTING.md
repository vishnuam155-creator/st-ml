# Troubleshooting Guide

## Common Issues and Solutions

### Issue 1: "Insufficient data" during Live Market Filtering

**Symptom:**
```
============================================================
STEP 1: TREND FILTER (5-min chart)
============================================================
  ⚠️  TATASTEEL.NS: Insufficient data
  ⚠️  ITC.NS: Insufficient data
  ...
Found 0 stocks with clear trend:
```

**Cause:**
This happens when intraday 5-minute data is not available. Common reasons:
1. **Market is closed**: The screener needs to run during market hours (9:15 AM - 3:30 PM IST)
2. **Data limitations**: yfinance has limited access to real-time NSE intraday data
3. **Network issues**: Connection problems preventing data fetch

**Solutions:**

#### Solution 1: Use Demo Mode (Recommended for Testing)
Use the `--demo` flag to fall back to daily data when intraday data is unavailable:

```bash
python main.py --mode full --capital 100000 --demo
```

This allows you to:
- Test the system outside market hours
- Backtest strategies on historical data
- Learn how the system works without live data

#### Solution 2: Run During Market Hours
Execute the screener during active trading hours:
- **Pre-market**: 8:45 AM - 9:15 AM IST
- **Live market**: 9:20 AM - 3:30 PM IST

```bash
# Best times to run:
# 9:00 AM - Pre-market screening
# 9:30 AM - Live market filtering (after market opens)
python main.py --mode full --capital 100000
```

#### Solution 3: Alternative Data Sources
For production use, consider integrating better data sources:

**Free Options:**
- **NSEPy**: Direct NSE data (more reliable for Indian markets)
  ```python
  pip install nsepy
  ```

**Paid Options:**
- **Alpha Vantage**: https://www.alphavantage.co/
- **Upstox API**: https://upstox.com/developer/
- **Zerodha Kite Connect**: https://kite.trade/
- **IIFL API**: https://www.indiainfoline.com/

### Issue 2: No Trading Setups Found

**Symptom:**
```
❌ No trading setups found. Exiting.
```

**Solutions:**
1. **Adjust filters**: The strategy is strict. Try relaxing some filters in `config/config.py`:
   ```python
   'gap_min_pct': 0.2,  # Lower from 0.3
   'min_range_pct': 0.5,  # Lower from 0.8
   ```

2. **Different market conditions**: The strategy works best in trending markets. In sideways markets, fewer setups appear.

3. **Use demo mode**: Test with historical data to see if setups existed in past trading sessions.

### Issue 3: ML Model Not Found

**Symptom:**
```
⚠️  Model not trained. Skipping ML ranking.
```

**Solution:**
Train the ML model first:
```bash
python main.py --mode train-ml
```

This will:
- Download 6 months of historical data for Nifty 50
- Train a Random Forest classifier
- Save the model to `models/stock_predictor.pkl`

After training, use with:
```bash
python main.py --mode full --capital 100000 --use-ml
```

### Issue 4: Import Errors

**Symptom:**
```
ModuleNotFoundError: No module named 'pandas'
```

**Solution:**
Install all dependencies:
```bash
pip install -r requirements.txt
```

If using a virtual environment:
```bash
# Create venv
python -m venv venv

# Activate
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install
pip install -r requirements.txt
```

### Issue 5: Slow Performance

**Solutions:**
1. **Reduce stock list**: Test with fewer stocks first
   ```python
   # In config/config.py
   NIFTY_50_STOCKS = [
       'RELIANCE.NS', 'TCS.NS', 'INFY.NS',  # Test with 3-5 stocks
   ]
   ```

2. **Adjust timeframes**: Use larger intervals
   ```python
   # In src/live_market_filter.py
   data = self.data_fetcher.get_intraday_data(symbol, interval='15m')  # Instead of 5m
   ```

## Usage Tips

### Best Practices

1. **Paper Trade First**: Always test with paper trading before using real money
2. **Market Hours**: Run during active trading hours for best results
3. **Demo Mode**: Use `--demo` for testing and learning
4. **Start Small**: Test with a small stock list first
5. **Monitor Performance**: Keep track of trades and adjust strategy

### Recommended Workflow

```bash
# 1. Train ML model (once, then retrain monthly)
python main.py --mode train-ml

# 2. Pre-market (8:45 AM - 9:15 AM)
python main.py --mode premarket

# Review candidates, prepare watchlist

# 3. Live market (9:30 AM onwards)
python main.py --mode full --capital 100000 --use-ml

# 4. Demo/testing (anytime)
python main.py --mode full --capital 100000 --demo --use-ml
```

### Testing Without Live Data

For testing, backtesting, or learning:

```bash
# Full test with demo mode
python main.py --mode full --capital 100000 --demo

# With ML predictions
python main.py --mode full --capital 100000 --demo --use-ml
```

This uses historical daily data, allowing you to:
- Learn how the system works
- Test configuration changes
- Understand the screening logic
- Backtest strategies

## Configuration Tweaks

### Make the Screener More Aggressive

```python
# In config/config.py
TRADING_CONFIG = {
    'gap_min_pct': 0.2,  # Lower threshold
    'gap_max_pct': 3.0,  # Higher threshold
    'pre_market_candidates': 12,  # More candidates
    'live_market_candidates': 6,  # More final stocks
    'min_range_pct': 0.5,  # Lower range requirement
}
```

### Make the Screener More Conservative

```python
# In config/config.py
TRADING_CONFIG = {
    'gap_min_pct': 0.5,  # Higher threshold
    'gap_max_pct': 1.5,  # Lower threshold
    'pre_market_candidates': 5,  # Fewer candidates
    'live_market_candidates': 3,  # Fewer final stocks
    'min_range_pct': 1.0,  # Higher range requirement
}
```

## Getting Help

If you encounter other issues:

1. **Check logs**: Enable debug mode in the code
2. **Review error messages**: They usually indicate the problem
3. **Check data availability**: Ensure yfinance can access the data
4. **Test with one stock**: Isolate the problem
5. **Check internet connection**: Required for data fetching

## Advanced: Switching to NSEPy

For better Indian market data, consider using NSEPy instead of yfinance:

1. Install NSEPy:
   ```bash
   pip install nsepy
   ```

2. Modify `src/data_fetcher.py` to use NSEPy for data fetching

3. NSEPy provides:
   - More reliable NSE data
   - Better historical data access
   - Corporate actions data
   - Option chain data

See NSEPy documentation: https://nsepy.xyz/

---

**Remember**: This tool is for educational purposes. Always paper trade first and never risk money you can't afford to lose.
