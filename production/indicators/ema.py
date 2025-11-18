"""
Exponential Moving Average (EMA) Indicator
"""

import pandas as pd
import numpy as np
from typing import Union


class EMA:
    """Exponential Moving Average calculator"""

    @staticmethod
    def calculate(
        data: pd.Series,
        period: int,
        adjust: bool = False
    ) -> pd.Series:
        """
        Calculate Exponential Moving Average

        Args:
            data: Price series (typically 'close')
            period: EMA period
            adjust: Use adjusted EMA (default False for standard EMA)

        Returns:
            Series with EMA values
        """
        if len(data) < period:
            return pd.Series(index=data.index, dtype=float)

        ema = data.ewm(span=period, adjust=adjust).mean()
        return ema

    @staticmethod
    def calculate_on_dataframe(
        df: pd.DataFrame,
        column: str = 'close',
        periods: list = [20, 50, 200]
    ) -> pd.DataFrame:
        """
        Calculate multiple EMAs and add to dataframe

        Args:
            df: DataFrame with OHLCV data
            column: Column to calculate EMA on
            periods: List of EMA periods

        Returns:
            DataFrame with EMA columns added
        """
        result = df.copy()

        for period in periods:
            col_name = f'ema_{period}'
            result[col_name] = EMA.calculate(df[column], period)

        return result

    @staticmethod
    def get_trend(
        current_price: float,
        ema_fast: float,
        ema_slow: float
    ) -> str:
        """
        Determine trend based on price and EMAs

        Args:
            current_price: Current price
            ema_fast: Fast EMA value
            ema_slow: Slow EMA value

        Returns:
            'uptrend', 'downtrend', or 'sideways'
        """
        if pd.isna(ema_fast) or pd.isna(ema_slow):
            return 'sideways'

        if current_price > ema_fast > ema_slow:
            return 'uptrend'
        elif current_price < ema_fast < ema_slow:
            return 'downtrend'
        else:
            return 'sideways'
