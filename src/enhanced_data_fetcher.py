"""
Enhanced Data Fetcher with better error handling and retry logic
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pytz
import time


class EnhancedDataFetcher:
    """
    Enhanced data fetcher with retry logic and better error handling
    """

    def __init__(self):
        self.ist_tz = pytz.timezone('Asia/Kolkata')
        self.max_retries = 3
        self.retry_delay = 2  # seconds

    def get_intraday_data_robust(
        self,
        symbol: str,
        interval: str = '5m',
        verbose: bool = False
    ) -> pd.DataFrame:
        """
        Fetch intraday data with multiple fallback strategies

        Args:
            symbol: Stock symbol
            interval: Candle interval
            verbose: Print debug information

        Returns:
            DataFrame with intraday data
        """
        if verbose:
            print(f"    Fetching {interval} data for {symbol}...")

        # Strategy 1: Try today's data with multiple period options
        for period in ['1d', '2d', '5d', '7d']:
            try:
                if verbose:
                    print(f"      Trying period={period}...")

                ticker = yf.Ticker(symbol)
                data = ticker.history(period=period, interval=interval)

                if not data.empty:
                    # Convert to IST
                    if data.index.tz is None:
                        data.index = data.index.tz_localize('UTC')
                    data.index = data.index.tz_convert(self.ist_tz)

                    # Filter for today
                    today = datetime.now(self.ist_tz).date()
                    data = data[data.index.date == today]

                    if len(data) >= 10:  # At least 10 candles (50 minutes of data)
                        if verbose:
                            print(f"      ✓ Got {len(data)} candles")
                        return data
                    elif verbose:
                        print(f"      ✗ Only {len(data)} candles")

                time.sleep(0.5)  # Brief delay between attempts

            except Exception as e:
                if verbose:
                    print(f"      ✗ Error with period={period}: {e}")
                continue

        # Strategy 2: Try with specific date range
        try:
            if verbose:
                print(f"      Trying specific date range...")

            today = datetime.now(self.ist_tz).date()
            start_date = today - timedelta(days=1)
            end_date = today + timedelta(days=1)

            ticker = yf.Ticker(symbol)
            data = ticker.history(start=start_date, end=end_date, interval=interval)

            if not data.empty:
                if data.index.tz is None:
                    data.index = data.index.tz_localize('UTC')
                data.index = data.index.tz_convert(self.ist_tz)
                data = data[data.index.date == today]

                if len(data) >= 10:
                    if verbose:
                        print(f"      ✓ Got {len(data)} candles via date range")
                    return data

        except Exception as e:
            if verbose:
                print(f"      ✗ Date range failed: {e}")

        # Strategy 3: Try 15-min interval if 5-min failed
        if interval == '5m':
            if verbose:
                print(f"      Trying 15m interval as fallback...")

            result = self.get_intraday_data_robust(symbol, interval='15m', verbose=False)
            if not result.empty:
                if verbose:
                    print(f"      ✓ Got {len(result)} candles with 15m interval")
                return result

        # All strategies failed
        if verbose:
            print(f"      ✗ All strategies failed")
        return pd.DataFrame()

    def get_current_price_robust(self, symbol: str, verbose: bool = False) -> Optional[float]:
        """
        Get current price with multiple fallback methods

        Args:
            symbol: Stock symbol
            verbose: Print debug info

        Returns:
            Current price or None
        """
        # Method 1: Latest minute data
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period='1d', interval='1m')
            if not data.empty:
                price = data['Close'].iloc[-1]
                if verbose:
                    print(f"    ✓ Current price from 1m data: ₹{price:.2f}")
                return price
        except:
            pass

        # Method 2: 5-min data
        try:
            data = self.get_intraday_data_robust(symbol, interval='5m', verbose=False)
            if not data.empty:
                price = data['Close'].iloc[-1]
                if verbose:
                    print(f"    ✓ Current price from 5m data: ₹{price:.2f}")
                return price
        except:
            pass

        # Method 3: Daily data (last close)
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period='2d', interval='1d')
            if not data.empty:
                price = data['Close'].iloc[-1]
                if verbose:
                    print(f"    ⚠ Current price from daily close: ₹{price:.2f}")
                return price
        except:
            pass

        # Method 4: ticker.info (least reliable for NSE)
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            if 'currentPrice' in info:
                price = info['currentPrice']
                if verbose:
                    print(f"    ⚠ Current price from info: ₹{price:.2f}")
                return price
            elif 'regularMarketPrice' in info:
                price = info['regularMarketPrice']
                if verbose:
                    print(f"    ⚠ Current price from regularMarketPrice: ₹{price:.2f}")
                return price
        except:
            pass

        if verbose:
            print(f"    ✗ Could not get current price for {symbol}")
        return None

    def diagnose_data_availability(self, symbol: str) -> Dict:
        """
        Diagnose what data is available for a symbol

        Args:
            symbol: Stock symbol

        Returns:
            Dictionary with availability information
        """
        print(f"\n{'='*60}")
        print(f"DIAGNOSING DATA AVAILABILITY FOR {symbol}")
        print(f"{'='*60}")

        result = {
            'symbol': symbol,
            'timestamp': datetime.now(self.ist_tz),
            'available_data': []
        }

        # Check 1-minute data
        print("\n1. Checking 1-minute data...")
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period='1d', interval='1m')
            if not data.empty:
                print(f"   ✓ Available: {len(data)} candles")
                result['available_data'].append({
                    'interval': '1m',
                    'candles': len(data),
                    'latest_time': data.index[-1] if len(data) > 0 else None
                })
            else:
                print(f"   ✗ No data available")
        except Exception as e:
            print(f"   ✗ Error: {e}")

        # Check 5-minute data
        print("\n2. Checking 5-minute data...")
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period='5d', interval='5m')
            if not data.empty:
                print(f"   ✓ Available: {len(data)} candles")
                result['available_data'].append({
                    'interval': '5m',
                    'candles': len(data),
                    'latest_time': data.index[-1] if len(data) > 0 else None
                })
            else:
                print(f"   ✗ No data available")
        except Exception as e:
            print(f"   ✗ Error: {e}")

        # Check 15-minute data
        print("\n3. Checking 15-minute data...")
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period='5d', interval='15m')
            if not data.empty:
                print(f"   ✓ Available: {len(data)} candles")
                result['available_data'].append({
                    'interval': '15m',
                    'candles': len(data),
                    'latest_time': data.index[-1] if len(data) > 0 else None
                })
            else:
                print(f"   ✗ No data available")
        except Exception as e:
            print(f"   ✗ Error: {e}")

        # Check daily data
        print("\n4. Checking daily data...")
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period='1mo', interval='1d')
            if not data.empty:
                print(f"   ✓ Available: {len(data)} candles")
                result['available_data'].append({
                    'interval': '1d',
                    'candles': len(data),
                    'latest_time': data.index[-1] if len(data) > 0 else None
                })
            else:
                print(f"   ✗ No data available")
        except Exception as e:
            print(f"   ✗ Error: {e}")

        # Check current price
        print("\n5. Checking current price...")
        price = self.get_current_price_robust(symbol, verbose=True)
        result['current_price'] = price

        # Market status
        print("\n6. Market Status:")
        now = datetime.now(self.ist_tz)
        market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
        market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)

        if market_open <= now <= market_close and now.weekday() < 5:
            print("   ✓ Market is OPEN")
            result['market_status'] = 'OPEN'
        else:
            print("   ✗ Market is CLOSED")
            result['market_status'] = 'CLOSED'

        print(f"\n{'='*60}\n")

        return result


def test_data_fetching(symbols: List[str] = None):
    """
    Test data fetching for multiple symbols

    Args:
        symbols: List of symbols to test (default: sample of 3)
    """
    if symbols is None:
        symbols = ['RELIANCE.NS', 'TCS.NS', 'INFY.NS']

    fetcher = EnhancedDataFetcher()

    print("\n" + "="*60)
    print("TESTING DATA FETCHING FOR NSE STOCKS")
    print("="*60)

    results = []

    for symbol in symbols:
        print(f"\n\nTesting {symbol}...")
        print("-" * 60)

        # Diagnose
        diagnosis = fetcher.diagnose_data_availability(symbol)
        results.append(diagnosis)

        # Try robust fetch
        print(f"\nAttempting robust intraday fetch...")
        data = fetcher.get_intraday_data_robust(symbol, interval='5m', verbose=True)

        if not data.empty:
            print(f"\n✓ SUCCESS: Got {len(data)} candles")
            print(f"  Latest candle: {data.index[-1]}")
            print(f"  Latest close: ₹{data['Close'].iloc[-1]:.2f}")
        else:
            print(f"\n✗ FAILED: Could not get intraday data")

    # Summary
    print("\n\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    for result in results:
        print(f"\n{result['symbol']}:")
        print(f"  Market Status: {result.get('market_status', 'Unknown')}")
        print(f"  Current Price: ₹{result.get('current_price', 0):.2f}" if result.get('current_price') else "  Current Price: N/A")
        print(f"  Available intervals: {', '.join([d['interval'] for d in result['available_data']])}")

    print("\n" + "="*60)


if __name__ == '__main__':
    # Run diagnostics
    test_data_fetching()
