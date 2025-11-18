"""
Signal Generator
Generates BUY/SELL signals based on 20/200 EMA + VWAP method
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging

from ..indicators import EMA, VWAP, ATR

logger = logging.getLogger(__name__)


class SignalGenerator:
    """
    Generate trading signals based on configured rules

    BUY Signal:
    - Price > 200 EMA AND > VWAP
    - Pullback to 20 EMA (within 0.5%)
    - Bullish reversal candle
    - Higher volume

    SELL Signal:
    - Price < 200 EMA AND < VWAP
    - Pullback to 20 EMA
    - Bearish reversal candle
    - Higher volume
    """

    def __init__(self, config: Dict):
        """
        Initialize signal generator

        Args:
            config: Configuration dictionary
        """
        self.config = config

    def detect_reversal_candle(
        self,
        data: pd.DataFrame,
        index: int = -1,
        signal_type: str = 'buy'
    ) -> Dict:
        """
        Detect bullish or bearish reversal candle patterns

        Patterns:
        - Hammer: Long lower wick, small body, small upper wick
        - Engulfing: Current candle engulfs previous
        - Shooting Star: Long upper wick, small body
        - Bullish/Bearish candle: Strong directional candle

        Args:
            data: DataFrame with OHLCV data
            index: Index of candle to check (default -1 for latest)
            signal_type: 'buy' or 'sell'

        Returns:
            Dictionary with pattern information
        """
        if len(data) < abs(index) + 2:
            return {'type': 'none', 'strength': 0, 'pattern': 'none'}

        current = data.iloc[index]
        previous = data.iloc[index - 1]

        open_price = current['open']
        close_price = current['close']
        high_price = current['high']
        low_price = current['low']

        body = abs(close_price - open_price)
        upper_wick = high_price - max(open_price, close_price)
        lower_wick = min(open_price, close_price) - low_price
        total_range = high_price - low_price

        if total_range == 0:
            return {'type': 'none', 'strength': 0, 'pattern': 'none'}

        result = {'type': 'none', 'strength': 0, 'pattern': 'none'}

        if signal_type == 'buy':
            # Bullish Hammer
            if lower_wick > 2 * body and upper_wick < body * 0.5 and close_price > open_price:
                result = {'type': 'bullish', 'strength': 0.8, 'pattern': 'hammer'}

            # Bullish Engulfing
            elif close_price > open_price and previous['close'] < previous['open'] and \
                 close_price > previous['open'] and open_price < previous['close']:
                result = {'type': 'bullish', 'strength': 0.9, 'pattern': 'engulfing'}

            # Bullish candle
            elif close_price > open_price and body > total_range * 0.6:
                result = {'type': 'bullish', 'strength': 0.6, 'pattern': 'bullish_candle'}

        else:  # sell
            # Bearish Shooting Star
            if upper_wick > 2 * body and lower_wick < body * 0.5 and close_price < open_price:
                result = {'type': 'bearish', 'strength': 0.8, 'pattern': 'shooting_star'}

            # Bearish Engulfing
            elif close_price < open_price and previous['close'] > previous['open'] and \
                 close_price < previous['open'] and open_price > previous['close']:
                result = {'type': 'bearish', 'strength': 0.9, 'pattern': 'engulfing'}

            # Bearish candle
            elif close_price < open_price and body > total_range * 0.6:
                result = {'type': 'bearish', 'strength': 0.6, 'pattern': 'bearish_candle'}

        return result

    def detect_buy_signal(self, data: pd.DataFrame) -> Optional[Dict]:
        """
        Detect BUY signal

        Conditions:
        1. Price > 200 EMA (uptrend)
        2. Price > VWAP (bullish intraday)
        3. Pullback to 20 EMA (within 0.5%)
        4. Bullish reversal candle
        5. Higher volume

        Args:
            data: DataFrame with OHLCV and indicators

        Returns:
            Signal dictionary or None
        """
        if len(data) < 5:
            return None

        # Ensure indicators are present
        required_cols = ['ema_20', 'ema_200', 'vwap', 'atr']
        if not all(col in data.columns for col in required_cols):
            return None

        latest = data.iloc[-1]
        current_price = latest['close']
        ema_20 = latest['ema_20']
        ema_200 = latest['ema_200']
        vwap = latest['vwap']
        atr = latest['atr']

        # Check for NaN
        if pd.isna(ema_20) or pd.isna(ema_200) or pd.isna(vwap):
            return None

        # Condition 1: Price > 200 EMA
        if current_price <= ema_200:
            return None

        # Condition 2: Price > VWAP
        if current_price <= vwap:
            return None

        # Condition 3: Pullback to 20 EMA
        pullback_pct = self.config['signals']['buy']['pullback_to_20ema_percent']
        distance_from_ema20 = abs((current_price - ema_20) / current_price) * 100

        if distance_from_ema20 > pullback_pct:
            # Check if touched in last 3 candles
            touched_ema = False
            for i in range(-3, 0):
                if i >= -len(data):
                    candle = data.iloc[i]
                    if candle['low'] <= candle['ema_20'] <= candle['high']:
                        touched_ema = True
                        break

            if not touched_ema:
                return None

        # Condition 4: Bullish reversal candle
        reversal = self.detect_reversal_candle(data, index=-1, signal_type='buy')

        if reversal['type'] != 'bullish':
            return None

        # Condition 5: Higher volume
        min_volume_ratio = self.config['signals']['buy']['min_volume_ratio']

        if len(data) >= 11:
            current_volume = data['volume'].iloc[-1]
            avg_volume = data['volume'].iloc[-11:-1].mean()
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
        else:
            volume_ratio = 1.0

        if volume_ratio < min_volume_ratio:
            return None

        # All conditions met - generate BUY signal
        stop_loss = ATR.calculate_stop_loss(current_price, atr, multiplier=1.5, direction='long')
        risk = current_price - stop_loss
        target = current_price + (risk * self.config['risk']['target']['risk_reward_ratio'])

        signal = {
            'type': 'BUY',
            'entry': current_price,
            'stop_loss': stop_loss,
            'target': round(target, 2),
            'atr': atr,
            'volume_ratio': volume_ratio,
            'reversal_pattern': reversal['pattern'],
            'reversal_strength': reversal['strength'],
            'indicators': {
                'ema_20': ema_20,
                'ema_200': ema_200,
                'vwap': vwap
            }
        }

        return signal

    def detect_sell_signal(self, data: pd.DataFrame) -> Optional[Dict]:
        """
        Detect SELL signal

        Conditions:
        1. Price < 200 EMA (downtrend)
        2. Price < VWAP (bearish intraday)
        3. Pullback to 20 EMA
        4. Bearish reversal candle
        5. Higher volume

        Args:
            data: DataFrame with OHLCV and indicators

        Returns:
            Signal dictionary or None
        """
        if len(data) < 5:
            return None

        # Ensure indicators are present
        required_cols = ['ema_20', 'ema_200', 'vwap', 'atr']
        if not all(col in data.columns for col in required_cols):
            return None

        latest = data.iloc[-1]
        current_price = latest['close']
        ema_20 = latest['ema_20']
        ema_200 = latest['ema_200']
        vwap = latest['vwap']
        atr = latest['atr']

        # Check for NaN
        if pd.isna(ema_20) or pd.isna(ema_200) or pd.isna(vwap):
            return None

        # Condition 1: Price < 200 EMA
        if current_price >= ema_200:
            return None

        # Condition 2: Price < VWAP
        if current_price >= vwap:
            return None

        # Condition 3: Pullback to 20 EMA
        pullback_pct = self.config['signals']['sell']['pullback_to_20ema_percent']
        distance_from_ema20 = abs((current_price - ema_20) / current_price) * 100

        if distance_from_ema20 > pullback_pct:
            # Check if touched in last 3 candles
            touched_ema = False
            for i in range(-3, 0):
                if i >= -len(data):
                    candle = data.iloc[i]
                    if candle['low'] <= candle['ema_20'] <= candle['high']:
                        touched_ema = True
                        break

            if not touched_ema:
                return None

        # Condition 4: Bearish reversal candle
        reversal = self.detect_reversal_candle(data, index=-1, signal_type='sell')

        if reversal['type'] != 'bearish':
            return None

        # Condition 5: Higher volume
        min_volume_ratio = self.config['signals']['sell']['min_volume_ratio']

        if len(data) >= 11:
            current_volume = data['volume'].iloc[-1]
            avg_volume = data['volume'].iloc[-11:-1].mean()
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
        else:
            volume_ratio = 1.0

        if volume_ratio < min_volume_ratio:
            return None

        # All conditions met - generate SELL signal
        stop_loss = ATR.calculate_stop_loss(current_price, atr, multiplier=1.5, direction='short')
        risk = stop_loss - current_price
        target = current_price - (risk * self.config['risk']['target']['risk_reward_ratio'])

        signal = {
            'type': 'SELL',
            'entry': current_price,
            'stop_loss': stop_loss,
            'target': round(target, 2),
            'atr': atr,
            'volume_ratio': volume_ratio,
            'reversal_pattern': reversal['pattern'],
            'reversal_strength': reversal['strength'],
            'indicators': {
                'ema_20': ema_20,
                'ema_200': ema_200,
                'vwap': vwap
            }
        }

        return signal

    def score_signal(self, signal: Dict, data: pd.DataFrame) -> float:
        """
        Score signal quality (0-100)

        Factors:
        - Trend strength (30 points)
        - Volume surge (25 points)
        - Reversal pattern strength (25 points)
        - Distance from support/resistance (20 points)

        Args:
            signal: Signal dictionary
            data: DataFrame with price data

        Returns:
            Quality score (0-100)
        """
        score = 0

        # Trend strength (30 points)
        current_price = signal['entry']
        ema_200 = signal['indicators']['ema_200']
        distance_from_200 = abs((current_price - ema_200) / ema_200) * 100

        if distance_from_200 > 2:
            score += 30
        elif distance_from_200 > 1:
            score += 20
        else:
            score += 10

        # Volume surge (25 points)
        volume_ratio = signal['volume_ratio']

        if volume_ratio > 2:
            score += 25
        elif volume_ratio > 1.5:
            score += 20
        elif volume_ratio > 1.2:
            score += 15
        else:
            score += 10

        # Reversal pattern strength (25 points)
        score += signal['reversal_strength'] * 25

        # Risk-reward (20 points)
        risk = abs(signal['entry'] - signal['stop_loss'])
        reward = abs(signal['target'] - signal['entry'])
        rr_ratio = reward / risk if risk > 0 else 0

        if rr_ratio >= 2:
            score += 20
        elif rr_ratio >= 1.5:
            score += 15
        else:
            score += 10

        return min(score, 100)

    def generate_signals(self, candidates: List[Dict]) -> List[Dict]:
        """
        Generate signals for all candidates

        Args:
            candidates: List of filtered candidate stocks

        Returns:
            List of signals with scores
        """
        logger.info("Generating trading signals...")

        signals = []

        for candidate in candidates:
            symbol = candidate['symbol']
            data = candidate.get('data')

            if data is None or data.empty:
                continue

            try:
                # Try BUY signal
                if candidate.get('trend') == 'bullish':
                    signal = self.detect_buy_signal(data)

                    if signal:
                        signal['symbol'] = symbol
                        signal['score'] = self.score_signal(signal, data)
                        signals.append(signal)
                        logger.info(f"{symbol}: BUY signal (score={signal['score']:.0f})")

                # Try SELL signal
                elif candidate.get('trend') == 'bearish':
                    signal = self.detect_sell_signal(data)

                    if signal:
                        signal['symbol'] = symbol
                        signal['score'] = self.score_signal(signal, data)
                        signals.append(signal)
                        logger.info(f"{symbol}: SELL signal (score={signal['score']:.0f})")

            except Exception as e:
                logger.error(f"Error generating signal for {symbol}: {e}")
                continue

        # Sort by score
        signals.sort(key=lambda x: x['score'], reverse=True)

        logger.info(f"Generated {len(signals)} signals")
        return signals
