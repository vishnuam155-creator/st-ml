"""
Demo Helper Module
Provides fallback functionality for testing when live intraday data is unavailable
"""

import pandas as pd
from typing import List, Dict

from .data_fetcher import DataFetcher
from .technical_indicators import TechnicalIndicators


class DemoHelper:
    """
    Helper class for demo/testing mode
    Uses daily data when intraday data is unavailable
    """

    def __init__(self):
        self.data_fetcher = DataFetcher()
        self.tech_indicators = TechnicalIndicators()

    def get_usable_data(self, symbol: str, prefer_intraday: bool = True) -> pd.DataFrame:
        """
        Get usable data - tries intraday first, falls back to daily

        Args:
            symbol: Stock symbol
            prefer_intraday: Try intraday data first

        Returns:
            DataFrame with OHLCV data
        """
        data = pd.DataFrame()

        if prefer_intraday:
            # Try 5-min intraday data first
            data = self.data_fetcher.get_intraday_data(symbol, interval='5m')

            # If not enough data, try 15-min
            if data.empty or len(data) < 50:
                data = self.data_fetcher.get_intraday_data(symbol, interval='15m')

        # Fallback to daily data
        if data.empty or len(data) < 50:
            data = self.data_fetcher.get_historical_data(symbol, period='3mo', interval='1d')

        return data

    def simulate_intraday_from_daily(self, symbol: str) -> pd.DataFrame:
        """
        Simulate intraday data from recent daily data for demo purposes

        Args:
            symbol: Stock symbol

        Returns:
            DataFrame with simulated intraday-like data
        """
        # Get recent daily data
        daily_data = self.data_fetcher.get_historical_data(symbol, period='1mo', interval='1d')

        if daily_data.empty or len(daily_data) < 20:
            return pd.DataFrame()

        # For demo, we'll use the daily data but treat it as if it were intraday
        # In a real scenario, you'd want actual intraday data
        return daily_data

    def check_data_availability(self, symbols: List[str]) -> Dict:
        """
        Check data availability for multiple symbols

        Args:
            symbols: List of stock symbols

        Returns:
            Dictionary with availability status
        """
        status = {
            'intraday_available': [],
            'daily_only': [],
            'no_data': []
        }

        for symbol in symbols:
            intraday = self.data_fetcher.get_intraday_data(symbol, interval='5m')

            if not intraday.empty and len(intraday) >= 50:
                status['intraday_available'].append(symbol)
            else:
                daily = self.data_fetcher.get_historical_data(symbol, period='1mo', interval='1d')
                if not daily.empty and len(daily) >= 20:
                    status['daily_only'].append(symbol)
                else:
                    status['no_data'].append(symbol)

        return status
