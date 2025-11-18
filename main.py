#!/usr/bin/env python3
"""
Intraday Stock Screener - Main Application
Complete screening and trading system for Indian stocks
"""

import argparse
import sys
from datetime import datetime

from src.pre_market_screener import PreMarketScreener
from src.live_market_filter import LiveMarketFilter
from src.trading_strategy import TradingStrategy
from src.risk_manager import RiskManager
from src.ml_predictor import MLPredictor
from config.config import TRADING_CONFIG, NIFTY_50_STOCKS


def print_header():
    """Print application header"""
    print("\n" + "="*60)
    print("  📈 INTRADAY STOCK SCREENER & TRADING SYSTEM 📈")
    print("="*60)
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60 + "\n")


def print_trading_plan(plans: list, risk_manager: RiskManager, capital: float):
    """Print detailed trading plans"""
    if not plans:
        print("\n⚠️  No trading setups found!")
        return

    print("\n" + "="*60)
    print("📋 DETAILED TRADING PLANS")
    print("="*60)

    for i, plan in enumerate(plans, 1):
        print(f"\n{i}. {plan['symbol']} - {plan['setup_type']} SETUP")
        print("-" * 60)

        print(f"\n   Setup Quality: {plan['setup_quality']:.0f}/100")
        print(f"   Reversal Pattern: {plan['reversal_pattern']}")

        print(f"\n   Entry Details:")
        print(f"      Entry Price: ₹{plan['entry_price']:.2f}")
        print(f"      Stop Loss: ₹{plan['stop_loss']:.2f}")
        print(f"      Target: ₹{plan['target']:.2f}")
        print(f"      Risk:Reward = 1:{plan['risk_reward_ratio']:.1f}")

        print(f"\n   Technical Levels:")
        print(f"      20 EMA: ₹{plan['technical_levels']['ema_20']:.2f}")
        print(f"      200 EMA: ₹{plan['technical_levels']['ema_200']:.2f}")
        print(f"      VWAP: ₹{plan['technical_levels']['vwap']:.2f}")

        print(f"\n   Market Data:")
        print(f"      ATR: ₹{plan['atr']:.2f}")
        print(f"      Volume Surge: {plan['volume_surge']:.2f}x")
        if 'gap_pct' in plan:
            print(f"      Gap: {plan['gap_pct']:+.2f}%")

        # Calculate position sizing
        validation = risk_manager.validate_trade_plan(plan, capital)

        if validation['valid']:
            print(f"\n   Position Sizing (Capital: ₹{capital:,.0f}):")
            print(f"      Quantity: {validation['quantity']} shares")
            print(f"      Position Value: ₹{validation['position_value']:,.2f}")
            print(f"      Risk Amount: ₹{validation['risk_amount']:,.2f} ({validation['risk_pct']:.1f}%)")
            print(f"      Potential Profit: ₹{validation['potential_profit']:,.2f}")

            print(f"\n   ✅ TRADE APPROVED")
        else:
            print(f"\n   ❌ TRADE REJECTED: {validation['reason']}")

        if 'ml_prediction' in plan and plan['ml_prediction']:
            print(f"\n   ML Prediction:")
            print(f"      Direction: {plan['ml_prediction'].upper()}")
            print(f"      Probability: {plan['ml_probability']:.1%}")
            print(f"      Confidence: {plan['ml_confidence']:.1%}")
            print(f"      ML Score: {plan.get('ml_score', 0):.0f}/100")


def run_pre_market_screening():
    """Run pre-market screening (8:45 - 9:15 AM)"""
    print("\n🔍 Starting Pre-Market Screening...")

    screener = PreMarketScreener()
    candidates = screener.run_screening()

    return candidates


def run_live_market_filtering(candidates: list):
    """Run live market filtering (After 9:20 AM)"""
    print("\n📊 Starting Live Market Filtering...")

    filter = LiveMarketFilter()
    final_candidates = filter.run_filtering(candidates)

    return final_candidates


def run_strategy_analysis(candidates: list, use_ml: bool = False):
    """Run trading strategy analysis"""
    print("\n🎯 Analyzing Trading Setups...")

    strategy = TradingStrategy()
    trading_plans = strategy.scan_for_setups(candidates)

    # Apply ML ranking if enabled
    if use_ml and trading_plans:
        ml_predictor = MLPredictor()
        trading_plans = ml_predictor.rank_candidates(trading_plans)

    return trading_plans


