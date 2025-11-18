"""
Volume Weighted Average Price (VWAP) Indicator
"""

import pandas as pd
import numpy as np


class VWAP:
    """VWAP calculator for intraday analysis"""

    @staticmethod
    def calculate(df: pd.DataFrame) -> pd.Series:
        """
        Calculate intraday VWAP

        VWAP = Cumulative(Typical Price * Volume) / Cumulative(Volume)
        Typical Price = (High + Low + Close) / 3

        Args:
            df: DataFrame with OHLCV data (must have datetime index)

        Returns:
            Series with VWAP values
        """
        if len(df) == 0:
            return pd.Series(dtype=float)

        # Calculate typical price
        typical_price = (df['high'] + df['low'] + df['close']) / 3

        # Calculate VWAP
        cumulative_tp_volume = (typical_price * df['volume']).cumsum()
        cumulative_volume = df['volume'].cumsum()

        # Avoid division by zero
        vwap = cumulative_tp_volume / cumulative_volume.replace(0, np.nan)

        return vwap

    @staticmethod
    def calculate_daily_reset(df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate VWAP with daily reset (for multi-day data)

        Args:
            df: DataFrame with OHLCV data and datetime index

        Returns:
            DataFrame with VWAP column added
        """
        result = df.copy()

        # Group by date and calculate VWAP for each day
        result['date'] = result.index.date
        result['vwap'] = result.groupby('date', group_keys=False).apply(
            lambda x: VWAP.calculate(x)
        )

        result = result.drop('date', axis=1)
        return result

    @staticmethod
    def is_above_vwap(price: float, vwap: float) -> bool:
        """
        Check if price is above VWAP

        Args:
            price: Current price
            vwap: VWAP value

        Returns:
            True if price > VWAP
        """
        if pd.isna(vwap):
            return False
        return price > vwap

    @staticmethod
    def distance_from_vwap(price: float, vwap: float) -> float:
        """
        Calculate percentage distance from VWAP

        Args:
            price: Current price
            vwap: VWAP value

        Returns:
            Percentage distance (positive if above, negative if below)
        """
        if pd.isna(vwap) or vwap == 0:
            return 0.0

        return ((price - vwap) / vwap) * 100
