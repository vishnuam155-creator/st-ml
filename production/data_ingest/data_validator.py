"""
Data Validator
Validates OHLCV data integrity and quality
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


class DataValidator:
    """Validates OHLCV data for integrity and quality"""

    @staticmethod
    def validate_ohlcv(df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Validate OHLCV data integrity

        Checks:
        - Required columns present
        - No missing values in critical columns
        - High >= Low
        - High >= Open, Close
        - Low <= Open, Close
        - Volume >= 0

        Args:
            df: DataFrame with OHLCV data

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []

        # Check required columns
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        missing_cols = [col for col in required_cols if col not in df.columns]

        if missing_cols:
            errors.append(f"Missing columns: {missing_cols}")
            return False, errors

        # Check for missing values
        for col in required_cols:
            if df[col].isna().any():
                na_count = df[col].isna().sum()
                errors.append(f"Column '{col}' has {na_count} missing values")

        # Check OHLC relationships
        invalid_hl = df[df['high'] < df['low']]
        if len(invalid_hl) > 0:
            errors.append(f"{len(invalid_hl)} candles where High < Low")

        invalid_ho = df[df['high'] < df['open']]
        if len(invalid_ho) > 0:
            errors.append(f"{len(invalid_ho)} candles where High < Open")

        invalid_hc = df[df['high'] < df['close']]
        if len(invalid_hc) > 0:
            errors.append(f"{len(invalid_hc)} candles where High < Close")

        invalid_lo = df[df['low'] > df['open']]
        if len(invalid_lo) > 0:
            errors.append(f"{len(invalid_lo)} candles where Low > Open")

        invalid_lc = df[df['low'] > df['close']]
        if len(invalid_lc) > 0:
            errors.append(f"{len(invalid_lc)} candles where Low > Close")

        # Check volume
        invalid_vol = df[df['volume'] < 0]
        if len(invalid_vol) > 0:
            errors.append(f"{len(invalid_vol)} candles with negative volume")

        is_valid = len(errors) == 0
        return is_valid, errors

    @staticmethod
    def check_data_gaps(df: pd.DataFrame, expected_interval_minutes: int = 5) -> List[Dict]:
        """
        Check for gaps in time series data

        Args:
            df: DataFrame with datetime index
            expected_interval_minutes: Expected minutes between candles

        Returns:
            List of gaps found
        """
        if len(df) < 2:
            return []

        gaps = []
        expected_delta = pd.Timedelta(minutes=expected_interval_minutes)

        for i in range(1, len(df)):
            actual_delta = df.index[i] - df.index[i-1]

            if actual_delta > expected_delta * 1.5:  # Allow 50% tolerance
                gaps.append({
                    'start': df.index[i-1],
                    'end': df.index[i],
                    'duration': actual_delta,
                    'expected': expected_delta
                })

        if gaps:
            logger.warning(f"Found {len(gaps)} time gaps in data")

        return gaps

    @staticmethod
    def check_outliers(df: pd.DataFrame, column: str = 'close', std_threshold: float = 5.0) -> pd.DataFrame:
        """
        Detect outliers in price data

        Args:
            df: DataFrame with price data
            column: Column to check
            std_threshold: Number of standard deviations for outlier detection

        Returns:
            DataFrame with outliers
        """
        if column not in df.columns:
            return pd.DataFrame()

        returns = df[column].pct_change()
        mean_return = returns.mean()
        std_return = returns.std()

        outliers = df[np.abs(returns - mean_return) > std_threshold * std_return]

        if len(outliers) > 0:
            logger.warning(f"Found {len(outliers)} outliers in {column}")

        return outliers

    @staticmethod
    def summarize_data(df: pd.DataFrame) -> Dict:
        """
        Generate summary statistics for OHLCV data

        Args:
            df: DataFrame with OHLCV data

        Returns:
            Dictionary with summary statistics
        """
        if df.empty:
            return {}

        summary = {
            'total_candles': len(df),
            'date_range': {
                'start': df.index[0],
                'end': df.index[-1]
            },
            'price_range': {
                'min': df['low'].min(),
                'max': df['high'].max(),
                'mean': df['close'].mean()
            },
            'volume': {
                'total': df['volume'].sum(),
                'mean': df['volume'].mean(),
                'max': df['volume'].max()
            },
            'missing_values': df.isna().sum().to_dict()
        }

        return summary
