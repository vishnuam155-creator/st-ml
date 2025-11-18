"""
Trading Strategy Module
Implements 20 EMA + 200 EMA + VWAP trend-following strategy
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple

from .data_fetcher import DataFetcher
from .technical_indicators import TechnicalIndicators
from config.config import TRADING_CONFIG


class TradingStrategy:
    """
    Implements the main trading strategy:
    - 20 EMA + 200 EMA + VWAP Trend Method
    - BUY: Price > 200 EMA, > VWAP, pullback to 20 EMA, bullish reversal
    - SELL: Price < 200 EMA, < VWAP, pullback to 20 EMA, bearish reversal
    """

    def __init__(self, config: dict = None):
        self.config = config or TRADING_CONFIG
        self.data_fetcher = DataFetcher()
        self.tech_indicators = TechnicalIndicators()

    def detect_buy_setup(self, data: pd.DataFrame) -> Optional[Dict]:
        """
        Detect BUY setup:
        1. Price above 200 EMA (uptrend)
        2. Price above VWAP (strong intraday bias)
        3. Pullback to 20 EMA
        4. Bullish reversal candle with higher volume

        Args:
            data: DataFrame with OHLCV and indicators

        Returns:
            Dictionary with setup details if found, None otherwise
        """
        if len(data) < 5:
            return None

        # Get latest candles
        latest = data.iloc[-1]
        previous = data.iloc[-2]

        current_price = latest['Close']
        ema_20 = latest['EMA_20']
        ema_200 = latest['EMA_200']
        vwap = latest['VWAP']

        # Check if any indicator is missing
        if pd.isna(ema_20) or pd.isna(ema_200) or pd.isna(vwap):
            return None

        # Condition 1: Price above 200 EMA (uptrend)
        if current_price < ema_200:
            return None

        # Condition 2: Price above VWAP (bullish intraday)
        if current_price < vwap:
            return None

        # Condition 3: Pullback to 20 EMA (price near 20 EMA)
        # Price should be within 0.5% of 20 EMA
        distance_from_ema20 = abs((current_price - ema_20) / current_price) * 100

        if distance_from_ema20 > 0.5:
            # Not near 20 EMA, but check if it bounced recently
            # Check last 3 candles for a touch to 20 EMA
            touched_ema = False
            for i in range(-3, 0):
                if i >= -len(data):
                    candle = data.iloc[i]
                    if candle['Low'] <= candle['EMA_20'] <= candle['High']:
                        touched_ema = True
                        break

            if not touched_ema:
                return None

        # Condition 4: Bullish reversal candle
        reversal = self.tech_indicators.detect_reversal_candle(data, index=-1)

        if reversal['type'] != 'bullish':
            return None

        # Condition 5: Higher volume
        volume_surge = self.tech_indicators.calculate_volume_surge(data, lookback=10)

        if volume_surge < 1.0:  # At least equal to average volume
            return None

        # Calculate ATR for stop-loss
        atr = latest['ATR']

        # All conditions met - BUY setup detected
        return {
            'type': 'BUY',
            'price': current_price,
            'ema_20': ema_20,
            'ema_200': ema_200,
            'vwap': vwap,
            'atr': atr,
            'volume_surge': volume_surge,
            'reversal_pattern': reversal['pattern'],
            'reversal_strength': reversal['strength'],
            'setup_quality': self._calculate_setup_quality('BUY', data),
        }

    def detect_sell_setup(self, data: pd.DataFrame) -> Optional[Dict]:
        """
        Detect SELL setup:
        1. Price below 200 EMA (downtrend)
        2. Price below VWAP (weak intraday)
        3. Pullback to 20 EMA
        4. Bearish reversal candle with higher volume

        Args:
            data: DataFrame with OHLCV and indicators

        Returns:
            Dictionary with setup details if found, None otherwise
        """
        if len(data) < 5:
            return None

        # Get latest candles
        latest = data.iloc[-1]
        previous = data.iloc[-2]

        current_price = latest['Close']
        ema_20 = latest['EMA_20']
        ema_200 = latest['EMA_200']
        vwap = latest['VWAP']

        # Check if any indicator is missing
        if pd.isna(ema_20) or pd.isna(ema_200) or pd.isna(vwap):
            return None

        # Condition 1: Price below 200 EMA (downtrend)
        if current_price > ema_200:
            return None

        # Condition 2: Price below VWAP (bearish intraday)
        if current_price > vwap:
            return None

        # Condition 3: Pullback to 20 EMA (price near 20 EMA)
        distance_from_ema20 = abs((current_price - ema_20) / current_price) * 100

        if distance_from_ema20 > 0.5:
            # Check if it touched 20 EMA in last 3 candles
            touched_ema = False
            for i in range(-3, 0):
                if i >= -len(data):
                    candle = data.iloc[i]
                    if candle['Low'] <= candle['EMA_20'] <= candle['High']:
                        touched_ema = True
                        break

            if not touched_ema:
                return None

        # Condition 4: Bearish reversal candle
        reversal = self.tech_indicators.detect_reversal_candle(data, index=-1)

        if reversal['type'] != 'bearish':
            return None

        # Condition 5: Higher volume
        volume_surge = self.tech_indicators.calculate_volume_surge(data, lookback=10)

        if volume_surge < 1.0:
            return None

        # Calculate ATR for stop-loss
        atr = latest['ATR']

        # All conditions met - SELL setup detected
        return {
            'type': 'SELL',
            'price': current_price,
            'ema_20': ema_20,
            'ema_200': ema_200,
            'vwap': vwap,
            'atr': atr,
            'volume_surge': volume_surge,
            'reversal_pattern': reversal['pattern'],
            'reversal_strength': reversal['strength'],
            'setup_quality': self._calculate_setup_quality('SELL', data),
        }

    def _calculate_setup_quality(self, setup_type: str, data: pd.DataFrame) -> float:
        """
        Calculate setup quality score (0-100)

        Factors:
        - Distance from 200 EMA (closer = better trend)
        - Volume surge (higher = better)
        - Reversal strength
        - Trend consistency (HH/HL or LH/LL)

        Args:
            setup_type: 'BUY' or 'SELL'
            data: DataFrame with indicators

        Returns:
            Quality score (0-100)
        """
        score = 0
        latest = data.iloc[-1]

        # Factor 1: Trend strength (30 points)
        current_price = latest['Close']
        ema_200 = latest['EMA_200']
        distance_from_200 = abs((current_price - ema_200) / ema_200) * 100

        if distance_from_200 > 2:  # Strong trend
            score += 30
        elif distance_from_200 > 1:  # Moderate trend
            score += 20
        else:  # Weak trend
            score += 10

        # Factor 2: Volume surge (25 points)
        volume_surge = self.tech_indicators.calculate_volume_surge(data, lookback=10)

        if volume_surge > 2:  # Very high volume
            score += 25
        elif volume_surge > 1.5:
            score += 20
        elif volume_surge > 1.2:
            score += 15
        elif volume_surge > 1.0:
            score += 10

        # Factor 3: Reversal pattern strength (25 points)
        reversal = self.tech_indicators.detect_reversal_candle(data, index=-1)
        score += reversal['strength'] * 25

        # Factor 4: Trend consistency (20 points)
        if setup_type == 'BUY':
            if self.tech_indicators.is_higher_high_higher_low(data, periods=3):
                score += 20
            elif self.tech_indicators.is_higher_high_higher_low(data, periods=2):
                score += 15
        else:  # SELL
            if self.tech_indicators.is_lower_high_lower_low(data, periods=3):
                score += 20
            elif self.tech_indicators.is_lower_high_lower_low(data, periods=2):
                score += 15

        return min(score, 100)

    def calculate_position_size(
        self,
        capital: float,
        entry_price: float,
        stop_loss: float,
        risk_pct: float = None
    ) -> Tuple[int, float]:
        """
        Calculate position size based on risk management

        Args:
            capital: Total trading capital
            entry_price: Entry price for the trade
            stop_loss: Stop-loss price
            risk_pct: Risk percentage (default from config)

        Returns:
            Tuple of (quantity, risk_amount)
        """
        if risk_pct is None:
            risk_pct = self.config['risk_per_trade_pct']

        risk_amount = capital * (risk_pct / 100)
        risk_per_share = abs(entry_price - stop_loss)

        if risk_per_share == 0:
            return 0, 0

        quantity = int(risk_amount / risk_per_share)

        return quantity, risk_amount

    def calculate_stop_loss(
        self,
        setup: Dict,
        data: pd.DataFrame,
        method: str = 'atr'
    ) -> float:
        """
        Calculate stop-loss price

        Args:
            setup: Setup dictionary from detect_buy/sell_setup
            data: DataFrame with price data
            method: 'atr' or 'swing' (swing low/high)

        Returns:
            Stop-loss price
        """
        setup_type = setup['type']
        current_price = setup['price']
        atr = setup['atr']

        if method == 'atr':
            # ATR-based stop-loss
            multiplier = self.config['stop_loss_atr_multiplier']

            if setup_type == 'BUY':
                stop_loss = current_price - (atr * multiplier)
            else:  # SELL
                stop_loss = current_price + (atr * multiplier)

        elif method == 'swing':
            # Swing low/high based stop-loss
            if setup_type == 'BUY':
                # Find recent swing low (last 5-10 candles)
                recent_data = data.iloc[-10:]
                swing_low = recent_data['Low'].min()
                stop_loss = swing_low * 0.995  # 0.5% below swing low

            else:  # SELL
                # Find recent swing high
                recent_data = data.iloc[-10:]
                swing_high = recent_data['High'].max()
                stop_loss = swing_high * 1.005  # 0.5% above swing high

        return round(stop_loss, 2)

    def calculate_target(
        self,
        setup: Dict,
        stop_loss: float,
        reward_ratio: float = 2.0
    ) -> float:
        """
        Calculate target price based on risk-reward ratio

        Args:
            setup: Setup dictionary
            stop_loss: Stop-loss price
            reward_ratio: Reward-to-risk ratio (default 2:1)

        Returns:
            Target price
        """
        setup_type = setup['type']
        entry_price = setup['price']

        risk = abs(entry_price - stop_loss)
        reward = risk * reward_ratio

        if setup_type == 'BUY':
            target = entry_price + reward
        else:  # SELL
            target = entry_price - reward

        return round(target, 2)

    def analyze_stock_for_trading(self, symbol: str, stock_info: Dict = None) -> Optional[Dict]:
        """
        Analyze a stock and detect trading setups

        Args:
            symbol: Stock symbol
            stock_info: Optional stock info from screener

        Returns:
            Complete trading plan or None
        """
        try:
            # Get intraday data
            data = self.data_fetcher.get_intraday_data(symbol, interval='5m')

            if data.empty or len(data) < 50:
                return None

            # Add indicators
            data = self.tech_indicators.add_all_indicators(data, self.config)

            # Detect setups
            buy_setup = self.detect_buy_setup(data)
            sell_setup = self.detect_sell_setup(data)

            setup = buy_setup or sell_setup

            if not setup:
                return None

            # Calculate stop-loss and target
            stop_loss = self.calculate_stop_loss(setup, data, method='atr')
            target = self.calculate_target(setup, stop_loss, reward_ratio=2.0)

            # Create trading plan
            trading_plan = {
                'symbol': symbol,
                'setup_type': setup['type'],
                'entry_price': setup['price'],
                'stop_loss': stop_loss,
                'target': target,
                'risk_reward_ratio': 2.0,
                'setup_quality': setup['setup_quality'],
                'atr': setup['atr'],
                'volume_surge': setup['volume_surge'],
                'reversal_pattern': setup['reversal_pattern'],
                'technical_levels': {
                    'ema_20': setup['ema_20'],
                    'ema_200': setup['ema_200'],
                    'vwap': setup['vwap'],
                }
            }

            # Add stock info if available
            if stock_info:
                trading_plan['gap_pct'] = stock_info.get('gap_pct', 0)
                trading_plan['aligned_with_index'] = stock_info.get('aligned_with_index', False)

            return trading_plan

        except Exception as e:
            print(f"Error analyzing {symbol}: {e}")
            return None

    def scan_for_setups(self, candidates: List[Dict]) -> List[Dict]:
        """
        Scan all candidates for trading setups

        Args:
            candidates: List of candidate stocks

        Returns:
            List of trading plans
        """
        print("\n" + "🎯 " + "="*58 + " 🎯")
        print("        SCANNING FOR TRADING SETUPS")
        print("🎯 " + "="*58 + " 🎯\n")

        trading_plans = []

        for stock_info in candidates:
            symbol = stock_info['symbol']
            print(f"Analyzing {symbol}...", end=" ")

            plan = self.analyze_stock_for_trading(symbol, stock_info)

            if plan:
                print(f"✓ {plan['setup_type']} setup found (Quality: {plan['setup_quality']:.0f}/100)")
                trading_plans.append(plan)
            else:
                print("✗ No setup")

        # Sort by setup quality
        trading_plans.sort(key=lambda x: x['setup_quality'], reverse=True)

        return trading_plans
