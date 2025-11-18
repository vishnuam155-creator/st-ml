"""
Configuration file for Intraday Stock Screener
"""

# Trading Parameters
TRADING_CONFIG = {
    # Pre-Market Screening Time
    'pre_market_start': '08:45',
    'pre_market_end': '09:15',

    # Live Market Screening Time
    'live_market_start': '09:20',

    # Market Close
    'market_close': '15:30',

    # Gap Filter
    'gap_min_pct': 0.3,
    'gap_max_pct': 2.0,

    # Volume Filter
    'volume_lookback_days': 20,
    'min_volume_multiplier': 1.2,  # Pre-open volume should be 1.2x average

    # Range Filter
    'min_range_pct': 0.8,  # Minimum daily range as % of price

    # Candidate Limits
    'pre_market_candidates': 8,
    'live_market_candidates': 4,

    # Technical Indicators
    'ema_fast': 20,
    'ema_slow': 200,

    # Risk Management
    'risk_per_trade_pct': 1.0,  # 1% of capital per trade
    'max_trades_per_day': 3,
    'max_consecutive_losses': 2,
    'atr_period': 14,
    'stop_loss_atr_multiplier': 1.5,
}

# Nifty 50 Stock List (as of 2025)
NIFTY_50_STOCKS = [
    'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ICICIBANK.NS',
    'HINDUNILVR.NS', 'ITC.NS', 'SBIN.NS', 'BHARTIARTL.NS', 'KOTAKBANK.NS',
    'LT.NS', 'AXISBANK.NS', 'ASIANPAINT.NS', 'MARUTI.NS', 'BAJFINANCE.NS',
    'HCLTECH.NS', 'WIPRO.NS', 'ULTRACEMCO.NS', 'ONGC.NS', 'SUNPHARMA.NS',
    'TITAN.NS', 'NESTLEIND.NS', 'NTPC.NS', 'TATAMOTORS.NS', 'POWERGRID.NS',
    'M&M.NS', 'BAJAJFINSV.NS', 'TECHM.NS', 'ADANIPORTS.NS', 'DIVISLAB.NS',
    'TATASTEEL.NS', 'COALINDIA.NS', 'HINDALCO.NS', 'JSWSTEEL.NS', 'GRASIM.NS',
    'INDUSINDBK.NS', 'DRREDDY.NS', 'CIPLA.NS', 'EICHERMOT.NS', 'HEROMOTOCO.NS',
    'APOLLOHOSP.NS', 'BRITANNIA.NS', 'BPCL.NS', 'TATACONSUM.NS', 'SBILIFE.NS',
    'LTIM.NS', 'ADANIENT.NS', 'BAJAJ-AUTO.NS', 'HDFCLIFE.NS', 'SHRIRAMFIN.NS'
]

# Index Symbols
INDICES = {
    'nifty': '^NSEI',
    'banknifty': '^NSEBANK'
}

# Chart Timeframes
TIMEFRAMES = {
    'pre_market': '1d',  # Daily for gap analysis
    'intraday_5min': '5m',
    'intraday_15min': '15m',
}

# News Keywords (for filtering important news)
NEWS_KEYWORDS = [
    'result', 'results', 'earnings', 'merger', 'acquisition',
    'rbi', 'government', 'policy', 'deal', 'contract',
    'bonus', 'dividend', 'split', 'buyback'
]
