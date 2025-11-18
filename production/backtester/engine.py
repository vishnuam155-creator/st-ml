"""
Backtest Engine
Simulates the screening and trading strategy on historical data
"""

import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import datetime, timedelta
import logging

from ..screener import PreMarketScreener, LiveMarketFilter
from ..signal_engine import SignalGenerator
from ..risk_manager import RiskManager, PositionSizer

logger = logging.getLogger(__name__)


class BacktestEngine:
    """
    Backtest the complete screening and trading system
    """

    def __init__(self, config: Dict):
        """
        Initialize backtest engine

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.pre_market_screener = PreMarketScreener(config)
        self.live_market_filter = LiveMarketFilter(config)
        self.signal_generator = SignalGenerator(config)

    def run_backtest(
        self,
        start_date: datetime,
        end_date: datetime,
        initial_capital: float
    ) -> Dict:
        """
        Run backtest over date range

        Args:
            start_date: Start date
            end_date: End date
            initial_capital: Starting capital

        Returns:
            Dictionary with backtest results
        """
        logger.info(f"Running backtest from {start_date.date()} to {end_date.date()}")

        # Initialize risk manager
        risk_manager = RiskManager(initial_capital, self.config)

        # Track daily results
        daily_results = []

        # Iterate through trading days
        current_date = start_date

        while current_date <= end_date:
            # Skip weekends
            if current_date.weekday() >= 5:
                current_date += timedelta(days=1)
                continue

            logger.info(f"\n{'='*60}")
            logger.info(f"Backtesting: {current_date.date()}")
            logger.info(f"{'='*60}")

            # Reset daily counters
            risk_manager.reset_daily_counters()

            try:
                # Step 1: Pre-market screening
                pre_market_candidates = self.pre_market_screener.run_screening(current_date)

                if not pre_market_candidates:
                    logger.info("No pre-market candidates")
                    daily_results.append({
                        'date': current_date,
                        'pre_market_candidates': 0,
                        'live_market_candidates': 0,
                        'signals': 0,
                        'trades': 0,
                        'pnl': 0
                    })
                    current_date += timedelta(days=1)
                    continue

                # Step 2: Live market filtering
                live_market_candidates = self.live_market_filter.run_filtering(
                    pre_market_candidates,
                    current_date
                )

                if not live_market_candidates:
                    logger.info("No live market candidates")
                    daily_results.append({
                        'date': current_date,
                        'pre_market_candidates': len(pre_market_candidates),
                        'live_market_candidates': 0,
                        'signals': 0,
                        'trades': 0,
                        'pnl': 0
                    })
                    current_date += timedelta(days=1)
                    continue

                # Step 3: Generate signals
                signals = self.signal_generator.generate_signals(live_market_candidates)

                if not signals:
                    logger.info("No signals generated")
                    daily_results.append({
                        'date': current_date,
                        'pre_market_candidates': len(pre_market_candidates),
                        'live_market_candidates': len(live_market_candidates),
                        'signals': 0,
                        'trades': 0,
                        'pnl': 0
                    })
                    current_date += timedelta(days=1)
                    continue

                # Step 4: Execute trades
                day_pnl = 0
                trades_taken = 0

                for signal in signals:
                    # Check if can take trade
                    can_trade, reason = risk_manager.can_take_trade()

                    if not can_trade:
                        logger.info(f"Cannot take trade: {reason}")
                        break

                    # Validate signal and calculate position
                    is_valid, reason, position = PositionSizer.validate_signal(
                        signal,
                        risk_manager.capital,
                        self.config
                    )

                    if not is_valid:
                        logger.warning(f"Invalid signal for {signal['symbol']}: {reason}")
                        continue

                    # Add trade
                    trade = risk_manager.add_trade(
                        signal['symbol'],
                        signal,
                        position,
                        current_date
                    )

                    # Simulate trade exit (simplified: assume hit target or stop)
                    exit_price = self._simulate_exit(signal, current_date)

                    # Close trade
                    closed_trade = risk_manager.close_trade(
                        trade['id'],
                        exit_price,
                        current_date
                    )

                    day_pnl += closed_trade['pnl']
                    trades_taken += 1

                # Record daily results
                daily_results.append({
                    'date': current_date,
                    'pre_market_candidates': len(pre_market_candidates),
                    'live_market_candidates': len(live_market_candidates),
                    'signals': len(signals),
                    'trades': trades_taken,
                    'pnl': day_pnl
                })

            except Exception as e:
                logger.error(f"Error on {current_date.date()}: {e}")

            # Move to next day
            current_date += timedelta(days=1)

        # Calculate overall metrics
        results = self._calculate_metrics(risk_manager, daily_results, initial_capital)

        return results

    def _simulate_exit(self, signal: Dict, date: datetime) -> float:
        """
        Simulate trade exit (simplified)

        In reality, you'd replay minute data to see if SL or target hit.
        For simplicity, we assume:
        - 60% probability of hitting target
        - 40% probability of hitting stop-loss

        Args:
            signal: Trading signal
            date: Trading date

        Returns:
            Exit price
        """
        # Simple Monte Carlo simulation
        hit_target = np.random.random() < 0.6

        if hit_target:
            return signal['target']
        else:
            return signal['stop_loss']

    def _calculate_metrics(
        self,
        risk_manager: RiskManager,
        daily_results: List[Dict],
        initial_capital: float
    ) -> Dict:
        """
        Calculate backtest metrics

        Args:
            risk_manager: RiskManager instance
            daily_results: List of daily results
            initial_capital: Starting capital

        Returns:
            Dictionary with metrics
        """
        summary = risk_manager.get_summary()
        closed_trades = risk_manager.get_closed_trades()

        # Daily P&L series
        daily_pnl = [d['pnl'] for d in daily_results]
        cumulative_pnl = np.cumsum(daily_pnl)

        # Calculate max drawdown
        running_max = np.maximum.accumulate(cumulative_pnl)
        drawdown = running_max - cumulative_pnl
        max_drawdown = np.max(drawdown) if len(drawdown) > 0 else 0

        # Calculate Sharpe ratio (simplified)
        if len(daily_pnl) > 1:
            sharpe_ratio = np.mean(daily_pnl) / np.std(daily_pnl) * np.sqrt(252)
        else:
            sharpe_ratio = 0

        results = {
            'summary': summary,
            'total_days': len(daily_results),
            'trading_days': sum(1 for d in daily_results if d['trades'] > 0),
            'total_signals': sum(d['signals'] for d in daily_results),
            'total_trades': sum(d['trades'] for d in daily_results),
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'daily_results': daily_results,
            'trades': closed_trades
        }

        logger.info("\n" + "="*60)
        logger.info("BACKTEST RESULTS")
        logger.info("="*60)
        logger.info(f"Total Days: {results['total_days']}")
        logger.info(f"Trading Days: {results['trading_days']}")
        logger.info(f"Total Trades: {results['total_trades']}")
        logger.info(f"Win Rate: {summary['win_rate']:.2f}%")
        logger.info(f"Total P&L: ₹{summary['total_pnl']:,.2f} ({summary['total_pnl_percent']:+.2f}%)")
        logger.info(f"Max Drawdown: ₹{max_drawdown:,.2f}")
        logger.info(f"Sharpe Ratio: {sharpe_ratio:.2f}")
        logger.info("="*60)

        return results
