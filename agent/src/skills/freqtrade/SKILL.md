---
name: freqtrade
category: execution
description: Live crypto trading execution via Freqtrade API. Bridges Vibe-Trading AI strategies to real exchange execution on Binance, Bybit, OKX, and 100+ exchanges.
version: 0.1.0
requires:
  - freqtrade>=2024.0
  - httpx>=0.25.0
  - pydantic>=2.0.0
---

## Overview

This skill integrates **Freqtrade** — the leading open-source crypto trading bot — into Vibe-Trading's AI-powered trading workflow.

**What it does:**
- Executes AI-generated strategies on real exchanges
- Provides real-time position monitoring
- Manages risk and position sizing
- Supports paper trading and live trading modes

**Supported exchanges:** Binance, Bybit, OKX, Coinbase, Kraken, Gate, and 100+ via CCXT

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 Vibe-Trading AI Agent                        │
│                                                              │
│  Strategy: "RSI < 30 + MACD crossover on BTC/USDT"         │
│                      ↓                                       │
│              Strategy Generator                              │
│                      ↓                                       │
│  ┌────────────────────────────────────────────────────┐    │
│  │            FREQTRADE SKILL                          │    │
│  │                                                      │    │
│  │  StrategyConverter → FreqtradeStrategy              │    │
│  │  FreqtradeAdapter → REST API                        │    │
│  │  RiskManager → Position limits                      │    │
│  └────────────────────────────────────────────────────┘    │
│                      ↓                                       │
│              Freqtrade Bot (Docker)                          │
│                      ↓                                       │
│              Exchange API (Binance/etc)                      │
└─────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### 1. Start Freqtrade

```bash
# Using Docker
docker run -d --name freqtrade \
  -p 8080:8080 \
  -v $(pwd)/freqtrade_data:/freqtrade/user_data \
  freqtradeorg/freqtrade:stable \
  trade \
  --config /freqtrade/user_data/config.json \
  --strategy SampleStrategy

# Or with docker-compose
docker-compose up -d freqtrade
```

### 2. Configure API Keys

Edit `freqtrade_data/user_data/config.json`:

```json
{
  "api_key": "YOUR_BINANCE_API_KEY",
  "api_secret": "YOUR_BINANCE_SECRET",
  "exchange": {
    "name": "binance",
    "key": "YOUR_KEY",
    "secret": "YOUR_SECRET"
  },
  "pairlists": [
    {"method": "StaticPairList"}
  ],
  "dry_run": true
}
```

### 3. Use in Vibe-Trading

```python
from agent.src.freqtrade import FreqtradeAdapter

# Initialize adapter
adapter = FreqtradeAdapter(
    api_url="http://localhost:8080",
    api_key="your_freqtrade_api_key"
)

# Check connection
if adapter.is_connected:
    print("✅ Connected to Freqtrade")
    
    # Get account info
    info = adapter.get_account_info()
    print(f"Balance: ${info['balance']['total']}")
    
    # Start trading
    adapter.start_trading()
```

---

## Core Functions

### Connection & Status

| Function | Description |
|----------|-------------|
| `is_connected` | Check if Freqtrade API is accessible |
| `is_trading` | Check if bot is currently running |
| `trading_mode` | Get "paper" or "live" mode |
| `health_check()` | Full system health check |

### Account Management

| Function | Description |
|----------|-------------|
| `get_balance()` | Get account balance |
| `get_available_balance()` | Get free (available) balance |
| `get_account_info()` | Full account summary |

### Position Management

| Function | Description |
|----------|-------------|
| `get_positions()` | List all open positions |
| `get_position(pair)` | Get position for specific pair |
| `get_trade_history(limit)` | Historical trades |

### Bot Control

| Function | Description |
|----------|-------------|
| `start_trading()` | Start the trading bot |
| `stop_trading()` | Stop the trading bot |
| `emergency_stop(reason)` | Immediate stop + no new trades |
| `switch_strategy(name)` | Change active strategy |

### Strategy Deployment

| Function | Description |
|----------|-------------|
| `get_available_strategies()` | List strategies in Freqtrade |
| `convert_and_deploy(strategy)` | Convert Vibe-Trading → Freqtrade → deploy |
| `deploy_strategy(freq_strategy)` | Deploy FreqtradeStrategy object |

### Risk Management

| Function | Description |
|----------|-------------|
| `get_risk_metrics()` | Calculate exposure, drawdown risk |
| `check_risk_limits()` | Validate against configured limits |
| `get_trading_pairs()` | Current whitelist |
| `block_pair(pair)` | Add pair to blacklist |

