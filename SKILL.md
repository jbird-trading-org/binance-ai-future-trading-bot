---
name: neko-futures-trader
description: |
  Automated Binance Futures trading scanner with runner detection.
  Features:
  - Runner detection (volume spike + momentum + breakout)
  - Real crypto news via Brave Search
  - Auto SL/TP after position opens
  - Score-based signal ranking (0-10)
  - Post signals + execute trades to Telegram
  - Auto-start on install
  Use when user wants automated futures trading signals.
metadata:
  openclaw:
    emoji: 🐱📈
    requires:
      bins: ["python3"]
      env: ["BINANCE_API_KEY", "BINANCE_SECRET", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHANNEL", "BRAVE_API_KEY"]
    startup:
      command: "cd /root/.openclaw/workspace && nohup bash -c 'while true; do source binance-futures/.env && python3 scanner-v8.py; echo \"---\"; sleep 300; done' > scanner.log 2>&1 &"
      type: "background"
---

# Neko Futures Trader 🐱📈

Binance Futures automated scanner with runner detection and real news.

## Quick Start (Auto-Run)

### Option 1: One-Command Install + Run
```bash
# Install dependencies
pip install requests hmac hashlib

# Setup .env (see below)

# Auto-start scanner (runs every 5 min)
cd /root/.openclaw/workspace
nohup bash -c 'while true; do source binance-futures/.env && python3 scanner-v8.py; echo "---"; sleep 300; done' > scanner.log 2>&1 &
```

### Option 2: Manual Run
```bash
source .env
python3 scanner-v8.py
```

## Environment Setup

Create `.env` file:
```
BINANCE_API_KEY=your_binance_api_key
BINANCE_SECRET=your_binance_secret
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHANNEL=your_channel_id
BRAVE_API_KEY=your_brave_api_key
```

## Configuration

Edit `scanner-v8.py`:
```python
LEVERAGE = 10
MAX_POSITIONS = 8
ENTRY_PERCENT = 5
MIN_GAIN = 0.5
```

## Signal Template

```
🟢 LONG SIGNAL 🟢

📈 XANUSDT TECHNICAL ANALYSIS 📊
📊 Chart: https://www.tradingview.com/chart/?symbol=BINANCE:XANUSDT

📐 MULTI-TF CONFIRMATION:
• Trend 1H: BULLISH
• Structure: BREAKOUT
📊 24h Change: +47.0%

📐 INDICATORS:
• RSI (14): 72.5
• EMA 21: 0.007842
• EMA 50: 0.006521
• ATR: 0.000892

🔊 VOLUME: Volume Spike (12.8x)

📊 STRUCTURE:
• Support: 0.006200
• Resistance: 0.009500

🎯 RUNNER METRICS:
• 1H Momentum: +24.5%
• Volume Spike: 12.8x
• Breakout: ✅ Yes
• Score: 7/10 🚀

💡 INSIGHT: BREAKOUT | Strong momentum
🎯 Entry: $0.008950
📈 TP: $0.011600
🛡 SL: $0.007800

📰 Latest News: ...

✅ ORDER EXECUTED: LONG
🛡 SL: $0.007800
📈 TP: $0.011600
📋 Order ID: 123456789 | Status: NEW
```

## Runner Detection Criteria

| Criteria | Weight |
|----------|--------|
| Volume Spike 3x+ | +2 pts |
| Volume Spike 2x+ | +1 pt |
| 24h Change 10%+ | +2 pts |
| 24h Change 5%+ | +1 pt |
| 1H Momentum 3%+ | +1 pt |
| Breakout (new high) | +2 pts |

**Min Score: 3/10** to trigger

## Commands

| Action | Command |
|--------|---------|
| Start Scanner | `python3 scanner-v8.py` |
| Background | `nohup python3 scanner-v8.py &` |
| Check Log | `tail -f scanner.log` |
| Check Positions | `python3 -c "import requests,hmac,hashlib,time; ..."` |

## Files

- `scanner-v8.py` - Main scanner
- `position-monitor.py` - Position watcher
- `README.md` - Full docs

## Safety

⚠️ Monitor positions. Understand leveraged trading risks.

---
*Skill by Neko Sentinel* 🐱🛡️
