"""
Production-Ready Intraday Stock Screener
A modular, configurable screening and signal generation system for Nifty 50 stocks
"""

__version__ = "1.0.0"
__author__ = "Stock Screener Team"

from .data_ingest import CSVDataLoader, DataValidator
from .indicators import EMA, VWAP, ATR
from .screener import PreMarketScreener, LiveMarketFilter
from .signal_engine import SignalGenerator
from .risk_manager import RiskManager, PositionSizer
from .backtester import BacktestEngine

__all__ = [
    "CSVDataLoader",
    "DataValidator",
    "EMA",
    "VWAP",
    "ATR",
    "PreMarketScreener",
    "LiveMarketFilter",
    "SignalGenerator",
    "RiskManager",
    "PositionSizer",
    "BacktestEngine",
]
