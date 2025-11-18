"""
Risk Management Module
Manages trading risk, position sizing, and trade tracking
"""

import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from config.config import TRADING_CONFIG


class RiskManager:
    """
    Manages risk for trading operations:
    - Position sizing (1% risk per trade)
    - Max trades per day (2-3)
    - Stop trading after 2 consecutive losses
    - Track daily P&L
    """

    def __init__(self, capital: float, config: dict = None):
        self.capital = capital
        self.initial_capital = capital
        self.config = config or TRADING_CONFIG

        # Trading limits
        self.risk_per_trade_pct = self.config['risk_per_trade_pct']
        self.max_trades_per_day = self.config['max_trades_per_day']
        self.max_consecutive_losses = self.config['max_consecutive_losses']

        # Trade tracking
        self.trades = []
        self.daily_trades = 0
        self.consecutive_losses = 0
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_pnl = 0

    def can_take_trade(self) -> Tuple[bool, str]:
        """
        Check if we can take another trade based on risk rules

        Returns:
            Tuple of (can_trade, reason)
        """
        # Check max trades per day
        if self.daily_trades >= self.max_trades_per_day:
            return False, f"Maximum trades per day reached ({self.max_trades_per_day})"

        # Check consecutive losses
        if self.consecutive_losses >= self.max_consecutive_losses:
            return False, f"Maximum consecutive losses reached ({self.max_consecutive_losses})"

        # Check if capital is sufficient (at least 20% of initial capital)
        if self.capital < self.initial_capital * 0.2:
            return False, "Capital too low (below 20% of initial)"

        return True, "OK"

    def calculate_position_size(
        self,
        entry_price: float,
        stop_loss: float,
        custom_risk_pct: float = None
    ) -> Dict:
        """
        Calculate position size based on risk per trade

        Args:
            entry_price: Entry price
            stop_loss: Stop-loss price
            custom_risk_pct: Custom risk percentage (optional)

        Returns:
            Dictionary with position sizing details
        """
        risk_pct = custom_risk_pct or self.risk_per_trade_pct
        risk_amount = self.capital * (risk_pct / 100)

        risk_per_share = abs(entry_price - stop_loss)

        if risk_per_share == 0:
            return {
                'quantity': 0,
                'risk_amount': 0,
                'position_value': 0,
                'error': 'Invalid stop-loss (zero risk per share)'
            }

        quantity = int(risk_amount / risk_per_share)
        position_value = quantity * entry_price

        # Check if position value is within limits (not more than 20% of capital)
        max_position_value = self.capital * 0.2

        if position_value > max_position_value:
            # Reduce quantity
            quantity = int(max_position_value / entry_price)
            position_value = quantity * entry_price
            actual_risk = quantity * risk_per_share

        return {
            'quantity': quantity,
            'risk_amount': risk_amount,
            'position_value': position_value,
            'risk_per_share': risk_per_share,
            'risk_pct': risk_pct,
        }

    def add_trade(
        self,
        symbol: str,
        setup_type: str,
        entry_price: float,
        stop_loss: float,
        target: float,
        quantity: int,
        timestamp: datetime = None
    ) -> Dict:
        """
        Add a new trade to tracking

        Args:
            symbol: Stock symbol
            setup_type: 'BUY' or 'SELL'
            entry_price: Entry price
            stop_loss: Stop-loss price
            target: Target price
            quantity: Number of shares
            timestamp: Trade timestamp (default: now)

        Returns:
            Trade dictionary
        """
        if timestamp is None:
            timestamp = datetime.now()

        trade = {
            'id': len(self.trades) + 1,
            'symbol': symbol,
            'type': setup_type,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'target': target,
            'quantity': quantity,
            'entry_time': timestamp,
            'status': 'open',
            'exit_price': None,
            'exit_time': None,
            'pnl': 0,
            'pnl_pct': 0,
        }

        self.trades.append(trade)
        self.daily_trades += 1
        self.total_trades += 1

        return trade

    def close_trade(
        self,
        trade_id: int,
        exit_price: float,
        timestamp: datetime = None
    ) -> Dict:
        """
        Close an open trade

        Args:
            trade_id: Trade ID
            exit_price: Exit price
            timestamp: Exit timestamp (default: now)

        Returns:
            Updated trade dictionary
        """
        if timestamp is None:
            timestamp = datetime.now()

        # Find trade
        trade = None
        for t in self.trades:
            if t['id'] == trade_id:
                trade = t
                break

        if not trade:
            return {'error': 'Trade not found'}

        if trade['status'] != 'open':
            return {'error': 'Trade already closed'}

        # Calculate P&L
        if trade['type'] == 'BUY':
            pnl = (exit_price - trade['entry_price']) * trade['quantity']
        else:  # SELL
            pnl = (trade['entry_price'] - exit_price) * trade['quantity']

        pnl_pct = (pnl / (trade['entry_price'] * trade['quantity'])) * 100

        # Update trade
        trade['exit_price'] = exit_price
        trade['exit_time'] = timestamp
        trade['status'] = 'closed'
        trade['pnl'] = pnl
        trade['pnl_pct'] = pnl_pct

        # Update capital
        self.capital += pnl
        self.total_pnl += pnl

        # Track win/loss
        if pnl > 0:
            self.winning_trades += 1
            self.consecutive_losses = 0
        else:
            self.losing_trades += 1
            self.consecutive_losses += 1

        return trade

    def get_open_trades(self) -> List[Dict]:
        """Get all open trades"""
        return [t for t in self.trades if t['status'] == 'open']

    def get_closed_trades(self) -> List[Dict]:
        """Get all closed trades"""
        return [t for t in self.trades if t['status'] == 'closed']

    def get_daily_summary(self) -> Dict:
        """
        Get summary of today's trading

        Returns:
            Dictionary with daily statistics
        """
        closed_trades = self.get_closed_trades()

        if not closed_trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'total_pnl_pct': 0,
                'average_pnl': 0,
            }

        total_pnl = sum(t['pnl'] for t in closed_trades)
        total_pnl_pct = (total_pnl / self.initial_capital) * 100

        return {
            'total_trades': len(closed_trades),
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': (self.winning_trades / len(closed_trades)) * 100 if closed_trades else 0,
            'total_pnl': total_pnl,
            'total_pnl_pct': total_pnl_pct,
            'average_pnl': total_pnl / len(closed_trades) if closed_trades else 0,
            'current_capital': self.capital,
            'capital_change': self.capital - self.initial_capital,
            'capital_change_pct': ((self.capital - self.initial_capital) / self.initial_capital) * 100,
        }

    def print_summary(self):
        """Print trading summary"""
        summary = self.get_daily_summary()

        print("\n" + "="*60)
        print("📊 TRADING SUMMARY")
        print("="*60)
        print(f"\nCapital:")
        print(f"  Initial: ₹{self.initial_capital:,.2f}")
        print(f"  Current: ₹{summary['current_capital']:,.2f}")
        print(f"  Change: ₹{summary['capital_change']:+,.2f} ({summary['capital_change_pct']:+.2f}%)")

        print(f"\nTrades:")
        print(f"  Total: {summary['total_trades']}")
        print(f"  Winning: {summary['winning_trades']} ({summary['win_rate']:.1f}%)")
        print(f"  Losing: {summary['losing_trades']}")
        print(f"  Open: {len(self.get_open_trades())}")

        print(f"\nP&L:")
        print(f"  Total: ₹{summary['total_pnl']:+,.2f} ({summary['total_pnl_pct']:+.2f}%)")
        print(f"  Average: ₹{summary['average_pnl']:+,.2f}")

        print(f"\nRisk Status:")
        print(f"  Consecutive Losses: {self.consecutive_losses}/{self.max_consecutive_losses}")
        print(f"  Daily Trades: {self.daily_trades}/{self.max_trades_per_day}")

        can_trade, reason = self.can_take_trade()
        print(f"  Can Trade: {'Yes ✓' if can_trade else f'No ✗ ({reason})'}")

    def validate_trade_plan(self, trade_plan: Dict, capital: float = None) -> Dict:
        """
        Validate a trade plan against risk rules

        Args:
            trade_plan: Trading plan dictionary
            capital: Capital to use (default: current capital)

        Returns:
            Dictionary with validation results and position sizing
        """
        if capital is None:
            capital = self.capital

        # Check if we can take trade
        can_trade, reason = self.can_take_trade()

        if not can_trade:
            return {
                'valid': False,
                'reason': reason,
            }

        # Calculate position size
        position_info = self.calculate_position_size(
            trade_plan['entry_price'],
            trade_plan['stop_loss']
        )

        if position_info['quantity'] == 0:
            return {
                'valid': False,
                'reason': position_info.get('error', 'Invalid position size'),
            }

        # Calculate potential profit/loss
        risk_amount = position_info['risk_amount']
        potential_profit = position_info['quantity'] * abs(trade_plan['target'] - trade_plan['entry_price'])

        return {
            'valid': True,
            'quantity': position_info['quantity'],
            'position_value': position_info['position_value'],
            'risk_amount': risk_amount,
            'risk_pct': position_info['risk_pct'],
            'potential_profit': potential_profit,
            'risk_reward_ratio': potential_profit / risk_amount if risk_amount > 0 else 0,
        }

    def reset_daily_counters(self):
        """Reset daily counters (call at start of each day)"""
        self.daily_trades = 0
        # Note: consecutive_losses is NOT reset as it carries across days
