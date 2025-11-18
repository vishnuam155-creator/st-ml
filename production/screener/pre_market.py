"""
Pre-Market Screener
Screens stocks before market open (8:45 - 9:15 AM)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
import logging

from ..data_ingest import CSVDataLoader
from ..indicators import EMA

logger = logging.getLogger(__name__)


class PreMarketScreener:
    """
    Pre-market stock screener
    Filters stocks based on gaps, liquidity, and news
    """

    def __init__(self, config: Dict):
        """
        Initialize pre-market screener

        Args:
            config: Configuration dictionary from YAML
        """
        self.config = config
        self.data_loader = CSVDataLoader(
            minute_data_dir=config['data']['csv']['minute_data_dir'],
            daily_data_dir=config['data']['csv']['daily_data_dir'],
            timezone=config['market']['timezone']
        )

    def get_index_context(self, date: datetime) -> Dict:
        """
        Determine index context (Nifty & BankNifty trend)

        Uses 50/200 EMA on daily data to determine trend:
        - Uptrend: price > 50 EMA > 200 EMA
        - Downtrend: price < 50 EMA < 200 EMA
        - Sideways: mixed

        Args:
            date: Trading date

        Returns:
            Dictionary with index trends and levels
        """
        logger.info("Getting index context...")

        context = {}
        indices = self.config['universe']['indices']

        for index_symbol in indices:
            # Load daily data
            daily_data = self.data_loader.load_daily_data(
                index_symbol,
                lookback_days=250
            )

            if daily_data.empty:
                logger.warning(f"No daily data for {index_symbol}")
                continue

            # Calculate EMAs
            ema_fast_period = self.config['index_context']['ema_fast']
            ema_slow_period = self.config['index_context']['ema_slow']

            daily_data['ema_fast'] = EMA.calculate(daily_data['close'], ema_fast_period)
            daily_data['ema_slow'] = EMA.calculate(daily_data['close'], ema_slow_period)

            # Get latest values
            latest = daily_data.iloc[-1]
            current_price = latest['close']
            ema_fast = latest['ema_fast']
            ema_slow = latest['ema_slow']

            # Determine trend
            trend = EMA.get_trend(current_price, ema_fast, ema_slow)

            # Calculate change from previous close
            if len(daily_data) >= 2:
                prev_close = daily_data['close'].iloc[-2]
                change_pct = ((current_price - prev_close) / prev_close) * 100
            else:
                change_pct = 0.0

            context[index_symbol] = {
                'trend': trend,
                'current_price': current_price,
                'ema_fast': ema_fast,
                'ema_slow': ema_slow,
                'change_pct': change_pct,
                'yesterday_high': daily_data['high'].iloc[-1],
                'yesterday_low': daily_data['low'].iloc[-1]
            }

            logger.info(
                f"{index_symbol}: trend={trend}, price={current_price:.2f}, "
                f"change={change_pct:+.2f}%"
            )

        return context

    def apply_gap_filter(
        self,
        symbols: List[str],
        date: datetime,
        index_trend: str
    ) -> List[Dict]:
        """
        Filter stocks with gaps between 0.3% and 2.0%

        Prefers gaps in same direction as Nifty

        Args:
            symbols: List of stock symbols
            date: Trading date
            index_trend: Nifty trend ('uptrend', 'downtrend', 'sideways')

        Returns:
            List of stocks with gap information
        """
        logger.info("Applying gap filter...")

        gap_min = self.config['pre_market']['gap']['min_percent']
        gap_max = self.config['pre_market']['gap']['max_percent']

        gap_stocks = []

        for symbol in symbols:
            try:
                # Get previous close
                prev_close = self.data_loader.get_previous_close(symbol, date)

                if prev_close is None:
                    continue

                # Get current price (from minute data)
                minute_data = self.data_loader.load_minute_data(
                    symbol,
                    start_date=date.replace(hour=9, minute=0),
                    end_date=date.replace(hour=9, minute=30)
                )

                if minute_data.empty:
                    continue

                current_price = minute_data['close'].iloc[0]

                # Calculate gap
                gap_pct = ((current_price - prev_close) / prev_close) * 100

                # Filter by gap range
                if gap_min <= abs(gap_pct) <= gap_max:
                    gap_direction = 'up' if gap_pct > 0 else 'down'

                    # Check alignment with index
                    aligned_with_index = False
                    if (index_trend == 'uptrend' and gap_direction == 'up') or \
                       (index_trend == 'downtrend' and gap_direction == 'down'):
                        aligned_with_index = True

                    gap_stocks.append({
                        'symbol': symbol,
                        'current_price': current_price,
                        'prev_close': prev_close,
                        'gap_pct': gap_pct,
                        'gap_direction': gap_direction,
                        'aligned_with_index': aligned_with_index
                    })

            except Exception as e:
                logger.error(f"Error processing {symbol} in gap filter: {e}")
                continue

        # Sort by alignment with index and gap size
        gap_stocks.sort(
            key=lambda x: (x['aligned_with_index'], abs(x['gap_pct'])),
            reverse=True
        )

        logger.info(f"Found {len(gap_stocks)} stocks with valid gaps")
        return gap_stocks

    def apply_liquidity_filter(
        self,
        stocks: List[Dict],
        date: datetime
    ) -> List[Dict]:
        """
        Filter stocks with high liquidity

        Checks:
        - Average volume over last 20 days
        - Pre-open/first 5-min volume

        Args:
            stocks: List of stock dictionaries from gap filter
            date: Trading date

        Returns:
            List of liquid stocks
        """
        logger.info("Applying liquidity filter...")

        min_avg_volume = self.config['pre_market']['liquidity']['min_avg_volume']
        lookback_days = self.config['pre_market']['liquidity']['volume_lookback_days']
        min_preopen_ratio = self.config['pre_market']['liquidity']['min_preopen_volume_ratio']

        liquid_stocks = []

        for stock in stocks:
            symbol = stock['symbol']

            try:
                # Get historical volume
                daily_data = self.data_loader.load_daily_data(symbol, lookback_days)

                if daily_data.empty:
                    continue

                avg_volume = daily_data['volume'].mean()

                # Check minimum volume threshold
                if avg_volume < min_avg_volume:
                    continue

                # Get pre-open volume
                minute_data = self.data_loader.load_minute_data(
                    symbol,
                    start_date=date.replace(hour=9, minute=0),
                    end_date=date.replace(hour=9, minute=20)
                )

                if not minute_data.empty:
                    preopen_volume = minute_data['volume'].sum()
                    volume_ratio = preopen_volume / (avg_volume / 78)  # Approximate daily volume per 5-min
                else:
                    preopen_volume = 0
                    volume_ratio = 0

                # Add liquidity metrics
                stock['avg_volume'] = avg_volume
                stock['preopen_volume'] = preopen_volume
                stock['volume_ratio'] = volume_ratio

                # Filter by minimum pre-open volume
                if volume_ratio >= min_preopen_ratio or avg_volume > min_avg_volume * 2:
                    liquid_stocks.append(stock)

            except Exception as e:
                logger.error(f"Error checking liquidity for {symbol}: {e}")
                continue

        # Sort by average volume
        liquid_stocks.sort(key=lambda x: x['avg_volume'], reverse=True)

        logger.info(f"Found {len(liquid_stocks)} liquid stocks")
        return liquid_stocks

    def apply_news_filter(
        self,
        stocks: List[Dict],
        date: datetime
    ) -> List[Dict]:
        """
        Mark stocks with important news/events

        Args:
            stocks: List of stock dictionaries
            date: Trading date

        Returns:
            List of stocks with news flags
        """
        logger.info("Applying news filter...")

        # Load news data
        news_file = self.config['data']['csv'].get('news_file')

        if not news_file:
            logger.warning("No news file configured")
            for stock in stocks:
                stock['has_news'] = False
                stock['news_type'] = None
            return stocks

        news_data = self.data_loader.load_news_data(news_file)

        if news_data.empty:
            for stock in stocks:
                stock['has_news'] = False
                stock['news_type'] = None
            return stocks

        # Filter news for today
        today_news = news_data[news_data['date'].dt.date == date.date()]

        # Tag stocks with news
        for stock in stocks:
            symbol = stock['symbol']
            stock_news = today_news[today_news['symbol'] == symbol]

            if not stock_news.empty:
                stock['has_news'] = True
                stock['news_type'] = stock_news['event_type'].iloc[0]
                stock['news_description'] = stock_news['description'].iloc[0]
            else:
                stock['has_news'] = False
                stock['news_type'] = None

        logger.info(f"Tagged {sum(1 for s in stocks if s['has_news'])} stocks with news")
        return stocks

    def score_candidates(self, stocks: List[Dict]) -> List[Dict]:
        """
        Score candidates based on multiple factors

        Scoring (0-100):
        - Gap size: 30 points (larger gap = higher score)
        - Alignment with index: 25 points
        - Liquidity: 25 points
        - News: 20 points

        Args:
            stocks: List of candidate stocks

        Returns:
            List of stocks with scores added
        """
        for stock in stocks:
            score = 0

            # Gap size score (0-30)
            gap_pct = abs(stock['gap_pct'])
            gap_score = min((gap_pct / 2.0) * 30, 30)  # Max at 2%
            score += gap_score

            # Alignment score (0-25)
            if stock['aligned_with_index']:
                score += 25

            # Liquidity score (0-25)
            avg_vol = stock.get('avg_volume', 0)
            if avg_vol > 10_000_000:
                score += 25
            elif avg_vol > 5_000_000:
                score += 20
            elif avg_vol > 1_000_000:
                score += 15
            elif avg_vol > 500_000:
                score += 10
            else:
                score += 5

            # News score (0-20)
            if stock.get('has_news', False):
                if stock['news_type'] in ['earnings', 'results']:
                    score += 20
                else:
                    score += 10

            stock['score'] = round(score, 2)

        return stocks

    def run_screening(
        self,
        date: datetime,
        symbols: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Run complete pre-market screening workflow

        Args:
            date: Trading date
            symbols: Optional list of symbols (defaults to config universe)

        Returns:
            List of 5-8 candidate stocks with scores
        """
        logger.info(f"Running pre-market screening for {date.date()}")

        # Use configured universe if not provided
        if symbols is None:
            symbols = self.config['universe']['stocks']

        # Step 1: Get index context
        index_context = self.get_index_context(date)

        # Get Nifty trend
        nifty_symbol = self.config['universe']['indices'][0]
        nifty_trend = index_context.get(nifty_symbol, {}).get('trend', 'sideways')

        # Step 2: Apply gap filter
        gap_stocks = self.apply_gap_filter(symbols, date, nifty_trend)

        if not gap_stocks:
            logger.warning("No stocks found with valid gaps")
            return []

        # Step 3: Apply liquidity filter
        liquid_stocks = self.apply_liquidity_filter(gap_stocks, date)

        if not liquid_stocks:
            logger.warning("No liquid stocks found")
            return []

        # Step 4: Apply news filter
        stocks_with_news = self.apply_news_filter(liquid_stocks, date)

        # Step 5: Score candidates
        scored_stocks = self.score_candidates(stocks_with_news)

        # Select top candidates
        max_candidates = self.config['pre_market']['max_candidates']
        final_candidates = sorted(scored_stocks, key=lambda x: x['score'], reverse=True)[:max_candidates]

        logger.info(f"Selected {len(final_candidates)} final candidates")

        return final_candidates
