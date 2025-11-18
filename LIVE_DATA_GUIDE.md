# Live Data Fetching Guide for NSE Stocks

## 🔍 Understanding the Issue

**yfinance limitations with NSE**: The free yfinance library has limited/unreliable access to real-time NSE intraday data. This is a known limitation, not a bug in the screener.

### Common Symptoms:
- "Insufficient data" errors
- Empty dataframes
- Only getting daily data, not 5-minute candles
- Works for some stocks but not others
- Works sometimes but not always

## 🛠️ Immediate Solutions

### 1. Run the Diagnostic Tool (Recommended First Step)

```bash
python diagnose_data.py
```

This will:
- ✅ Check if market is currently open
- ✅ Test data availability for sample stocks
- ✅ Show what intervals are available
- ✅ Give specific recommendations

### 2. Use Demo Mode (Works Anytime)

```bash
python main.py --mode full --capital 100000 --demo
```

**Benefits:**
- ✅ Works 24/7 (doesn't need market to be open)
- ✅ Uses historical daily data
- ✅ Great for learning and testing
- ✅ Perfect for backtesting strategies
- ✅ No data fetching issues

### 3. Run During Market Hours (Best for Live Trading)

**Indian Market Hours (IST):**
- Pre-market: 9:00 AM - 9:15 AM
- Regular: 9:15 AM - 3:30 PM
- Post-market: 3:30 PM - 4:00 PM

**Best time to run:**
```bash
# Between 9:30 AM - 3:00 PM IST
python main.py --mode full --capital 100000
```

## 📊 Data Availability by Time

| Time (IST) | Live Intraday Data | Daily Data | Recommended Mode |
|------------|-------------------|------------|------------------|
| Before 9:00 AM | ❌ No | ✅ Yes | `--demo` |
| 9:00 - 9:15 AM (Pre-market) | ⚠️ Limited | ✅ Yes | `--demo` or wait |
| 9:15 - 3:30 PM (Market hours) | ✅ Yes* | ✅ Yes | Normal or `--demo` |
| After 3:30 PM | ⚠️ Day's data only | ✅ Yes | `--demo` |
| Weekends | ❌ No | ✅ Yes | `--demo` |

*Even during market hours, yfinance may have delays or gaps

## 🚀 Production-Ready Solutions

For serious/live trading, yfinance is NOT recommended. Use these alternatives:

### Free Options:

#### 1. NSEPy (Recommended for Indian Markets)

More reliable for NSE data:

```bash
pip install nsepy
```

**Advantages:**
- ✅ Direct NSE data source
- ✅ More reliable than yfinance
- ✅ Historical data
- ✅ Corporate actions included

**Disadvantages:**
- ❌ No real-time intraday (only daily)
- ❌ Data with 1-day delay

**Use case:** Good for daily analysis, not real-time intraday

#### 2. Alpha Vantage (Limited Free Tier)

```bash
pip install alpha-vantage
```

Get free API key: https://www.alphavantage.co/support/#api-key

**Limits:** 5 API calls/minute, 500 calls/day (free tier)

### Paid Options (Professional):

#### 1. Zerodha Kite Connect
- **Cost:** ₹2,000/month
- **Best for:** Retail traders with Zerodha account
- **Features:** Real-time data, order execution, historical data
- **Link:** https://kite.trade/

#### 2. Upstox API
- **Cost:** ₹1,499/month
- **Best for:** Retail traders with Upstox account
- **Features:** Real-time streaming, historical data, order placement
- **Link:** https://upstox.com/developer/

#### 3. Dhan HQ API
- **Cost:** Free with Dhan account
- **Best for:** Cost-conscious traders
- **Features:** Real-time data, order execution
- **Link:** https://dhanhq.co/

#### 4. IIFL Markets API
- **Cost:** Varies
- **Best for:** Professional traders
- **Features:** Enterprise-grade data and execution

## 🔧 Troubleshooting Steps

### Step 1: Diagnose the Issue

```bash
python diagnose_data.py
```

This will tell you exactly what's wrong.

### Step 2: Check Market Status

Market must be open for live intraday data:

```python
from datetime import datetime
import pytz

ist = pytz.timezone('Asia/Kolkata')
now = datetime.now(ist)
print(f"Current time (IST): {now}")

# Market hours: 9:15 AM - 3:30 PM, Mon-Fri
```

### Step 3: Test Single Stock

```python
from src.enhanced_data_fetcher import EnhancedDataFetcher

fetcher = EnhancedDataFetcher()
data = fetcher.get_intraday_data_robust('RELIANCE.NS', interval='5m', verbose=True)
print(f"Got {len(data)} candles")
```

### Step 4: Use Fallback Intervals

If 5-minute data fails, try 15-minute:

```bash
# Modify config/config.py
TIMEFRAMES = {
    'intraday_5min': '15m',  # Change from '5m'
}
```

## 📝 Quick Reference

### Working Configuration (Market Hours)

```bash
# Morning setup (9:00 AM)
python main.py --mode premarket

# Live trading (9:30 AM - 3:00 PM)
python main.py --mode full --capital 100000
```

### Working Configuration (Anytime)

```bash
# Testing/Learning (anytime)
python main.py --mode full --capital 100000 --demo

# With ML predictions
python main.py --mode full --capital 100000 --demo --use-ml
```

## 🎯 Recommended Workflow

### For Learning/Testing:
1. ✅ Use `--demo` mode
2. ✅ Test with small stock list
3. ✅ Understand the logic
4. ✅ Tune parameters

### For Paper Trading:
1. ✅ Run during market hours (9:30 AM - 3:00 PM)
2. ✅ Use `--demo` as fallback if data issues
3. ✅ Track paper trades manually
4. ✅ Analyze performance

### For Live Trading:
1. ⚠️ **Don't use yfinance** for production
2. ✅ Get Zerodha/Upstox API
3. ✅ Integrate proper data source
4. ✅ Test extensively first

## 💡 Understanding yfinance Limitations

### Why yfinance fails for NSE intraday:

1. **Not official API**: yfinance scrapes Yahoo Finance
2. **Rate limiting**: Too many requests = blocked
3. **Data delays**: Real-time data not guaranteed
4. **Missing candles**: Some 5-min candles may be missing
5. **Geographic restrictions**: May not work from all locations

### What yfinance IS good for:

- ✅ Historical daily data
- ✅ US stocks (more reliable)
- ✅ Learning and prototyping
- ✅ Backtesting
- ✅ Free testing

### What yfinance is NOT good for:

- ❌ Production live trading
- ❌ Real-time NSE intraday
- ❌ High-frequency strategies
- ❌ Mission-critical applications

## 🔐 Best Practices

1. **Always use demo mode for testing**
   ```bash
   python main.py --mode full --capital 100000 --demo
   ```

2. **Run diagnostic before live trading**
   ```bash
   python diagnose_data.py
   ```

3. **Have fallback strategy**
   - Primary: Live API (if available)
   - Fallback: Demo mode with daily data

4. **Don't trade real money with yfinance**
   - Get proper data source first
   - Paper trade extensively
   - Understand all limitations

## 📞 Getting More Help

### If diagnostic shows "Market CLOSED":
→ Use `--demo` mode or wait for market hours

### If diagnostic shows data available but screener fails:
→ Check TROUBLESHOOTING.md
→ Try with single stock
→ Check internet connection

### If you need real-time data:
→ Consider paid API (Zerodha, Upstox)
→ Or wait for market hours with current setup

## ✅ Summary

| Scenario | Solution | Command |
|----------|----------|---------|
| Learning the system | Demo mode | `python main.py --mode full --demo` |
| Testing outside hours | Demo mode | `python main.py --mode full --demo` |
| Paper trading (market hours) | Normal mode | `python main.py --mode full` |
| Live trading | Paid API + Demo fallback | Use proper API |
| Data issues | Run diagnostic | `python diagnose_data.py` |

---

**Remember:** This tool is educational. For live trading, always use professional-grade data sources and never risk money you can't afford to lose.
