"""
Data Fetcher Module
Fetches real-time and historical stock data from NSE
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pytz

class DataFetcher:
    """Fetches stock data for Indian markets"""

    def __init__(self):
        self.ist_tz = pytz.timezone('Asia/Kolkata')

    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current/latest price for a symbol"""
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period='1d', interval='1m')
            if not data.empty:
                return data['Close'].iloc[-1]
            return None
        except Exception as e:
            print(f"Error fetching price for {symbol}: {e}")
            return None

    def get_historical_data(
        self,
        symbol: str,
        period: str = '1mo',
        interval: str = '1d'
    ) -> pd.DataFrame:
        """
        Fetch historical data for a symbol

        Args:
            symbol: Stock symbol (e.g., 'RELIANCE.NS')
            period: Data period ('1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', 'max')
            interval: Data interval ('1m', '5m', '15m', '30m', '1h', '1d', '1wk', '1mo')

        Returns:
            DataFrame with OHLCV data
        """
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period, interval=interval)
            return data
        except Exception as e:
            print(f"Error fetching historical data for {symbol}: {e}")
            return pd.DataFrame()

    def get_intraday_data(self, symbol: str, interval: str = '5m') -> pd.DataFrame:
        """
        Fetch today's intraday data

        Args:
            symbol: Stock symbol
            interval: Candle interval ('1m', '5m', '15m')

        Returns:
            DataFrame with intraday OHLCV data
        """
        try:
            ticker = yf.Ticker(symbol)
            # Get last 5 days of data to ensure we have today's data
            data = ticker.history(period='5d', interval=interval)

            # Filter for today only
            today = datetime.now(self.ist_tz).date()
            if not data.empty:
                data.index = data.index.tz_convert(self.ist_tz)
                data = data[data.index.date == today]

            return data
        except Exception as e:
            print(f"Error fetching intraday data for {symbol}: {e}")
            return pd.DataFrame()

    def get_previous_close(self, symbol: str) -> Optional[float]:
        """Get previous day's closing price"""
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period='5d', interval='1d')
            if len(data) >= 2:
                return data['Close'].iloc[-2]
            return None
        except Exception as e:
            print(f"Error fetching previous close for {symbol}: {e}")
            return None

    def get_pre_open_data(self, symbol: str) -> Dict:
        """
        Get pre-open market data

        Returns:
            Dictionary with pre-open price, volume, etc.
        """
        try:
            ticker = yf.Ticker(symbol)
            # Get pre-market data
            data = ticker.history(period='1d', interval='1m', prepost=True)

            if data.empty:
                return {}

            # Convert to IST
            data.index = data.index.tz_convert(self.ist_tz)

            # Filter for pre-market hours (before 9:15 AM IST)
            today = datetime.now(self.ist_tz).date()
            pre_market_start = datetime.combine(today, datetime.strptime('09:00', '%H:%M').time())
            pre_market_start = self.ist_tz.localize(pre_market_start)
            pre_market_end = datetime.combine(today, datetime.strptime('09:15', '%H:%M').time())
            pre_market_end = self.ist_tz.localize(pre_market_end)

            pre_market_data = data[(data.index >= pre_market_start) & (data.index < pre_market_end)]

            if pre_market_data.empty:
                return {}

            return {
                'pre_open_price': pre_market_data['Close'].iloc[-1],
                'pre_open_volume': pre_market_data['Volume'].sum(),
                'pre_open_high': pre_market_data['High'].max(),
                'pre_open_low': pre_market_data['Low'].min(),
            }
        except Exception as e:
            print(f"Error fetching pre-open data for {symbol}: {e}")
            return {}

    def get_support_resistance_levels(
        self,
        symbol: str,
        lookback_days: int = 20
    ) -> Dict[str, List[float]]:
        """
        Calculate support and resistance levels based on historical data

        Args:
            symbol: Stock symbol
            lookback_days: Number of days to look back

        Returns:
            Dictionary with support and resistance levels
        """
        try:
            data = self.get_historical_data(symbol, period=f'{lookback_days}d', interval='1d')

            if data.empty or len(data) < 5:
                return {'support': [], 'resistance': []}

            # Find pivot points
            highs = data['High'].values
            lows = data['Low'].values

            resistance_levels = []
            support_levels = []

            # Find local maxima (resistance)
            for i in range(2, len(highs) - 2):
                if highs[i] > highs[i-1] and highs[i] > highs[i-2] and \
                   highs[i] > highs[i+1] and highs[i] > highs[i+2]:
                    resistance_levels.append(highs[i])

            # Find local minima (support)
            for i in range(2, len(lows) - 2):
                if lows[i] < lows[i-1] and lows[i] < lows[i-2] and \
                   lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                    support_levels.append(lows[i])

            # Sort and return top 3 of each
            resistance_levels = sorted(list(set(resistance_levels)), reverse=True)[:3]
            support_levels = sorted(list(set(support_levels)), reverse=True)[:3]

            return {
                'resistance': resistance_levels,
                'support': support_levels,
                'yesterday_high': data['High'].iloc[-1],
                'yesterday_low': data['Low'].iloc[-1],
            }
        except Exception as e:
            print(f"Error calculating S/R levels for {symbol}: {e}")
            return {'support': [], 'resistance': []}

    def get_average_volume(self, symbol: str, days: int = 20) -> Optional[float]:
        """Get average volume over specified days"""
        try:
            data = self.get_historical_data(symbol, period=f'{days}d', interval='1d')
            if not data.empty:
                return data['Volume'].mean()
            return None
        except Exception as e:
            print(f"Error calculating average volume for {symbol}: {e}")
            return None

    def get_index_trend(self, index_symbol: str) -> Dict:
        """
        Determine if index is in uptrend, downtrend, or sideways

        Args:
            index_symbol: Index symbol (e.g., '^NSEI' for Nifty)

        Returns:
            Dictionary with trend information
        """
        try:
            data = self.get_historical_data(index_symbol, period='3mo', interval='1d')

            if data.empty or len(data) < 50:
                return {'trend': 'unknown'}

            # Calculate moving averages
            data['SMA_20'] = data['Close'].rolling(window=20).mean()
            data['SMA_50'] = data['Close'].rolling(window=50).mean()

            latest = data.iloc[-1]
            current_price = latest['Close']
            sma_20 = latest['SMA_20']
            sma_50 = latest['SMA_50']

            # Determine trend
            if current_price > sma_20 > sma_50:
                trend = 'uptrend'
            elif current_price < sma_20 < sma_50:
                trend = 'downtrend'
            else:
                trend = 'sideways'

            return {
                'trend': trend,
                'current_price': current_price,
                'sma_20': sma_20,
                'sma_50': sma_50,
                'change_pct': ((current_price - data['Close'].iloc[-2]) / data['Close'].iloc[-2]) * 100
            }
        except Exception as e:
            print(f"Error determining trend for {index_symbol}: {e}")
            return {'trend': 'unknown'}
