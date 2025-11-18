#!/usr/bin/env python3
"""
Data Fetching Diagnostic Tool
Run this to diagnose issues with fetching live NSE data
"""

import sys
from datetime import datetime
import pytz

# Import the enhanced data fetcher
from src.enhanced_data_fetcher import EnhancedDataFetcher, test_data_fetching

def check_market_status():
    """Check if market is currently open"""
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)

    print("\n" + "="*60)
    print("MARKET STATUS CHECK")
    print("="*60)
    print(f"\nCurrent Time (IST): {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"Day: {now.strftime('%A')}")

    # Check if weekend
    if now.weekday() >= 5:
        print(f"\n⚠️  Market is CLOSED (Weekend)")
        return False

    # Check market hours
    market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    pre_market_start = now.replace(hour=9, minute=0, second=0, microsecond=0)

    if now < pre_market_start:
        print(f"\n⚠️  Market is CLOSED (Before pre-market)")
        print(f"Market opens at: {market_open.strftime('%H:%M:%S')}")
        return False
    elif pre_market_start <= now < market_open:
        print(f"\n⏰ Pre-market Session")
        print(f"Market opens at: {market_open.strftime('%H:%M:%S')}")
        return False
    elif market_open <= now <= market_close:
        print(f"\n✓ Market is OPEN")
        print(f"Market closes at: {market_close.strftime('%H:%M:%S')}")
        return True
    else:
        print(f"\n⚠️  Market is CLOSED (After hours)")
        print(f"Market opens tomorrow at: {market_open.strftime('%H:%M:%S')}")
        return False


def quick_test():
    """Quick test of data fetching for a few stocks"""
    print("\n" + "="*60)
    print("QUICK DATA FETCH TEST")
    print("="*60)

    # Test with 3 popular stocks
    test_stocks = ['RELIANCE.NS', 'TCS.NS', 'INFY.NS']

    print(f"\nTesting with: {', '.join(test_stocks)}")
    print("This will check what data is available...\n")

    test_data_fetching(test_stocks)


def detailed_test(symbol: str):
    """Detailed test for a specific symbol"""
    fetcher = EnhancedDataFetcher()

    print(f"\n" + "="*60)
    print(f"DETAILED TEST FOR {symbol}")
    print("="*60)

    # Full diagnosis
    diagnosis = fetcher.diagnose_data_availability(symbol)

    # Try fetching with different intervals
    print("\nTrying to fetch data with different intervals...")

    for interval in ['1m', '5m', '15m', '30m', '1h']:
        print(f"\n  Testing {interval} interval:")
        data = fetcher.get_intraday_data_robust(symbol, interval=interval, verbose=True)
        if not data.empty:
            print(f"    ✓ Got {len(data)} candles")
            print(f"    Time range: {data.index[0]} to {data.index[-1]}")
        else:
            print(f"    ✗ No data available")


def main():
    """Main diagnostic function"""
    print("\n" + "🔍 " + "="*58 + " 🔍")
    print("     NSE STOCK DATA FETCHING DIAGNOSTIC TOOL")
    print("🔍 " + "="*58 + " 🔍\n")

    # Check market status
    is_open = check_market_status()

    if not is_open:
        print("\n" + "⚠️ " + "="*58 + " ⚠️")
        print("  IMPORTANT: Market is currently CLOSED")
        print("  Live intraday data will NOT be available")
        print("  Use --demo mode for testing with historical data")
        print("⚠️ " + "="*58 + " ⚠️\n")

    # Run quick test
    quick_test()

    # Offer detailed test
    print("\n" + "-"*60)
    response = input("\nDo you want to run a detailed test for a specific stock? (y/n): ")

    if response.lower() == 'y':
        symbol = input("Enter stock symbol (e.g., RELIANCE.NS): ").strip()
        if symbol:
            detailed_test(symbol)

    # Recommendations
    print("\n" + "="*60)
    print("RECOMMENDATIONS")
    print("="*60)

    if is_open:
        print("""
✓ Market is open - you can use live intraday data

Run the screener normally:
  python main.py --mode full --capital 100000

If you still get errors:
  1. Check your internet connection
  2. Try with --demo mode as fallback
  3. Wait a few minutes and try again (data might be delayed)
        """)
    else:
        print("""
⚠️  Market is closed - use demo mode for testing

Run the screener in demo mode:
  python main.py --mode full --capital 100000 --demo

Demo mode uses historical daily data and allows you to:
  - Test the system anytime
  - Learn the workflow
  - Backtest strategies
  - Verify configuration

For live trading:
  - Run during market hours (9:15 AM - 3:30 PM IST)
  - Best time: 9:30 AM - 3:00 PM IST
        """)

    print("\nFor more help, see TROUBLESHOOTING.md")
    print("="*60 + "\n")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Diagnostic interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error during diagnostic: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
