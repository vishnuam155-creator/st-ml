"""
CSV Data Loader
Loads minute and daily OHLCV data from CSV files
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime
import pytz
import logging

logger = logging.getLogger(__name__)


class CSVDataLoader:
    """
    Loads OHLCV data from CSV files for minute and daily timeframes

    Expected CSV format:
    timestamp,open,high,low,close,volume
    2024-01-15 09:15:00,2450.50,2455.00,2448.00,2453.25,125000
    """

    def __init__(
        self,
        minute_data_dir: str,
        daily_data_dir: str,
        timezone: str = "Asia/Kolkata",
        date_format: str = "%Y-%m-%d %H:%M:%S"
    ):
        """
        Initialize CSV data loader

        Args:
            minute_data_dir: Directory containing minute-level CSV files
            daily_data_dir: Directory containing daily CSV files
            timezone: Exchange timezone
            date_format: Date format in CSV files
        """
        self.minute_data_dir = Path(minute_data_dir)
        self.daily_data_dir = Path(daily_data_dir)
        self.timezone = pytz.timezone(timezone)
        self.date_format = date_format

        logger.info(f"CSV Loader initialized with minute_dir={minute_data_dir}, daily_dir={daily_data_dir}")

    def load_minute_data(
        self,
        symbol: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        Load minute-level OHLCV data for a symbol

        Args:
            symbol: Stock symbol (e.g., "RELIANCE.NS")
            start_date: Start date (optional)
            end_date: End date (optional)

        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        file_path = self.minute_data_dir / f"{symbol}_minute.csv"

        if not file_path.exists():
            logger.warning(f"Minute data file not found: {file_path}")
            return pd.DataFrame()

        try:
            df = pd.read_csv(file_path)

            # Parse timestamp
            df['timestamp'] = pd.to_datetime(df['timestamp'], format=self.date_format)

            # Localize to timezone if naive
            if df['timestamp'].dt.tz is None:
                df['timestamp'] = df['timestamp'].dt.tz_localize(self.timezone)
            else:
                df['timestamp'] = df['timestamp'].dt.tz_convert(self.timezone)

            # Set as index
            df = df.set_index('timestamp').sort_index()

            # Filter by date range if provided
            if start_date:
                df = df[df.index >= start_date]
            if end_date:
                df = df[df.index <= end_date]

            # Ensure required columns
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            if not all(col in df.columns for col in required_cols):
                raise ValueError(f"Missing required columns. Expected: {required_cols}")

            logger.info(f"Loaded {len(df)} minute candles for {symbol}")
            return df[required_cols]

        except Exception as e:
            logger.error(f"Error loading minute data for {symbol}: {e}")
            return pd.DataFrame()

    def load_daily_data(
        self,
        symbol: str,
        lookback_days: int = 250
    ) -> pd.DataFrame:
        """
        Load daily OHLCV data for a symbol

        Args:
            symbol: Stock symbol
            lookback_days: Number of days to load

        Returns:
            DataFrame with daily OHLCV data
        """
        file_path = self.daily_data_dir / f"{symbol}_daily.csv"

        if not file_path.exists():
            logger.warning(f"Daily data file not found: {file_path}")
            return pd.DataFrame()

        try:
            df = pd.read_csv(file_path)

            # Parse date
            df['date'] = pd.to_datetime(df['date'], format="%Y-%m-%d")
            df = df.set_index('date').sort_index()

            # Take last N days
            df = df.tail(lookback_days)

            required_cols = ['open', 'high', 'low', 'close', 'volume']
            if not all(col in df.columns for col in required_cols):
                raise ValueError(f"Missing required columns. Expected: {required_cols}")

            logger.info(f"Loaded {len(df)} daily candles for {symbol}")
            return df[required_cols]

        except Exception as e:
            logger.error(f"Error loading daily data for {symbol}: {e}")
            return pd.DataFrame()

    def get_previous_close(self, symbol: str, date: datetime) -> Optional[float]:
        """
        Get previous day's closing price

        Args:
            symbol: Stock symbol
            date: Current date

        Returns:
            Previous close price or None
        """
        daily_data = self.load_daily_data(symbol, lookback_days=10)

        if daily_data.empty:
            return None

        # Find the close before the given date
        prev_data = daily_data[daily_data.index < date.date()]

        if prev_data.empty:
            return None

        return prev_data['close'].iloc[-1]

    def load_news_data(self, news_file: str) -> pd.DataFrame:
        """
        Load news/events data

        Expected format:
        date,symbol,event_type,description
        2024-01-15,RELIANCE.NS,earnings,Q3 Results

        Args:
            news_file: Path to news CSV file

        Returns:
            DataFrame with news data
        """
        file_path = Path(news_file)

        if not file_path.exists():
            logger.warning(f"News file not found: {file_path}")
            return pd.DataFrame()

        try:
            df = pd.read_csv(file_path)
            df['date'] = pd.to_datetime(df['date'])
            logger.info(f"Loaded {len(df)} news items")
            return df

        except Exception as e:
            logger.error(f"Error loading news data: {e}")
            return pd.DataFrame()

    def load_all_symbols(
        self,
        symbols: List[str],
        date: datetime,
        minute: bool = True
    ) -> Dict[str, pd.DataFrame]:
        """
        Load data for multiple symbols

        Args:
            symbols: List of symbols
            date: Trading date
            minute: Load minute data if True, else daily

        Returns:
            Dictionary mapping symbol to DataFrame
        """
        data = {}

        for symbol in symbols:
            if minute:
                df = self.load_minute_data(
                    symbol,
                    start_date=date.replace(hour=0, minute=0, second=0),
                    end_date=date.replace(hour=23, minute=59, second=59)
                )
            else:
                df = self.load_daily_data(symbol)

            if not df.empty:
                data[symbol] = df

        logger.info(f"Loaded data for {len(data)}/{len(symbols)} symbols")
        return data
