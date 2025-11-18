"""
Live Market Filter Module
Refines candidates after market open (9:20 AM onwards)
"""

import pandas as pd
import numpy as np
from typing import List, Dict

from .data_fetcher import DataFetcher
from .technical_indicators import TechnicalIndicators
from config.config import TRADING_CONFIG


class LiveMarketFilter:
    """
    Live market filter to refine pre-market candidates
    Uses trend, volume, range, and location filters
    """

    def __init__(self, config: dict = None, demo_mode: bool = False):
        self.config = config or TRADING_CONFIG
        self.data_fetcher = DataFetcher()
        self.tech_indicators = TechnicalIndicators()
        self.final_candidates = []
        self.demo_mode = demo_mode  # Use daily data fallback when True

    def apply_trend_filter(self, candidates: List[Dict]) -> List[Dict]:
        """
        Step 1: Filter based on trend (EMA 200 & VWAP)

        Bullish: Price > 200 EMA and Price > VWAP
        Bearish: Price < 200 EMA and Price < VWAP

        Args:
            candidates: List of candidate stocks from pre-market screening

        Returns:
            List of stocks with trend information
        """
        print("\n" + "="*60)
        print("STEP 1: TREND FILTER (5-min chart)")
        print("="*60)

        trend_stocks = []

        for stock_info in candidates:
            symbol = stock_info['symbol']

            try:
                # Get 5-min intraday data
                data = self.data_fetcher.get_intraday_data(symbol, interval='5m')

                # Fallback to daily data if intraday not available
                if (data.empty or len(data) < 50) and self.demo_mode:
                    print(f"  📝 {symbol}: Using daily data (intraday not available)")
                    data = self.data_fetcher.get_historical_data(symbol, period='3mo', interval='1d')

                if data.empty or len(data) < 50:
                    print(f"  ⚠️  {symbol}: Insufficient data")
                    continue

                # Add technical indicators
                data = self.tech_indicators.add_all_indicators(data, self.config)

                # Get latest values
                latest = data.iloc[-1]
                current_price = latest['Close']
                ema_200 = latest['EMA_200']
                vwap = latest['VWAP']

                # Determine trend
                if pd.isna(ema_200) or pd.isna(vwap):
                    continue

                if current_price > ema_200 and current_price > vwap:
                    trend = 'bullish'
                    trend_strength = ((current_price - ema_200) / ema_200) * 100
                elif current_price < ema_200 and current_price < vwap:
                    trend = 'bearish'
                    trend_strength = ((ema_200 - current_price) / ema_200) * 100
                else:
                    trend = 'mixed'
                    trend_strength = 0

                if trend != 'mixed':
                    stock_info['trend'] = trend
                    stock_info['trend_strength'] = trend_strength
                    stock_info['ema_200'] = ema_200
                    stock_info['vwap'] = vwap
                    stock_info['current_price_live'] = current_price
                    stock_info['data'] = data  # Store for later analysis
                    trend_stocks.append(stock_info)

            except Exception as e:
                print(f"  Error processing {symbol}: {e}")
                continue

        print(f"\nFound {len(trend_stocks)} stocks with clear trend:")
        for stock in trend_stocks:
            print(f"  {stock['symbol']:15s} | Trend: {stock['trend']:8s} | "
                  f"Price: ₹{stock['current_price_live']:.2f} | "
                  f"EMA200: ₹{stock['ema_200']:.2f} | VWAP: ₹{stock['vwap']:.2f}")

        return trend_stocks

    def apply_volume_range_filter(self, stocks: List[Dict]) -> List[Dict]:
        """
        Step 2: Filter based on volume and range

        - Volume on latest candles > average volume
        - Today's range >= 0.8-1% of price

        Args:
            stocks: List of stocks with trend info

        Returns:
            List of stocks meeting volume/range criteria
        """
        print("\n" + "="*60)
        print("STEP 2: VOLUME & RANGE FILTER")
        print("="*60)

        filtered_stocks = []

        for stock_info in stocks:
            symbol = stock_info['symbol']
            data = stock_info['data']

            try:
                # Check volume surge
                volume_surge = self.tech_indicators.calculate_volume_surge(data, lookback=10)

                # Calculate today's range
                today_high = data['High'].max()
                today_low = data['Low'].min()
                today_range_pct = ((today_high - today_low) / stock_info['current_price_live']) * 100

                # Filter criteria
                min_volume_surge = 1.0  # At least equal to average
                min_range_pct = self.config['min_range_pct']

                if volume_surge >= min_volume_surge and today_range_pct >= min_range_pct:
                    stock_info['volume_surge'] = volume_surge
                    stock_info['today_range_pct'] = today_range_pct
                    stock_info['today_high'] = today_high
                    stock_info['today_low'] = today_low
                    filtered_stocks.append(stock_info)

            except Exception as e:
                print(f"  Error processing {symbol}: {e}")
                continue

        print(f"\nFound {len(filtered_stocks)} stocks with good volume & range:")
        for stock in filtered_stocks:
            print(f"  {stock['symbol']:15s} | Vol Surge: {stock['volume_surge']:.2f}x | "
                  f"Range: {stock['today_range_pct']:.2f}% | Trend: {stock['trend']}")

        return filtered_stocks

    def apply_location_filter(self, stocks: List[Dict]) -> List[Dict]:
        """
        Step 3: Filter based on price location (near key levels)

        Price should be near:
        - Yesterday high/low
        - Today's opening range (15-min high/low)
        - Support/resistance zones

        Args:
            stocks: List of stocks

        Returns:
            List of stocks near key levels
        """
        print("\n" + "="*60)
        print("STEP 3: LOCATION FILTER (Near Key Levels)")
        print("="*60)

        location_stocks = []

        for stock_info in stocks:
            symbol = stock_info['symbol']
            current_price = stock_info['current_price_live']

            try:
                # Get support/resistance levels
                levels = self.data_fetcher.get_support_resistance_levels(symbol)

                # Get opening range (first 15 minutes)
                data = stock_info['data']
                if len(data) >= 3:  # At least 3 candles of 5-min data = 15 min
                    opening_range_high = data.iloc[:3]['High'].max()
                    opening_range_low = data.iloc[:3]['Low'].min()
                else:
                    opening_range_high = data['High'].max()
                    opening_range_low = data['Low'].min()

                # Define key levels
                key_levels = []

                # Add yesterday's high/low
                if levels.get('yesterday_high'):
                    key_levels.append(('Yesterday High', levels['yesterday_high']))
                if levels.get('yesterday_low'):
                    key_levels.append(('Yesterday Low', levels['yesterday_low']))

                # Add opening range
                key_levels.append(('Opening Range High', opening_range_high))
                key_levels.append(('Opening Range Low', opening_range_low))

                # Add support/resistance
                for r in levels.get('resistance', []):
                    key_levels.append(('Resistance', r))
                for s in levels.get('support', []):
                    key_levels.append(('Support', s))

                # Check if current price is near any key level (within 0.5%)
                near_level = None
                min_distance = float('inf')

                for level_name, level_price in key_levels:
                    distance_pct = abs((current_price - level_price) / current_price) * 100
                    if distance_pct <= 0.5 and distance_pct < min_distance:
                        min_distance = distance_pct
                        near_level = (level_name, level_price, distance_pct)

                if near_level:
                    stock_info['near_level'] = near_level[0]
                    stock_info['level_price'] = near_level[1]
                    stock_info['distance_from_level'] = near_level[2]
                    stock_info['opening_range_high'] = opening_range_high
                    stock_info['opening_range_low'] = opening_range_low
                    location_stocks.append(stock_info)
                else:
                    # Even if not near a specific level, include if it has good setup
                    stock_info['near_level'] = 'None'
                    stock_info['level_price'] = None
                    stock_info['distance_from_level'] = None
                    stock_info['opening_range_high'] = opening_range_high
                    stock_info['opening_range_low'] = opening_range_low
                    location_stocks.append(stock_info)

            except Exception as e:
                print(f"  Error processing {symbol}: {e}")
                continue

        print(f"\nStocks and their locations:")
        for stock in location_stocks:
            if stock.get('near_level') != 'None':
                print(f"  {stock['symbol']:15s} | Near: {stock['near_level']:20s} | "
                      f"Level: ₹{stock['level_price']:.2f} | Distance: {stock['distance_from_level']:.2f}%")
            else:
                print(f"  {stock['symbol']:15s} | Location: In range | "
                      f"OR High: ₹{stock['opening_range_high']:.2f} | OR Low: ₹{stock['opening_range_low']:.2f}")

        return location_stocks

    def run_filtering(self, candidates: List[Dict]) -> List[Dict]:
        """
        Run complete live market filtering

        Args:
            candidates: Pre-market candidates

        Returns:
            Final 3-4 stocks for trading
        """
        print("\n" + "📊 " + "="*58 + " 📊")
        print("        LIVE MARKET FILTER (After 9:20 AM)")
        print("📊 " + "="*58 + " 📊\n")

        if not candidates:
            print("⚠️  No candidates to filter!")
            return []

        # Step 1: Trend filter
        trend_stocks = self.apply_trend_filter(candidates)

        if not trend_stocks:
            print("\n⚠️  No stocks with clear trend. Exiting filtering.")
            return []

        # Step 2: Volume & Range filter
        volume_range_stocks = self.apply_volume_range_filter(trend_stocks)

        if not volume_range_stocks:
            print("\n⚠️  No stocks with sufficient volume/range. Exiting filtering.")
            return []

        # Step 3: Location filter
        final_stocks = self.apply_location_filter(volume_range_stocks)

        # Sort by trend strength and volume
        final_stocks.sort(key=lambda x: (x['trend_strength'], x['volume_surge']), reverse=True)

        # Select top 3-4
        max_final = self.config['live_market_candidates']
        self.final_candidates = final_stocks[:max_final]

        # Final output
        print("\n" + "="*60)
        print(f"🎯 FINAL TRADING CANDIDATES: {len(self.final_candidates)} stocks")
        print("="*60)

        for i, stock in enumerate(self.final_candidates, 1):
            print(f"\n{i}. {stock['symbol']} - {stock['trend'].upper()} SETUP")
            print(f"   Current Price: ₹{stock['current_price_live']:.2f}")
            print(f"   Trend Strength: {stock['trend_strength']:.2f}%")
            print(f"   EMA 200: ₹{stock['ema_200']:.2f} | VWAP: ₹{stock['vwap']:.2f}")
            print(f"   Volume Surge: {stock['volume_surge']:.2f}x")
            print(f"   Today's Range: {stock['today_range_pct']:.2f}%")
            print(f"   Opening Range: ₹{stock['opening_range_low']:.2f} - ₹{stock['opening_range_high']:.2f}")
            if stock.get('near_level') and stock['near_level'] != 'None':
                print(f"   Near Level: {stock['near_level']} at ₹{stock['level_price']:.2f}")

        return self.final_candidates
