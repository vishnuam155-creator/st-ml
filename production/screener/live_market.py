"""
Live Market Filter
Refines candidates after market open (9:20 AM onwards)
"""

import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import datetime
import logging

from ..data_ingest import CSVDataLoader
from ..indicators import EMA, VWAP, ATR

logger = logging.getLogger(__name__)


class LiveMarketFilter:
    """
    Live market filter to refine pre-market candidates
    Uses 5-minute candles for analysis
    """

    def __init__(self, config: Dict):
        """
        Initialize live market filter

        Args:
            config: Configuration dictionary from YAML
        """
        self.config = config
        self.data_loader = CSVDataLoader(
            minute_data_dir=config['data']['csv']['minute_data_dir'],
            daily_data_dir=config['data']['csv']['daily_data_dir'],
            timezone=config['market']['timezone']
        )

    def apply_trend_filter(
        self,
        candidates: List[Dict],
        date: datetime
    ) -> List[Dict]:
        """
        Filter based on trend (200 EMA & VWAP on 5-min chart)

        Bullish: price > 200 EMA AND price > VWAP
        Bearish: price < 200 EMA AND price < VWAP

        Args:
            candidates: List of candidate stocks from pre-market
            date: Trading date

        Returns:
            List of stocks with clear trend
        """
        logger.info("Applying trend filter (5-min chart)...")

        ema_slow_period = self.config['live_market']['ema_slow']
        ema_fast_period = self.config['live_market']['ema_fast']

        trend_stocks = []

        for candidate in candidates:
            symbol = candidate['symbol']

            try:
                # Load 5-min intraday data
                data = self.data_loader.load_minute_data(
                    symbol,
                    start_date=date.replace(hour=9, minute=15),
                    end_date=date.replace(hour=15, minute=30)
                )

                if data.empty or len(data) < ema_slow_period:
                    logger.debug(f"{symbol}: Insufficient data")
                    continue

                # Calculate indicators
                data['ema_20'] = EMA.calculate(data['close'], ema_fast_period)
                data['ema_200'] = EMA.calculate(data['close'], ema_slow_period)
                data['vwap'] = VWAP.calculate(data)
                data['atr'] = ATR.calculate(data, period=14)

                # Get latest values
                latest = data.iloc[-1]
                current_price = latest['close']
                ema_20 = latest['ema_20']
                ema_200 = latest['ema_200']
                vwap = latest['vwap']
                atr = latest['atr']

                # Check for NaN
                if pd.isna(ema_200) or pd.isna(vwap):
                    continue

                # Determine trend
                if current_price > ema_200 and current_price > vwap:
                    trend = 'bullish'
                    trend_strength = ((current_price - ema_200) / ema_200) * 100
                elif current_price < ema_200 and current_price < vwap:
                    trend = 'bearish'
                    trend_strength = ((ema_200 - current_price) / ema_200) * 100
                else:
                    trend = 'mixed'
                    trend_strength = 0

                # Only accept clear trends
                if trend != 'mixed':
                    candidate['trend'] = trend
                    candidate['trend_strength'] = trend_strength
                    candidate['current_price_live'] = current_price
                    candidate['ema_20'] = ema_20
                    candidate['ema_200'] = ema_200
                    candidate['vwap'] = vwap
                    candidate['atr'] = atr
                    candidate['data'] = data  # Store for later analysis
                    trend_stocks.append(candidate)

                    logger.debug(
                        f"{symbol}: {trend}, price={current_price:.2f}, "
                        f"ema200={ema_200:.2f}, vwap={vwap:.2f}"
                    )

            except Exception as e:
                logger.error(f"Error processing {symbol} in trend filter: {e}")
                continue

        logger.info(f"Found {len(trend_stocks)} stocks with clear trend")
        return trend_stocks

    def apply_volume_range_filter(self, stocks: List[Dict]) -> List[Dict]:
        """
        Filter based on volume and range

        Checks:
        - Latest candle volume > average of last 10 candles
        - Today's range >= 0.8-1% of price

        Args:
            stocks: List of stocks with trend info

        Returns:
            List of stocks meeting volume/range criteria
        """
        logger.info("Applying volume & range filter...")

        lookback = self.config['live_market']['volume']['lookback_candles']
        min_volume_ratio = self.config['live_market']['volume']['min_ratio']
        min_range_pct = self.config['live_market']['range']['min_percent']

        filtered_stocks = []

        for stock in stocks:
            symbol = stock['symbol']
            data = stock['data']

            try:
                # Check volume surge
                if len(data) >= lookback + 1:
                    current_volume = data['volume'].iloc[-1]
                    avg_volume = data['volume'].iloc[-lookback-1:-1].mean()
                    volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
                else:
                    volume_ratio = 1.0

                # Calculate today's range
                today_high = data['high'].max()
                today_low = data['low'].min()
                current_price = stock['current_price_live']
                today_range_pct = ((today_high - today_low) / current_price) * 100

                # Apply filters
                if volume_ratio >= min_volume_ratio and today_range_pct >= min_range_pct:
                    stock['volume_ratio'] = volume_ratio
                    stock['today_range_pct'] = today_range_pct
                    stock['today_high'] = today_high
                    stock['today_low'] = today_low
                    filtered_stocks.append(stock)

                    logger.debug(
                        f"{symbol}: vol_ratio={volume_ratio:.2f}x, "
                        f"range={today_range_pct:.2f}%"
                    )

            except Exception as e:
                logger.error(f"Error processing {symbol} in volume/range filter: {e}")
                continue

        logger.info(f"Found {len(filtered_stocks)} stocks with good volume & range")
        return filtered_stocks

    def apply_location_filter(self, stocks: List[Dict]) -> List[Dict]:
        """
        Filter based on price location near key levels

        Checks proximity to:
        - Yesterday's high/low
        - Opening range (first 15-min high/low)
        - Supply/demand zones (simplified: recent swing highs/lows)

        Args:
            stocks: List of stocks

        Returns:
            List of stocks near key levels
        """
        logger.info("Applying location filter...")

        proximity_pct = self.config['live_market']['location']['proximity_percent']

        location_stocks = []

        for stock in stocks:
            symbol = stock['symbol']
            current_price = stock['current_price_live']
            data = stock['data']

            try:
                # Get opening range (first 3 candles of 5-min data = 15 min)
                if len(data) >= 3:
                    opening_range_data = data.iloc[:3]
                    opening_range_high = opening_range_data['high'].max()
                    opening_range_low = opening_range_data['low'].min()
                else:
                    opening_range_high = data['high'].max()
                    opening_range_low = data['low'].min()

                # Get yesterday's high/low from gap info (already loaded)
                # We can also load it fresh if needed
                daily_data = self.data_loader.load_daily_data(symbol, lookback_days=5)
                if len(daily_data) >= 2:
                    yesterday_high = daily_data['high'].iloc[-2]
                    yesterday_low = daily_data['low'].iloc[-2]
                else:
                    yesterday_high = current_price * 1.02
                    yesterday_low = current_price * 0.98

                # Find recent swing highs/lows (supply/demand zones)
                swing_highs = []
                swing_lows = []

                if len(data) >= 5:
                    for i in range(2, len(data) - 2):
                        # Swing high
                        if data['high'].iloc[i] > data['high'].iloc[i-1] and \
                           data['high'].iloc[i] > data['high'].iloc[i-2] and \
                           data['high'].iloc[i] > data['high'].iloc[i+1] and \
                           data['high'].iloc[i] > data['high'].iloc[i+2]:
                            swing_highs.append(data['high'].iloc[i])

                        # Swing low
                        if data['low'].iloc[i] < data['low'].iloc[i-1] and \
                           data['low'].iloc[i] < data['low'].iloc[i-2] and \
                           data['low'].iloc[i] < data['low'].iloc[i+1] and \
                           data['low'].iloc[i] < data['low'].iloc[i+2]:
                            swing_lows.append(data['low'].iloc[i])

                # Collect all key levels
                key_levels = []
                key_levels.append(('Yesterday High', yesterday_high))
                key_levels.append(('Yesterday Low', yesterday_low))
                key_levels.append(('Opening Range High', opening_range_high))
                key_levels.append(('Opening Range Low', opening_range_low))

                for swing_high in swing_highs[-3:]:  # Last 3 swing highs
                    key_levels.append(('Swing High', swing_high))

                for swing_low in swing_lows[-3:]:  # Last 3 swing lows
                    key_levels.append(('Swing Low', swing_low))

                # Check proximity to any key level
                near_level = None
                min_distance = float('inf')

                for level_name, level_price in key_levels:
                    distance_pct = abs((current_price - level_price) / current_price) * 100

                    if distance_pct <= proximity_pct and distance_pct < min_distance:
                        min_distance = distance_pct
                        near_level = (level_name, level_price, distance_pct)

                # Add location info
                stock['opening_range_high'] = opening_range_high
                stock['opening_range_low'] = opening_range_low
                stock['yesterday_high'] = yesterday_high
                stock['yesterday_low'] = yesterday_low

                if near_level:
                    stock['near_level'] = near_level[0]
                    stock['level_price'] = near_level[1]
                    stock['distance_from_level'] = near_level[2]
                else:
                    stock['near_level'] = None
                    stock['level_price'] = None
                    stock['distance_from_level'] = None

                location_stocks.append(stock)

            except Exception as e:
                logger.error(f"Error processing {symbol} in location filter: {e}")
                continue

        logger.info(f"Processed {len(location_stocks)} stocks for location")
        return location_stocks

    def run_filtering(
        self,
        candidates: List[Dict],
        date: datetime
    ) -> List[Dict]:
        """
        Run complete live market filtering workflow

        Args:
            candidates: Pre-market candidates
            date: Trading date

        Returns:
            Final 3-4 stocks for trading
        """
        logger.info(f"Running live market filtering for {date.date()}")

        if not candidates:
            logger.warning("No candidates to filter")
            return []

        # Step 1: Trend filter
        trend_stocks = self.apply_trend_filter(candidates, date)

        if not trend_stocks:
            logger.warning("No stocks with clear trend")
            return []

        # Step 2: Volume & Range filter
        volume_range_stocks = self.apply_volume_range_filter(trend_stocks)

        if not volume_range_stocks:
            logger.warning("No stocks with sufficient volume/range")
            return []

        # Step 3: Location filter
        final_stocks = self.apply_location_filter(volume_range_stocks)

        # Sort by trend strength and volume
        final_stocks.sort(
            key=lambda x: (x['trend_strength'], x['volume_ratio']),
            reverse=True
        )

        # Select top candidates
        max_final = self.config['live_market']['max_candidates']
        final_candidates = final_stocks[:max_final]

        logger.info(f"Selected {len(final_candidates)} final candidates")

        return final_candidates
