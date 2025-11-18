"""
Generate Sample Data for Testing
Creates synthetic OHLCV data for testing the screener
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path


def generate_minute_data(symbol: str, date: datetime, base_price: float = 1000) -> pd.DataFrame:
    """
    Generate realistic minute-level OHLCV data for one day

    Args:
        symbol: Stock symbol
        date: Trading date
        base_price: Starting price

    Returns:
        DataFrame with minute data
    """
    # Market hours: 9:15 AM to 3:30 PM IST (6.25 hours = 375 minutes)
    start_time = date.replace(hour=9, minute=15, second=0, microsecond=0)
    num_minutes = 375

    timestamps = [start_time + timedelta(minutes=i) for i in range(num_minutes)]

    # Generate realistic price movement using random walk
    np.random.seed(hash(symbol + str(date)) % 2**32)

    returns = np.random.normal(0, 0.001, num_minutes)  # 0.1% std per minute
    prices = base_price * (1 + np.cumsum(returns))

    data = []
    for i, ts in enumerate(timestamps):
        price = prices[i]

        # Generate OHLC with some noise
        high = price * (1 + abs(np.random.normal(0, 0.002)))
        low = price * (1 - abs(np.random.normal(0, 0.002)))
        open_price = prices[i-1] if i > 0 else base_price
        close_price = price

        # Ensure OHLC relationships
        high = max(high, open_price, close_price)
        low = min(low, open_price, close_price)

        # Generate volume (higher in first/last hour)
        hour = ts.hour
        if hour == 9 or hour == 15:
            volume = int(np.random.uniform(50000, 150000))
        else:
            volume = int(np.random.uniform(20000, 80000))

        data.append({
            'timestamp': ts,
            'open': round(open_price, 2),
            'high': round(high, 2),
            'low': round(low, 2),
            'close': round(close_price, 2),
            'volume': volume
        })

    return pd.DataFrame(data)


def generate_daily_data(symbol: str, end_date: datetime, days: int = 250, base_price: float = 1000) -> pd.DataFrame:
    """
    Generate daily OHLCV data

    Args:
        symbol: Stock symbol
        end_date: End date
        days: Number of days
        base_price: Starting price

    Returns:
        DataFrame with daily data
    """
    np.random.seed(hash(symbol) % 2**32)

    dates = [end_date - timedelta(days=i) for i in range(days)]
    dates.reverse()
    dates = [d for d in dates if d.weekday() < 5]  # Remove weekends

    returns = np.random.normal(0, 0.015, len(dates))  # 1.5% daily std
    prices = base_price * (1 + np.cumsum(returns))

    data = []
    for i, date in enumerate(dates):
        price = prices[i]

        high = price * (1 + abs(np.random.normal(0, 0.02)))
        low = price * (1 - abs(np.random.normal(0, 0.02)))
        open_price = prices[i-1] if i > 0 else base_price
        close_price = price

        high = max(high, open_price, close_price)
        low = min(low, open_price, close_price)

        volume = int(np.random.uniform(5000000, 15000000))

        data.append({
            'date': date.strftime('%Y-%m-%d'),
            'open': round(open_price, 2),
            'high': round(high, 2),
            'low': round(low, 2),
            'close': round(close_price, 2),
            'volume': volume
        })

    return pd.DataFrame(data)


def main():
    """Generate sample data for testing"""
    print("Generating sample data...")

    # Create directories
    Path('data/sample/minute').mkdir(parents=True, exist_ok=True)
    Path('data/sample/daily').mkdir(parents=True, exist_ok=True)

    # Sample stocks with realistic base prices
    stocks = {
        'RELIANCE.NS': 2450,
        'TCS.NS': 3550,
        'INFY.NS': 1495,
        'HDFCBANK.NS': 1650,
        'ICICIBANK.NS': 1020
    }

    # Indices
    indices = {
        '^NSEI': 21500,
        '^NSEBANK': 46500
    }

    # Test date
    test_date = datetime(2024, 1, 15)

    # Generate minute data for test date
    print("\nGenerating minute data...")
    for symbol, base_price in stocks.items():
        minute_data = generate_minute_data(symbol, test_date, base_price)
        output_file = f'data/sample/minute/{symbol}_minute.csv'
        minute_data.to_csv(output_file, index=False)
        print(f"  ✅ {symbol}: {len(minute_data)} candles -> {output_file}")

    # Generate daily data
    print("\nGenerating daily data...")
    for symbol, base_price in {**stocks, **indices}.items():
        daily_data = generate_daily_data(symbol, test_date, days=250, base_price=base_price)
        output_file = f'data/sample/daily/{symbol}_daily.csv'
        daily_data.to_csv(output_file, index=False)
        print(f"  ✅ {symbol}: {len(daily_data)} candles -> {output_file}")

    # Generate news file
    print("\nGenerating news data...")
    news_data = pd.DataFrame([
        {
            'date': '2024-01-15',
            'symbol': 'RELIANCE.NS',
            'event_type': 'earnings',
            'description': 'Q3 FY24 Results'
        },
        {
            'date': '2024-01-15',
            'symbol': 'TCS.NS',
            'event_type': 'dividend',
            'description': 'Dividend Declaration'
        }
    ])
    news_data.to_csv('data/sample/news.csv', index=False)
    print(f"  ✅ News data -> data/sample/news.csv")

    print("\n✅ Sample data generation complete!")
    print("\nYou can now run the screener:")
    print("  python -m production.cli.main screen --date 2024-01-15 --mode full")


if __name__ == '__main__':
    main()
