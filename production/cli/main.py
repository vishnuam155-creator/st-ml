"""
Command-Line Interface
Main entry point for the screener application
"""

import argparse
import yaml
import json
import logging
from datetime import datetime
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from production.screener import PreMarketScreener, LiveMarketFilter
from production.signal_engine import SignalGenerator
from production.risk_manager import RiskManager, PositionSizer
from production.backtester import BacktestEngine
from production.data_ingest import DataValidator


def setup_logging(level: str = 'INFO'):
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/screener.log')
        ]
    )


def load_config(config_path: str) -> dict:
    """Load configuration from YAML file"""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config


def save_results(results: dict, output_path: str):
    """Save results to JSON file"""
    # Convert datetime objects to strings
    def serialize(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")

    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2, default=serialize)

    print(f"\nResults saved to: {output_path}")


def cmd_screen(args, config):
    """Run screening workflow"""
    date = datetime.strptime(args.date, '%Y-%m-%d')
    mode = args.mode

    print(f"\n{'='*60}")
    print(f"RUNNING SCREENER: {mode.upper()} MODE")
    print(f"Date: {date.date()}")
    print(f"{'='*60}\n")

    results = {}

    if mode in ['premarket', 'full']:
        # Pre-market screening
        screener = PreMarketScreener(config)
        pre_market_candidates = screener.run_screening(date)

        results['pre_market_candidates'] = pre_market_candidates

        print(f"\n✅ Pre-market screening complete: {len(pre_market_candidates)} candidates")

        if mode == 'premarket':
            # Save and exit
            if args.output:
                save_results(results, args.output)
            return

    if mode in ['live', 'full']:
        # Live market filtering
        if mode == 'live':
            # Need to run pre-market first
            screener = PreMarketScreener(config)
            pre_market_candidates = screener.run_screening(date)

        live_filter = LiveMarketFilter(config)
        live_candidates = live_filter.run_filtering(pre_market_candidates, date)

        results['live_market_candidates'] = live_candidates

        print(f"\n✅ Live market filtering complete: {len(live_candidates)} candidates")

        # Generate signals
        signal_gen = SignalGenerator(config)
        signals = signal_gen.generate_signals(live_candidates)

        results['signals'] = signals

        print(f"\n✅ Signal generation complete: {len(signals)} signals")

        # Calculate position sizing
        capital = args.capital
        risk_manager = RiskManager(capital, config)

        validated_signals = []
        for signal in signals:
            can_trade, reason = risk_manager.can_take_trade()

            if not can_trade:
                print(f"\n⚠️  Cannot take more trades: {reason}")
                break

            is_valid, reason, position = PositionSizer.validate_signal(
                signal,
                capital,
                config
            )

            if is_valid:
                signal['position'] = position
                validated_signals.append(signal)
            else:
                print(f"⚠️  Invalid signal for {signal['symbol']}: {reason}")

        results['validated_signals'] = validated_signals

        # Print summary
        print(f"\n{'='*60}")
        print("FINAL RECOMMENDATIONS")
        print(f"{'='*60}")

        for i, signal in enumerate(validated_signals, 1):
            print(f"\n{i}. {signal['symbol']} - {signal['type']}")
            print(f"   Entry: ₹{signal['entry']:.2f}")
            print(f"   Stop Loss: ₹{signal['stop_loss']:.2f}")
            print(f"   Target: ₹{signal['target']:.2f}")
            print(f"   Quantity: {signal['position']['quantity']} shares")
            print(f"   Risk: ₹{signal['position']['risk_amount']:,.2f}")
            print(f"   Potential Profit: ₹{signal['position']['potential_profit']:,.2f}")
            print(f"   Score: {signal['score']:.0f}/100")

    # Save results
    if args.output:
        save_results(results, args.output)


def cmd_backtest(args, config):
    """Run backtest"""
    start_date = datetime.strptime(args.start, '%Y-%m-%d')
    end_date = datetime.strptime(args.end, '%Y-%m-%d')
    capital = args.capital

    print(f"\n{'='*60}")
    print("RUNNING BACKTEST")
    print(f"Period: {start_date.date()} to {end_date.date()}")
    print(f"Capital: ₹{capital:,.2f}")
    print(f"{'='*60}\n")

    # Run backtest
    backtester = BacktestEngine(config)
    results = backtester.run_backtest(start_date, end_date, capital)

    # Save results
    if args.output:
        save_results(results, args.output)


def cmd_validate_data(args, config):
    """Validate data integrity"""
    from production.data_ingest import CSVDataLoader

    print(f"\n{'='*60}")
    print("VALIDATING DATA")
    print(f"{'='*60}\n")

    loader = CSVDataLoader(
        minute_data_dir=config['data']['csv']['minute_data_dir'],
        daily_data_dir=config['data']['csv']['daily_data_dir'],
        timezone=config['market']['timezone']
    )

    symbols = config['universe']['stocks'][:5]  # Test first 5 stocks

    for symbol in symbols:
        print(f"\nValidating {symbol}...")

        # Load data
        minute_data = loader.load_minute_data(symbol)
        daily_data = loader.load_daily_data(symbol)

        # Validate
        if not minute_data.empty:
            is_valid, errors = DataValidator.validate_ohlcv(minute_data)
            if is_valid:
                print(f"  ✅ Minute data: {len(minute_data)} candles - VALID")
            else:
                print(f"  ❌ Minute data: INVALID")
                for error in errors:
                    print(f"     - {error}")
        else:
            print(f"  ⚠️  No minute data found")

        if not daily_data.empty:
            is_valid, errors = DataValidator.validate_ohlcv(daily_data)
            if is_valid:
                print(f"  ✅ Daily data: {len(daily_data)} candles - VALID")
            else:
                print(f"  ❌ Daily data: INVALID")
                for error in errors:
                    print(f"     - {error}")
        else:
            print(f"  ⚠️  No daily data found")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='Production Intraday Stock Screener',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--config',
        type=str,
        default='config/screener_config.yaml',
        help='Path to configuration file'
    )

    parser.add_argument(
        '--log-level',
        type=str,
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level'
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Screen command
    screen_parser = subparsers.add_parser('screen', help='Run screening workflow')
    screen_parser.add_argument('--date', type=str, required=True, help='Trading date (YYYY-MM-DD)')
    screen_parser.add_argument(
        '--mode',
        type=str,
        choices=['premarket', 'live', 'full'],
        default='full',
        help='Screening mode'
    )
    screen_parser.add_argument('--capital', type=float, default=100000, help='Trading capital')
    screen_parser.add_argument('--output', type=str, help='Output file path (JSON)')

    # Backtest command
    backtest_parser = subparsers.add_parser('backtest', help='Run backtest')
    backtest_parser.add_argument('--start', type=str, required=True, help='Start date (YYYY-MM-DD)')
    backtest_parser.add_argument('--end', type=str, required=True, help='End date (YYYY-MM-DD)')
    backtest_parser.add_argument('--capital', type=float, default=100000, help='Initial capital')
    backtest_parser.add_argument('--output', type=str, help='Output file path (JSON)')

    # Validate data command
    validate_parser = subparsers.add_parser('validate-data', help='Validate data integrity')

    args = parser.parse_args()

    # Setup logging
    Path('logs').mkdir(exist_ok=True)
    setup_logging(args.log_level)

    # Load configuration
    config = load_config(args.config)

    # Route to appropriate command
    if args.command == 'screen':
        cmd_screen(args, config)
    elif args.command == 'backtest':
        cmd_backtest(args, config)
    elif args.command == 'validate-data':
        cmd_validate_data(args, config)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
