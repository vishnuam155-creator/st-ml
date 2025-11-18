"""
Average True Range (ATR) Indicator
"""

import pandas as pd
import numpy as np


class ATR:
    """Average True Range calculator for volatility measurement"""

    @staticmethod
    def calculate(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calculate Average True Range

        True Range is the greatest of:
        - Current High - Current Low
        - |Current High - Previous Close|
        - |Current Low - Previous Close|

        ATR is the moving average of True Range

        Args:
            df: DataFrame with OHLCV data
            period: ATR period (default 14)

        Returns:
            Series with ATR values
        """
        if len(df) < period:
            return pd.Series(index=df.index, dtype=float)

        high = df['high']
        low = df['low']
        close = df['close']

        # Calculate True Range components
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()

        # True Range is the maximum of the three
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # ATR is the moving average of True Range
        atr = true_range.ewm(span=period, adjust=False).mean()

        return atr

    @staticmethod
    def calculate_stop_loss(
        entry_price: float,
        atr: float,
        multiplier: float = 1.5,
        direction: str = 'long'
    ) -> float:
        """
        Calculate stop-loss using ATR

        Args:
            entry_price: Entry price
            atr: ATR value
            multiplier: ATR multiplier (default 1.5)
            direction: 'long' or 'short'

        Returns:
            Stop-loss price
        """
        if pd.isna(atr):
            return entry_price

        if direction == 'long':
            stop_loss = entry_price - (atr * multiplier)
        else:  # short
            stop_loss = entry_price + (atr * multiplier)

        return round(stop_loss, 2)

    @staticmethod
    def get_volatility_level(atr: float, price: float) -> str:
        """
        Categorize volatility level based on ATR

        Args:
            atr: ATR value
            price: Current price

        Returns:
            'low', 'medium', or 'high'
        """
        if pd.isna(atr) or price == 0:
            return 'unknown'

        atr_percent = (atr / price) * 100

        if atr_percent < 1.0:
            return 'low'
        elif atr_percent < 2.0:
            return 'medium'
        else:
            return 'high'
