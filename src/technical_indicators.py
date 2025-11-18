"""
Technical Indicators Module
Calculates various technical indicators for trading strategies
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional


class TechnicalIndicators:
    """Calculate technical indicators for stock analysis"""

    @staticmethod
    def calculate_ema(data: pd.DataFrame, period: int, column: str = 'Close') -> pd.Series:
        """
        Calculate Exponential Moving Average

        Args:
            data: DataFrame with OHLCV data
            period: EMA period
            column: Column to calculate EMA on

        Returns:
            Series with EMA values
        """
        return data[column].ewm(span=period, adjust=False).mean()

    @staticmethod
    def calculate_sma(data: pd.DataFrame, period: int, column: str = 'Close') -> pd.Series:
        """Calculate Simple Moving Average"""
        return data[column].rolling(window=period).mean()

    @staticmethod
    def calculate_vwap(data: pd.DataFrame) -> pd.Series:
        """
        Calculate Volume Weighted Average Price (VWAP)

        VWAP = Cumulative(Typical Price * Volume) / Cumulative(Volume)
        Typical Price = (High + Low + Close) / 3
        """
        typical_price = (data['High'] + data['Low'] + data['Close']) / 3
        cumulative_tp_volume = (typical_price * data['Volume']).cumsum()
        cumulative_volume = data['Volume'].cumsum()

        vwap = cumulative_tp_volume / cumulative_volume
        return vwap

    @staticmethod
    def calculate_atr(data: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calculate Average True Range (ATR)

        Args:
            data: DataFrame with OHLCV data
            period: ATR period (default 14)

        Returns:
            Series with ATR values
        """
        high = data['High']
        low = data['Low']
        close = data['Close']

        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())

        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean()

        return atr

    @staticmethod
    def calculate_rsi(data: pd.DataFrame, period: int = 14, column: str = 'Close') -> pd.Series:
        """
        Calculate Relative Strength Index (RSI)

        Args:
            data: DataFrame with OHLCV data
            period: RSI period (default 14)
            column: Column to calculate RSI on

        Returns:
            Series with RSI values (0-100)
        """
        delta = data[column].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    @staticmethod
    def calculate_bollinger_bands(
        data: pd.DataFrame,
        period: int = 20,
        std_dev: int = 2,
        column: str = 'Close'
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate Bollinger Bands

        Args:
            data: DataFrame with OHLCV data
            period: Moving average period
            std_dev: Number of standard deviations
            column: Column to calculate on

        Returns:
            Tuple of (upper_band, middle_band, lower_band)
        """
        middle_band = data[column].rolling(window=period).mean()
        std = data[column].rolling(window=period).std()

        upper_band = middle_band + (std * std_dev)
        lower_band = middle_band - (std * std_dev)

        return upper_band, middle_band, lower_band

    @staticmethod
    def calculate_macd(
        data: pd.DataFrame,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
        column: str = 'Close'
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate MACD (Moving Average Convergence Divergence)

        Args:
            data: DataFrame with OHLCV data
            fast: Fast EMA period
            slow: Slow EMA period
            signal: Signal line period
            column: Column to calculate on

        Returns:
            Tuple of (macd_line, signal_line, histogram)
        """
        ema_fast = data[column].ewm(span=fast, adjust=False).mean()
        ema_slow = data[column].ewm(span=slow, adjust=False).mean()

        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line

        return macd_line, signal_line, histogram

    @staticmethod
    def detect_reversal_candle(data: pd.DataFrame, index: int = -1) -> dict:
        """
        Detect bullish or bearish reversal candle patterns

        Args:
            data: DataFrame with OHLCV data
            index: Index of candle to check (default -1 for latest)

        Returns:
            Dictionary with reversal pattern information
        """
        if len(data) < abs(index) + 2:
            return {'type': 'none', 'strength': 0}

        current = data.iloc[index]
        previous = data.iloc[index - 1]

        open_price = current['Open']
        close_price = current['Close']
        high_price = current['High']
        low_price = current['Low']

        body = abs(close_price - open_price)
        upper_wick = high_price - max(open_price, close_price)
        lower_wick = min(open_price, close_price) - low_price
        total_range = high_price - low_price

        result = {'type': 'none', 'strength': 0, 'pattern': 'none'}

        # Bullish Hammer (long lower wick, small body, small/no upper wick)
        if lower_wick > 2 * body and upper_wick < body * 0.5 and close_price > open_price:
            result = {'type': 'bullish', 'strength': 0.8, 'pattern': 'hammer'}

        # Bullish Engulfing (current candle engulfs previous bearish candle)
        elif close_price > open_price and previous['Close'] < previous['Open'] and \
             close_price > previous['Open'] and open_price < previous['Close']:
            result = {'type': 'bullish', 'strength': 0.9, 'pattern': 'engulfing'}

        # Bearish Shooting Star (long upper wick, small body, small/no lower wick)
        elif upper_wick > 2 * body and lower_wick < body * 0.5 and close_price < open_price:
            result = {'type': 'bearish', 'strength': 0.8, 'pattern': 'shooting_star'}

        # Bearish Engulfing (current candle engulfs previous bullish candle)
        elif close_price < open_price and previous['Close'] > previous['Open'] and \
             close_price < previous['Open'] and open_price > previous['Close']:
            result = {'type': 'bearish', 'strength': 0.9, 'pattern': 'engulfing'}

        # Bullish Doji (very small body, potential reversal at support)
        elif body < total_range * 0.1 and close_price > open_price:
            result = {'type': 'bullish', 'strength': 0.6, 'pattern': 'doji'}

        # Bearish Doji
        elif body < total_range * 0.1 and close_price < open_price:
            result = {'type': 'bearish', 'strength': 0.6, 'pattern': 'doji'}

        # Simple bullish/bearish candle with good volume
        elif close_price > open_price and body > total_range * 0.6:
            result = {'type': 'bullish', 'strength': 0.5, 'pattern': 'bullish_candle'}
        elif close_price < open_price and body > total_range * 0.6:
            result = {'type': 'bearish', 'strength': 0.5, 'pattern': 'bearish_candle'}

        return result

    @staticmethod
    def calculate_volume_surge(data: pd.DataFrame, lookback: int = 10) -> float:
        """
        Calculate if current volume is a surge compared to average

        Args:
            data: DataFrame with OHLCV data
            lookback: Number of periods to calculate average

        Returns:
            Volume multiplier (e.g., 2.0 means current volume is 2x average)
        """
        if len(data) < lookback + 1:
            return 1.0

        current_volume = data['Volume'].iloc[-1]
        avg_volume = data['Volume'].iloc[-lookback-1:-1].mean()

        if avg_volume == 0:
            return 1.0

        return current_volume / avg_volume

    @staticmethod
    def is_higher_high_higher_low(data: pd.DataFrame, periods: int = 3) -> bool:
        """
        Check if price is making higher highs and higher lows (uptrend)

        Args:
            data: DataFrame with OHLCV data
            periods: Number of periods to check

        Returns:
            True if making HH and HL
        """
        if len(data) < periods + 1:
            return False

        highs = data['High'].iloc[-periods-1:].values
        lows = data['Low'].iloc[-periods-1:].values

        # Check if each high is higher than previous
        higher_highs = all(highs[i] > highs[i-1] for i in range(1, len(highs)))
        # Check if each low is higher than previous
        higher_lows = all(lows[i] > lows[i-1] for i in range(1, len(lows)))

        return higher_highs and higher_lows

    @staticmethod
    def is_lower_high_lower_low(data: pd.DataFrame, periods: int = 3) -> bool:
        """
        Check if price is making lower highs and lower lows (downtrend)

        Args:
            data: DataFrame with OHLCV data
            periods: Number of periods to check

        Returns:
            True if making LH and LL
        """
        if len(data) < periods + 1:
            return False

        highs = data['High'].iloc[-periods-1:].values
        lows = data['Low'].iloc[-periods-1:].values

        # Check if each high is lower than previous
        lower_highs = all(highs[i] < highs[i-1] for i in range(1, len(highs)))
        # Check if each low is lower than previous
        lower_lows = all(lows[i] < lows[i-1] for i in range(1, len(lows)))

        return lower_highs and lower_lows

    @staticmethod
    def add_all_indicators(data: pd.DataFrame, config: dict = None) -> pd.DataFrame:
        """
        Add all common technical indicators to the dataframe

        Args:
            data: DataFrame with OHLCV data
            config: Configuration dictionary with indicator parameters

        Returns:
            DataFrame with all indicators added
        """
        if config is None:
            config = {
                'ema_fast': 20,
                'ema_slow': 200,
                'atr_period': 14,
                'rsi_period': 14,
            }

        df = data.copy()

        # EMAs
        df['EMA_20'] = TechnicalIndicators.calculate_ema(df, config.get('ema_fast', 20))
        df['EMA_200'] = TechnicalIndicators.calculate_ema(df, config.get('ema_slow', 200))

        # VWAP (for intraday data)
        df['VWAP'] = TechnicalIndicators.calculate_vwap(df)

        # ATR
        df['ATR'] = TechnicalIndicators.calculate_atr(df, config.get('atr_period', 14))

        # RSI
        df['RSI'] = TechnicalIndicators.calculate_rsi(df, config.get('rsi_period', 14))

        # Volume surge
        df['Volume_Avg_10'] = df['Volume'].rolling(window=10).mean()
        df['Volume_Ratio'] = df['Volume'] / df['Volume_Avg_10']

        return df
