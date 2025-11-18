"""
Position Sizing and Risk Management
Manages position sizing, trade tracking, and risk controls
"""

import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class PositionSizer:
    """
    Calculate position sizes based on risk rules
    """

    @staticmethod
    def calculate_position_size(
        capital: float,
        entry_price: float,
        stop_loss: float,
        risk_percent: float = 1.0
    ) -> Dict:
        """
        Calculate position size to risk exactly X% of capital

        Args:
            capital: Total trading capital
            entry_price: Entry price
            stop_loss: Stop-loss price
            risk_percent: Percentage of capital to risk (default 1.0%)

        Returns:
            Dictionary with position sizing details
        """
        risk_amount = capital * (risk_percent / 100)
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

        # Ensure position not too large (max 20% of capital)
        max_position_value = capital * 0.2

        if position_value > max_position_value:
            quantity = int(max_position_value / entry_price)
            position_value = quantity * entry_price
            actual_risk = quantity * risk_per_share

        return {
            'quantity': quantity,
            'risk_amount': risk_amount,
            'position_value': position_value,
            'risk_per_share': risk_per_share,
            'risk_percent': risk_percent
        }

    @staticmethod
    def validate_signal(
        signal: Dict,
        capital: float,
        config: Dict
    ) -> Tuple[bool, str, Optional[Dict]]:
        """
        Validate a signal and calculate position size

        Args:
            signal: Trading signal
            capital: Available capital
            config: Risk configuration

        Returns:
            Tuple of (is_valid, reason, position_info)
        """
        # Calculate position size
        position = PositionSizer.calculate_position_size(
            capital=capital,
            entry_price=signal['entry'],
            stop_loss=signal['stop_loss'],
            risk_percent=config['risk']['risk_per_trade_percent']
        )

        if position['quantity'] == 0:
            return False, position.get('error', 'Invalid position size'), None

        # Check if sufficient capital
        if position['position_value'] > capital:
            return False, 'Insufficient capital', None

        # Add position info to response
        position['potential_profit'] = position['quantity'] * abs(signal['target'] - signal['entry'])
        position['risk_reward'] = position['potential_profit'] / position['risk_amount'] if position['risk_amount'] > 0 else 0

        return True, 'Valid', position


class RiskManager:
    """
    Track and manage trading risk
    Enforces risk rules and tracks P&L
    """

    def __init__(self, initial_capital: float, config: Dict):
        """
        Initialize risk manager

        Args:
            initial_capital: Starting capital
            config: Risk configuration from YAML
        """
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.config = config

        # Risk limits
        self.max_trades_per_day = config['risk']['max_trades_per_day']
        self.max_consecutive_losses = config['risk']['max_consecutive_losses']

        # Trade tracking
        self.trades = []
        self.daily_trades = 0
        self.consecutive_losses = 0
        self.winning_trades = 0
        self.losing_trades = 0

    def can_take_trade(self) -> Tuple[bool, str]:
        """
        Check if we can take another trade

        Returns:
            Tuple of (can_trade, reason)
        """
        # Check max trades per day
        if self.daily_trades >= self.max_trades_per_day:
            return False, f"Max trades per day reached ({self.max_trades_per_day})"

        # Check consecutive losses
        if self.consecutive_losses >= self.max_consecutive_losses:
            return False, f"Max consecutive losses reached ({self.max_consecutive_losses})"

        # Check capital (must have at least 20% of initial)
        if self.capital < self.initial_capital * 0.2:
            return False, "Capital too low (below 20% of initial)"

        return True, "OK"

    def add_trade(
        self,
        symbol: str,
        signal: Dict,
        position: Dict,
        timestamp: datetime = None
    ) -> Dict:
        """
        Add a new trade

        Args:
            symbol: Stock symbol
            signal: Trading signal
            position: Position sizing info
            timestamp: Trade timestamp

        Returns:
            Trade dictionary
        """
        if timestamp is None:
            timestamp = datetime.now()

        trade = {
            'id': len(self.trades) + 1,
            'symbol': symbol,
            'type': signal['type'],
            'entry': signal['entry'],
            'stop_loss': signal['stop_loss'],
            'target': signal['target'],
            'quantity': position['quantity'],
            'entry_time': timestamp,
            'status': 'open',
            'exit_price': None,
            'exit_time': None,
            'pnl': 0,
            'pnl_percent': 0
        }

        self.trades.append(trade)
        self.daily_trades += 1

        logger.info(
            f"Trade #{trade['id']}: {signal['type']} {symbol} "
            f"qty={position['quantity']} @ {signal['entry']:.2f}"
        )

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
            timestamp: Exit timestamp

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
            pnl = (exit_price - trade['entry']) * trade['quantity']
        else:  # SELL
            pnl = (trade['entry'] - exit_price) * trade['quantity']

        pnl_percent = (pnl / (trade['entry'] * trade['quantity'])) * 100

        # Update trade
        trade['exit_price'] = exit_price
        trade['exit_time'] = timestamp
        trade['status'] = 'closed'
        trade['pnl'] = pnl
        trade['pnl_percent'] = pnl_percent

        # Update capital
        self.capital += pnl

        # Track win/loss
        if pnl > 0:
            self.winning_trades += 1
            self.consecutive_losses = 0
            logger.info(f"Trade #{trade_id} CLOSED: WIN +₹{pnl:.2f} ({pnl_percent:+.2f}%)")
        else:
            self.losing_trades += 1
            self.consecutive_losses += 1
            logger.info(f"Trade #{trade_id} CLOSED: LOSS ₹{pnl:.2f} ({pnl_percent:+.2f}%)")

        return trade

    def get_open_trades(self) -> List[Dict]:
        """Get all open trades"""
        return [t for t in self.trades if t['status'] == 'open']

    def get_closed_trades(self) -> List[Dict]:
        """Get all closed trades"""
        return [t for t in self.trades if t['status'] == 'closed']

    def get_summary(self) -> Dict:
        """
        Get trading summary statistics

        Returns:
            Dictionary with summary metrics
        """
        closed_trades = self.get_closed_trades()

        if not closed_trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'total_pnl_percent': 0,
                'average_pnl': 0,
                'current_capital': self.capital,
                'capital_change': 0,
                'capital_change_percent': 0
            }

        total_pnl = sum(t['pnl'] for t in closed_trades)
        total_pnl_percent = ((self.capital - self.initial_capital) / self.initial_capital) * 100

        return {
            'total_trades': len(closed_trades),
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': (self.winning_trades / len(closed_trades)) * 100 if closed_trades else 0,
            'total_pnl': total_pnl,
            'total_pnl_percent': total_pnl_percent,
            'average_pnl': total_pnl / len(closed_trades) if closed_trades else 0,
            'current_capital': self.capital,
            'capital_change': self.capital - self.initial_capital,
            'capital_change_percent': total_pnl_percent,
            'consecutive_losses': self.consecutive_losses,
            'daily_trades': self.daily_trades
        }

    def reset_daily_counters(self):
        """Reset daily trade counter"""
        self.daily_trades = 0
        logger.info("Daily counters reset")
