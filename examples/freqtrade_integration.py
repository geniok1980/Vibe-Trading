#!/usr/bin/env python3
"""
Freqtrade Integration Example for Vibe-Trading

This script demonstrates how to use the Freqtrade adapter
to bridge Vibe-Trading AI strategies with live crypto trading.

Requirements:
- Freqtrade running at http://localhost:8080
- API key configured in Freqtrade

Usage:
    python examples/freqtrade_integration.py
"""

import os
import sys
from pathlib import Path

# Add agent/src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "agent" / "src"))

from freqtrade import FreqtradeAdapter, FreqtradeStrategy
from freqtrade.converter import StrategyConverter


def main():
    print("=" * 60)
    print("VIBE-TRADING + FREQTRADE INTEGRATION DEMO")
    print("=" * 60)
    
    # Configuration
    FREQTRADE_URL = os.getenv("FREQTRADE_URL", "http://localhost:8080")
    FREQTRADE_KEY = os.getenv("FREQTRADE_API_KEY", "your_api_key_here")
    
    print(f"\n📡 Connecting to Freqtrade at {FREQTRADE_URL}...")
    
    # Initialize adapter
    adapter = FreqtradeAdapter(
        api_url=FREQTRADE_URL,
        api_key=FREQTRADE_KEY
    )
    
    # ==========================================
    # 1. CONNECTION CHECK
    # ==========================================
    print("\n" + "-" * 40)
    print("1️⃣  CONNECTION CHECK")
    print("-" * 40)
    
    if adapter.is_connected:
        print("✅ Connected to Freqtrade!")
    else:
        print("❌ Cannot connect to Freqtrade")
        print("   Make sure Freqtrade is running:")
        print("   docker run -d --name freqtrade -p 8080:8080 \\")
        print("     -v $(pwd)/freqtrade_data:/freqtrade/user_data \\")
        print("     freqtradeorg/freqtrade:stable")
        return
    
    # ==========================================
    # 2. ACCOUNT INFO
    # ==========================================
    print("\n" + "-" * 40)
    print("2️⃣  ACCOUNT INFORMATION")
    print("-" * 40)
    
    try:
        info = adapter.get_account_info()
        print(f"Mode: {info.get('trading_mode', 'unknown').upper()}")
        print(f"Bot: {'🟢 Running' if info['bot_status']['is_running'] else '🔴 Stopped'}")
        print(f"Strategy: {info['bot_status']['strategy']}")
        print(f"\nBalance:")
        print(f"  Total: ${info['balance']['total']:.2f}")
        print(f"  Free:  ${info['balance']['free']:.2f}")
        print(f"  Used:  ${info['balance']['used']:.2f}")
        print(f"\nPositions: {info['open_trades_count']}")
    except Exception as e:
        print(f"Error getting account info: {e}")
    
    # ==========================================
    # 3. POSITIONS
    # ==========================================
    print("\n" + "-" * 40)
    print("3️⃣  OPEN POSITIONS")
    print("-" * 40)
    
    try:
        positions = adapter.get_positions()
        if positions:
            for pos in positions:
                pnl = pos.pnl_pct or 0
                emoji = "🟢" if pnl >= 0 else "🔴"
                print(f"  {emoji} {pos.pair}")
                print(f"     Amount: {pos.amount}")
                print(f"     Entry: ${pos.entry_price:.2f}")
                print(f"     P&L: {pnl:.2f}%")
        else:
            print("  No open positions")
    except Exception as e:
        print(f"Error getting positions: {e}")
    
    # ==========================================
    # 4. AVAILABLE STRATEGIES
    # ==========================================
    print("\n" + "-" * 40)
    print("4️⃣  AVAILABLE STRATEGIES")
    print("-" * 40)
    
    try:
        strategies = adapter.get_available_strategies()
        for i, s in enumerate(strategies[:10], 1):
            print(f"  {i}. {s}")
        if len(strategies) > 10:
            print(f"  ... and {len(strategies) - 10} more")
    except Exception as e:
        print(f"Error getting strategies: {e}")
    
    # ==========================================
    # 5. STRATEGY CONVERSION DEMO
    # ==========================================
    print("\n" + "-" * 40)
    print("5️⃣  STRATEGY CONVERSION DEMO")
    print("-" * 40)
    
    # Example Vibe-Trading strategy
    vibe_strategy = {
        "name": "RSI Bollinger Bounce",
        "description": "Buy RSI oversold + lower Bollinger band, sell at upper band",
        "timeframe": "1h",
        "indicators": [
            {"name": "rsi", "formula": "RSI < 30", "buy_signal": True, "sell_signal": False},
            {"name": "bb_lower", "formula": "close < bb_lower", "buy_signal": True, "sell_signal": False},
            {"name": "rsi", "formula": "RSI > 70", "buy_signal": False, "sell_signal": True},
            {"name": "bb_upper", "formula": "close > bb_upper", "buy_signal": False, "sell_signal": True},
        ],
        "risk_management": {
            "max_loss": -0.05,
            "trailing_stop": True,
            "take_profit": 0.025
        },
        "position_sizing": {
            "max_positions": 2,
            "fixed_amount": 100
        }
    }
    
    print("Vibe-Trading Strategy:")
    print(f"  Name: {vibe_strategy['name']}")
    print(f"  Indicators: {len(vibe_strategy['indicators'])}")
    print(f"  Stoploss: {vibe_strategy['risk_management']['max_loss']}")
    
    # Convert
    converter = StrategyConverter()
    freq_strategy = converter.convert(vibe_strategy)
    
    print("\nConverted to Freqtrade:")
    print(f"  Name: {freq_strategy.name}")
    print(f"  Timeframe: {freq_strategy.timeframe}")
    print(f"  Stoploss: {freq_strategy.stoploss}")
    print(f"  Minimal ROI: {freq_strategy.minimal_roi}")
    
    # Validate
    issues = converter.validate_strategy(freq_strategy)
    if issues:
        print(f"\n⚠️  Validation issues:")
        for issue in issues:
            print(f"    - {issue}")
    else:
        print("\n✅ Strategy validated!")
    
    # ==========================================
    # 6. DEPLOY STRATEGY
    # ==========================================
    print("\n" + "-" * 40)
    print("6️⃣  DEPLOY STRATEGY")
    print("-" * 40)
    
    try:
        result = adapter.deploy_strategy(freq_strategy)
        print(f"Status: {result['status']}")
        print(f"Deployed at: {result['deployed_at']}")
    except Exception as e:
        print(f"Error deploying strategy: {e}")
        print("(This is expected if Freqtrade doesn't have the strategy file)")
    
    # ==========================================
    # 7. RISK MANAGEMENT
    # ==========================================
    print("\n" + "-" * 40)
    print("7️⃣  RISK MANAGEMENT")
    print("-" * 40)
    
    try:
        risk = adapter.get_risk_metrics()
        print(f"Total Exposure: ${risk['total_exposure']:.2f}")
        print(f"Exposure %: {risk['exposure_percentage']:.1f}%")
        print(f"Drawdown Risk: {risk['max_drawdown_risk'].upper()}")
        print(f"Positions: {risk['positions_count']}")
        
        limits = adapter.check_risk_limits()
        if limits['passed']:
            print("\n✅ All risk limits OK")
        else:
            print("\n⚠️  Risk limit violations:")
            for v in limits['violations']:
                print(f"    - {v}")
    except Exception as e:
        print(f"Error checking risk: {e}")
    
    # ==========================================
    # 8. FULL SUMMARY
    # ==========================================
    print("\n" + "=" * 60)
    print("📊 FULL SUMMARY")
    print("=" * 60)
    
    print(adapter.get_summary())
    
    print("\n" + "=" * 60)
    print("DEMO COMPLETE")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Configure your exchange API keys in Freqtrade")
    print("2. Set dry_run=false for live trading")
    print("3. Use adapter.start_trading() to begin")
    print("4. Monitor with adapter.get_positions()")


if __name__ == "__main__":
    main()
