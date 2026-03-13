---
name: neko-futures-trader
description: |
  Automated Binance Futures trading with professional-grade framework. Features:
  - Multi-timeframe confirmation (1H + 4H)
  - Market structure analysis (HH/HL/LH/LL)
  - Volume analysis (spikes & drops)
  - Candlestick patterns (Engulfing, Pin Bar, Inside Bar)
  - ATR-based dynamic stop loss
  - Fibonacci extension targets
  - EMA trend filtering (EMA-21/50/200)
  - RSI momentum filter
  - S/R zone detection
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

Edit scanner variables:
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
3. **Volume Analysis** — Detects volume spikes for confirmation
4. **Candlestick Patterns** — Engulfing, Pin Bar, Inside Bar detection
5. **EMA Trend** — Price above EMA-200 = uptrend, below = downtrend

### Entry Zones
- **Support Bounce** — Price within 3% of support (LONG)
- **Breakout** — Price within 5% of resistance (LONG)
- **Resistance Rejection** — Price within 3% of resistance (SHORT)
- **Breakdown** — Price within 5% of support (SHORT)

### Stop Loss
- **ATR-based** — Dynamic 1.5x ATR below entry
- **Structure-based** — Below EMA-21 or support/resistance

### Take Profit
- **TP1:** Entry + (range × 1.272) — Fibonacci extension
- **TP2:** Entry + (range × 1.618) — Fibonacci extension

## Signal Template

```
🟢 LONG SIGNAL 🟢

📈 BTCUSDT TECHNICAL ANALYSIS 📊
📊 Chart: https://www.tradingview.com/chart/?symbol=BINANCE:BTCUSDT

📐 MULTI-TF CONFIRMATION:
• Trend 1H: BULLISH
• Trend 4H: BULLISH
• Structure: UPTREND

📐 INDICATORS:
• RSI (14): 45.2
• EMA 21: 67234.56
• EMA 50: 66890.12
• EMA 200: 65123.45
• ATR: 1234.56

🔊 VOLUME: ⚡ Volume Spike
🕯 PATTERNS: BULLISH_ENGULFING

📊 STRUCTURE:
• Support: 65000.00
• Resistance: 70000.00
• Range: 5000.00

💡 INSIGHT: LONG - Uptrend + Support Bounce + Volume Spike + Bullish Pattern. RSI: 45.2
🎯 Entry: $67500.00
📈 TP1: $73863.64 (Fib 1.272)
📈 TP2: $75618.18 (Fib 1.618)
🛡 SL: $65500.00 (ATR-based)
⏰ Timeframe: 1H
```

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

### Position Monitor
```bash
python3 position-monitor.py
```

## Files

- `scanner.py` — Main scanner + auto-trade
- `position-monitor.py` — Position watcher + auto-rescan
- `SKILL.md` — This file
- `.env.example` — Template

## Safety

⚠️ **Always use TEST_MODE first!**

```python
TEST_MODE = True  # Paper trading
TEST_MODE = False  # Real money
```

## Key Features

| Feature | Description |
|---------|-------------|
| Multi-TF | 1H + 4H alignment |
| Structure | HH/HL detection |
| Volume | Spike/drop detection |
| Patterns | Engulfing, Pin Bar |
| ATR SL | Dynamic stop loss |
| Fib TP | 1.272 / 1.618 extensions |

---
*Skill by Neko Sentinel* 🐱🛡️