def main():
    """Main application entry point"""
    parser = argparse.ArgumentParser(
        description='Intraday Stock Screener for Indian Markets',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full screening workflow
  python main.py --mode full --capital 100000

  # Pre-market screening only
  python main.py --mode premarket

  # Live market filtering (requires pre-market data)
  python main.py --mode live --capital 100000

  # Train ML model
  python main.py --mode train-ml

  # Full screening with ML predictions
  python main.py --mode full --capital 100000 --use-ml
        """
    )

    parser.add_argument(
        '--mode',
        type=str,
        choices=['premarket', 'live', 'full', 'train-ml'],
        default='full',
        help='Screening mode (default: full)'
    )

    parser.add_argument(
        '--capital',
        type=float,
        default=100000,
        help='Trading capital in INR (default: 100000)'
    )

    parser.add_argument(
        '--use-ml',
        action='store_true',
        help='Use ML predictions for ranking (requires trained model)'
    )

    args = parser.parse_args()

    # Print header
    print_header()

    try:
        if args.mode == 'train-ml':
            # Train ML model
            print("🤖 Training ML Model on Nifty 50 stocks...\n")
            ml_predictor = MLPredictor()
            ml_predictor.train_model(NIFTY_50_STOCKS, period='6mo')

        elif args.mode == 'premarket':
            # Pre-market screening only
            candidates = run_pre_market_screening()

            if candidates:
                print(f"\n✓ Pre-market screening complete. Found {len(candidates)} candidates.")
                print("Run with --mode live to continue filtering.")

        elif args.mode == 'live':
            # Live market filtering (assumes you have candidates)
            print("⚠️  Note: Running live mode requires pre-market candidates.")
            print("For full workflow, use --mode full\n")

            # For demo, run pre-market first
            candidates = run_pre_market_screening()

            if candidates:
                final_candidates = run_live_market_filtering(candidates)

                if final_candidates:
                    # Initialize risk manager
                    risk_manager = RiskManager(capital=args.capital)

                    # Run strategy analysis
                    trading_plans = run_strategy_analysis(final_candidates, use_ml=args.use_ml)

                    # Print trading plans
                    print_trading_plan(trading_plans, risk_manager, args.capital)

                    # Print risk summary
                    risk_manager.print_summary()

        elif args.mode == 'full':
            # Full workflow: Pre-market -> Live -> Strategy
            print("🚀 Running Full Screening Workflow\n")

            # Step 1: Pre-market screening
            candidates = run_pre_market_screening()

            if not candidates:
                print("\n❌ No candidates found in pre-market screening. Exiting.")
                return

            # Step 2: Live market filtering
            final_candidates = run_live_market_filtering(candidates)

            if not final_candidates:
                print("\n❌ No candidates passed live market filtering. Exiting.")
                return

            # Step 3: Trading strategy analysis
            trading_plans = run_strategy_analysis(final_candidates, use_ml=args.use_ml)

            if not trading_plans:
                print("\n❌ No trading setups found. Exiting.")
                return

            # Initialize risk manager
            risk_manager = RiskManager(capital=args.capital)

            # Step 4: Print detailed trading plans
            print_trading_plan(trading_plans, risk_manager, args.capital)

            # Print risk summary
            risk_manager.print_summary()

            # Final recommendations
            print("\n" + "="*60)
            print("🎯 FINAL RECOMMENDATIONS")
            print("="*60)

            approved_plans = []
            for plan in trading_plans:
                validation = risk_manager.validate_trade_plan(plan, args.capital)
                if validation['valid']:
                    approved_plans.append(plan)

            if approved_plans:
                print(f"\n✓ {len(approved_plans)} trade(s) approved for execution:")
                for i, plan in enumerate(approved_plans, 1):
                    print(f"\n{i}. {plan['symbol']} - {plan['setup_type']}")
                    print(f"   Entry: ₹{plan['entry_price']:.2f} | SL: ₹{plan['stop_loss']:.2f} | Target: ₹{plan['target']:.2f}")
                    validation = risk_manager.validate_trade_plan(plan, args.capital)
                    print(f"   Quantity: {validation['quantity']} shares | Risk: ₹{validation['risk_amount']:,.2f}")

                print("\n📝 Remember:")
                print("   - Maximum 3 trades per day")
                print("   - Risk 1% per trade")
                print("   - Stop trading after 2 consecutive losses")
                print("   - Always use stop-loss orders")
            else:
                print("\n⚠️  No trades approved. Check risk parameters.")

    except KeyboardInterrupt:
        print("\n\n⚠️  Screening interrupted by user.")
        sys.exit(0)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("\n" + "="*60)
    print("✅ Screening Complete!")
    print("="*60 + "\n")


if __name__ == '__main__':
    main()
