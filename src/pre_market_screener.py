"""
Pre-Market Screener Module
Screens stocks before market open (8:45 - 9:15 AM)
"""

import pandas as pd
import numpy as np
from typing import List, Dict
from datetime import datetime, timedelta

from .data_fetcher import DataFetcher
from config.config import TRADING_CONFIG, NIFTY_50_STOCKS, INDICES


class PreMarketScreener:
    """
    Pre-market stock screener
    Filters stocks based on gaps, liquidity, and news
    """

    def __init__(self, config: dict = None):
        self.config = config or TRADING_CONFIG
        self.data_fetcher = DataFetcher()
        self.candidates = []

    def get_index_context(self) -> Dict:
        """
        Step 1: Get index context (Nifty & BankNifty trend)

        Returns:
            Dictionary with index trends and levels
        """
        print("\n" + "="*60)
        print("STEP 1: INDEX CONTEXT")
        print("="*60)

        context = {}

        # Get Nifty trend
        nifty_trend = self.data_fetcher.get_index_trend(INDICES['nifty'])
        nifty_levels = self.data_fetcher.get_support_resistance_levels(INDICES['nifty'])

        print(f"\nNIFTY 50:")
        print(f"  Trend: {nifty_trend.get('trend', 'unknown').upper()}")
        print(f"  Current Price: {nifty_trend.get('current_price', 0):.2f}")
        print(f"  Change: {nifty_trend.get('change_pct', 0):.2f}%")
        print(f"  Yesterday High: {nifty_levels.get('yesterday_high', 0):.2f}")
        print(f"  Yesterday Low: {nifty_levels.get('yesterday_low', 0):.2f}")
        if nifty_levels.get('resistance'):
            print(f"  Resistance Levels: {', '.join([f'{r:.2f}' for r in nifty_levels['resistance']])}")
        if nifty_levels.get('support'):
            print(f"  Support Levels: {', '.join([f'{s:.2f}' for s in nifty_levels['support']])}")

        context['nifty'] = {**nifty_trend, **nifty_levels}

        # Get BankNifty trend
        banknifty_trend = self.data_fetcher.get_index_trend(INDICES['banknifty'])
        banknifty_levels = self.data_fetcher.get_support_resistance_levels(INDICES['banknifty'])

        print(f"\nBANK NIFTY:")
        print(f"  Trend: {banknifty_trend.get('trend', 'unknown').upper()}")
        print(f"  Current Price: {banknifty_trend.get('current_price', 0):.2f}")
        print(f"  Change: {banknifty_trend.get('change_pct', 0):.2f}%")
        print(f"  Yesterday High: {banknifty_levels.get('yesterday_high', 0):.2f}")
        print(f"  Yesterday Low: {banknifty_levels.get('yesterday_low', 0):.2f}")
        if banknifty_levels.get('resistance'):
            print(f"  Resistance Levels: {', '.join([f'{r:.2f}' for r in banknifty_levels['resistance']])}")
        if banknifty_levels.get('support'):
            print(f"  Support Levels: {', '.join([f'{s:.2f}' for s in banknifty_levels['support']])}")

        context['banknifty'] = {**banknifty_trend, **banknifty_levels}

        return context

    def apply_gap_filter(self, stocks: List[str], index_trend: str) -> List[Dict]:
        """
        Step 2: Filter stocks with gaps between 0.3% and 2%

        Args:
            stocks: List of stock symbols
            index_trend: Current Nifty trend ('uptrend', 'downtrend', 'sideways')

        Returns:
            List of stocks with gap information
        """
        print("\n" + "="*60)
        print("STEP 2: GAP FILTER (0.3% - 2.0%)")
        print("="*60)

        gap_stocks = []

        for symbol in stocks:
            try:
                # Get current price and previous close
                current_price = self.data_fetcher.get_current_price(symbol)
                prev_close = self.data_fetcher.get_previous_close(symbol)

                if current_price is None or prev_close is None:
                    continue

                # Calculate gap percentage
                gap_pct = ((current_price - prev_close) / prev_close) * 100

                # Filter based on gap range
                if self.config['gap_min_pct'] <= abs(gap_pct) <= self.config['gap_max_pct']:
                    gap_direction = 'up' if gap_pct > 0 else 'down'

                    # Prefer gaps in same direction as Nifty
                    aligned_with_index = False
                    if (index_trend == 'uptrend' and gap_direction == 'up') or \
                       (index_trend == 'downtrend' and gap_direction == 'down'):
                        aligned_with_index = True

                    stock_info = {
                        'symbol': symbol,
                        'current_price': current_price,
                        'prev_close': prev_close,
                        'gap_pct': gap_pct,
                        'gap_direction': gap_direction,
                        'aligned_with_index': aligned_with_index,
                    }

                    gap_stocks.append(stock_info)

            except Exception as e:
                print(f"  Error processing {symbol}: {e}")
                continue

        # Sort by alignment with index and gap percentage
        gap_stocks.sort(key=lambda x: (x['aligned_with_index'], abs(x['gap_pct'])), reverse=True)

        print(f"\nFound {len(gap_stocks)} stocks with gaps:")
        for stock in gap_stocks[:10]:  # Show top 10
            alignment = "✓" if stock['aligned_with_index'] else "✗"
            print(f"  {alignment} {stock['symbol']:15s} | Gap: {stock['gap_pct']:+6.2f}% | "
                  f"Direction: {stock['gap_direction']:5s} | Price: ₹{stock['current_price']:.2f}")

        return gap_stocks

    def apply_liquidity_filter(self, stocks: List[Dict]) -> List[Dict]:
        """
        Step 3: Filter stocks with high liquidity

        Args:
            stocks: List of stock dictionaries from gap filter

        Returns:
            List of liquid stocks
        """
        print("\n" + "="*60)
        print("STEP 3: LIQUIDITY FILTER")
        print("="*60)

        liquid_stocks = []

        for stock_info in stocks:
            symbol = stock_info['symbol']

            try:
                # Get average volume
                avg_volume = self.data_fetcher.get_average_volume(
                    symbol,
                    self.config['volume_lookback_days']
                )

                if avg_volume is None or avg_volume < 100000:  # Skip very low volume stocks
                    continue

                # Get today's volume (if available)
                intraday_data = self.data_fetcher.get_intraday_data(symbol, interval='5m')

                if not intraday_data.empty:
                    today_volume = intraday_data['Volume'].sum()
                    volume_ratio = today_volume / avg_volume if avg_volume > 0 else 0
                else:
                    today_volume = 0
                    volume_ratio = 0

                # Check if volume is sufficient
                if avg_volume > 100000:  # Minimum average volume threshold
                    stock_info['avg_volume'] = avg_volume
                    stock_info['today_volume'] = today_volume
                    stock_info['volume_ratio'] = volume_ratio
                    liquid_stocks.append(stock_info)

            except Exception as e:
                print(f"  Error checking liquidity for {symbol}: {e}")
                continue

        # Sort by average volume
        liquid_stocks.sort(key=lambda x: x['avg_volume'], reverse=True)

        print(f"\nFound {len(liquid_stocks)} liquid stocks:")
        for stock in liquid_stocks[:10]:  # Show top 10
            print(f"  {stock['symbol']:15s} | Avg Vol: {stock['avg_volume']:>12,.0f} | "
                  f"Gap: {stock['gap_pct']:+6.2f}%")

        return liquid_stocks

    def apply_news_filter(self, stocks: List[Dict]) -> List[Dict]:
        """
        Step 4: Mark stocks with important news (results, mergers, etc.)

        Note: This is a placeholder. In production, integrate with news API.

        Args:
            stocks: List of stock dictionaries

        Returns:
            List of stocks with news flags
        """
        print("\n" + "="*60)
        print("STEP 4: NEWS FILTER")
        print("="*60)

        # In a real implementation, you would:
        # 1. Fetch news from APIs like NewsAPI, MoneyControl, etc.
        # 2. Check for earnings dates using yfinance
        # 3. Mark stocks with significant news

        for stock in stocks:
            symbol = stock['symbol']

            # Add placeholder news flag
            stock['has_news'] = False
            stock['news_type'] = None

            # You can check earnings calendar from yfinance
            try:
                import yfinance as yf
                ticker = yf.Ticker(symbol)
                calendar = ticker.calendar

                if calendar is not None and not calendar.empty:
                    # Check if earnings date is today or soon
                    stock['has_news'] = True
                    stock['news_type'] = 'earnings'
            except:
                pass

        print("Note: News filtering is basic. Integrate with news APIs for better results.")
        news_stocks = [s for s in stocks if s.get('has_news', False)]
        if news_stocks:
            print(f"\nStocks with news/events: {len(news_stocks)}")
            for stock in news_stocks:
                print(f"  {stock['symbol']:15s} | {stock['news_type']} | Gap: {stock['gap_pct']:+6.2f}%")
        else:
            print("\nNo stocks with detected news/events")

        return stocks

    def run_screening(self) -> List[Dict]:
        """
        Run complete pre-market screening process

        Returns:
            List of candidate stocks (5-8 stocks)
        """
        print("\n" + "🔍 " + "="*58 + " 🔍")
        print("        PRE-MARKET SCREENER (8:45 - 9:15 AM)")
        print("🔍 " + "="*58 + " 🔍\n")

        # Step 1: Index context
        index_context = self.get_index_context()
        nifty_trend = index_context['nifty'].get('trend', 'sideways')

        # Step 2: Gap filter
        gap_stocks = self.apply_gap_filter(NIFTY_50_STOCKS, nifty_trend)

        if not gap_stocks:
            print("\n⚠️  No stocks found with valid gaps. Exiting screening.")
            return []

        # Step 3: Liquidity filter
        liquid_stocks = self.apply_liquidity_filter(gap_stocks)

        if not liquid_stocks:
            print("\n⚠️  No liquid stocks found. Exiting screening.")
            return []

        # Step 4: News filter
        final_stocks = self.apply_news_filter(liquid_stocks)

        # Select top candidates
        max_candidates = self.config['pre_market_candidates']
        self.candidates = final_stocks[:max_candidates]

        # Final output
        print("\n" + "="*60)
        print(f"🎯 FINAL PRE-MARKET CANDIDATES: {len(self.candidates)} stocks")
        print("="*60)

        for i, stock in enumerate(self.candidates, 1):
            print(f"\n{i}. {stock['symbol']}")
            print(f"   Price: ₹{stock['current_price']:.2f} | Gap: {stock['gap_pct']:+.2f}% ({stock['gap_direction']})")
            print(f"   Avg Volume: {stock['avg_volume']:,.0f}")
            print(f"   Aligned with Index: {'Yes' if stock['aligned_with_index'] else 'No'}")
            if stock.get('has_news'):
                print(f"   News: {stock.get('news_type', 'N/A')}")

        return self.candidates
