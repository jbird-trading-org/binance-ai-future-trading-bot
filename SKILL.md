---
name: neko-futures-trader
description: |
  Automated Binance Futures trading with professional-grade framework. Features:
  - Multi-timeframe confirmation (1H + 4H)
  - Market structure analysis (HH/HL/LH/LL)
  - ATR-based dynamic stop loss
  - Fibonacci extension targets
  - EMA trend filtering (EMA-21/50/200)
  - RSI momentum filter
  - Auto-execute + post to Telegram
  - Quick rescan when positions close
  Use when user wants automated futures trading signals or bot trading.
metadata:
  openclaw:
    emoji: 🐱📈
    requires:
      bins: ["python3"]
      env: ["BINANCE_API_KEY", "BINANCE_SECRET", "TELEGRAM_BOT_TOKEN"]
---

# Neko Futures Trader 🐱📈

Professional Binance Futures trading automation with multi-timeframe analysis.

## Setup

### Prerequisites
```bash
pip install requests hmac hashlib
```

### Environment Variables
Create `.env` file:
```
BINANCE_API_KEY=your_api_key
BINANCE_SECRET=your_secret
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHANNEL=-1003847994290
```

## Configuration

Edit scanner variables at top of `scanner.py`:
```python
LEVERAGE = 10
MAX_POSITIONS = 8
MAX_MARGIN_PERCENT = 40
ENTRY_PERCENT = 5
TEST_MODE = False  # Set True for paper trading
```

## Trading Framework

### Entry Rules
1. **Multi-TF Confirmation** — 1H and 4H trends must align
2. **Market Structure** — Price must show HH/HL (uptrend) or LH/LL (downtrend)
3. **EMA Trend** — Price above EMA-200 = uptrend, below = downtrend
4. **Entry Zones:**
   - **Support Bounce** — Price within 3% of support (LONG)
   - **Breakout** — Price within 5% of resistance (LONG)
   - **Resistance Rejection** — Price within 3% of resistance (SHORT)
   - **Breakdown** — Price within 5% of support (SHORT)

### Stop Loss
- **Breakout Entry:** Below EMA-21 OR 1.5x ATR below entry
- **Support Bounce Entry:** Below support OR 1.5x ATR below entry
- ATR-based for dynamic adjustment

### Take Profit
- **TP1:** Entry + (range × 1.272) — Fibonacci extension
- **TP2:** Entry + (range × 1.618) — Fibonacci extension

### Indicators
| Indicator | Purpose |
|-----------|---------|
| EMA 200 | Trend direction |
| EMA 50 | Mid-term trend |
| EMA 21 | Short-term momentum |
| RSI (14) | Momentum filter |
| ATR (14) | Dynamic SL calculation |
| Structure | HH/HL or LH/LL detection |

## Running

### Start Scanner
```bash
source .env
python3 scanner.py
```

### Run in Background
```bash
nohup python3 scanner.py > scanner.log 2>&1 &
```

### Position Monitor (Auto-rescan)
```bash
python3 position-monitor.py
```
Monitors positions and triggers quick scan when positions close.

## Files

- `scanner.py` — Main scanner + auto-trade
- `position-monitor.py` — Position watcher + auto-rescan
- `SKILL.md` — This file
- `scripts/check_balance.py` — Check account balance
- `scripts/check_positions.py` — List open positions

## Safety

⚠️ **Always use TEST_MODE first!**

```python
TEST_MODE = True  # Paper trading
TEST_MODE = False  # Real money
```

---
*Skill by Neko Sentinel* 🐱🛡️