---

## Example Workflow

### Generate and Deploy Strategy

```python
from agent.src.freqtrade import FreqtradeAdapter, FreqtradeStrategy

# Initialize
adapter = FreqtradeAdapter()

# Strategy from Vibe-Trading AI (example)
vibe_strategy = {
    "name": "RSI_Bounce_Strategy",
    "description": "Buy when RSI oversold, sell when overbought",
    "timeframe": "1h",
    "indicators": [
        {"name": "rsi", "formula": "RSI > 70", "buy_signal": False, "sell_signal": True},
        {"name": "rsi", "formula": "RSI < 30", "buy_signal": True, "sell_signal": False}
    ],
    "risk_management": {
        "max_loss": -0.05,  # 5% stoploss
        "trailing_stop": True,
        "take_profit": 0.03  # 3% profit target
    }
}

# Convert and deploy
result = adapter.convert_and_deploy(vibe_strategy)
print(f"Deployed: {result['status']}")

# Start trading
adapter.start_trading()

# Monitor
positions = adapter.get_positions()
print(f"Open positions: {len(positions)}")
```

### Monitor Live Trading

```python
# Get real-time summary
print(adapter.get_summary())

# Check risk
risk = adapter.check_risk_limits()
if not risk['passed']:
    print("⚠️ Risk violations:")
    for v in risk['violations']:
        print(f"  - {v}")

# Emergency stop if needed
if risk['max_drawdown_risk'] == 'high':
    adapter.emergency_stop("Risk limit exceeded")
```

---

## Strategy Conversion

The converter automatically transforms Vibe-Trading strategies:

| Vibe-Trading | Freqtrade |
|--------------|------------|
| `RSI > 70` | `ta.RSI(close, period=14) > 70` |
| `SMA 50` | `ta.SMA(close, timeperiod=50)` |
| `EMA 200` | `ta.EMA(close, timeperiod=200)` |
| `MACD crossover` | MACD signal logic |
| Custom formulas | Python expressions |

---

## Configuration

### Environment Variables

```bash
# Freqtrade connection
FREQTRADE_URL=http://localhost:8080
FREQTRADE_API_KEY=your_api_key_here

# Default settings
FREQTRADE_EXCHANGE=binance
FREQTRADE_STAKE_CURRENCY=USDT
FREQTRADE_MAX_TRADES=3
FREQTRADE_DRY_RUN=true
```

### Risk Limits

```python
config = FreqtradeConfig(
    max_open_trades=3,
    stoploss=-0.05,
    trailing_stop=True,
    dry_run=True  # Paper trading by default
)
```

---

## Error Handling

```python
from agent.src.freqtrade import (
    FreqtradeAdapter,
    ConnectionError,
    TradingError,
    StrategyError
)

try:
    adapter = FreqtradeAdapter()
    
    if not adapter.is_connected:
        raise ConnectionError("Cannot reach Freqtrade API")
    
    # ... trading operations
    
except ConnectionError as e:
    print(f"Connection issue: {e}")
    # Check if Freqtrade is running
    
except TradingError as e:
    print(f"Trading error: {e}")
    # Handle failed orders, insufficient balance, etc.
    
except StrategyError as e:
    print(f"Strategy error: {e}")
    # Fix strategy issues
```

---

## Safety Features

### Auto-Protections

1. **Risk limit checks** before any trade
2. **Position size limits** (configurable)
3. **Max drawdown alerts** 
4. **Emergency stop** for critical situations

### Best Practices

```python
# Always check risk limits
risk = adapter.check_risk_limits()
if not risk['passed']:
    print("Trading paused due to risk limits")
    # Review violations before continuing

# Use paper trading first
adapter = FreqtradeAdapter()
status = adapter.client.get_status()
if status.dry_run:
    print("Running in PAPER mode - no real money")

# Monitor positions
for pos in adapter.get_positions():
    pnl = pos.pnl_pct or 0
    if pnl < -5:  # -5% loss
        print(f"⚠️ Large loss on {pos.pair}: {pnl}%")
```

---

## Requirements

```bash
pip install freqtrade>=2024.0 httpx>=0.25.0 pydantic>=2.0.0
```

Or install via project:

```bash
cd Vibe-Trading
pip install -e ".[freqtrade]"
```

---

## Resources

- **Freqtrade Docs:** https://www.freqtrade.io/en/stable/
- **Freqtrade API:** https://www.freqtrade.io/en/stable/rest-api/
- **CCXT Library:** https://github.com/ccxt/ccxt
- **Docker Setup:** https://www.freqtrade.io/en/stable/docker/
