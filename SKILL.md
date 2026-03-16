---
name: neko-futures-trader
description: |
  Automated Binance Futures trading scanner with runner detection and price monitor.
  
  Features:
  - Runner detection (volume spike + momentum + breakout)
  - Real crypto news via Brave Search
  - Fibonacci+ATR based SL/TP
  - Price monitor (auto-close when SL/TP hit)
  - Emoji-heavy Telegram alerts
  - Score-based signal ranking (0-10)
  - Auto-execute trades
  
  Use when: user wants automated futures trading signals.
metadata:
  openclaw:
    emoji: 🐱📈
    requires:
      bins: ["python3"]
      env: 
        - BINANCE_API_KEY
        - BINANCE_SECRET
        - TELEGRAM_BOT_TOKEN
        - TELEGRAM_CHANNEL
        - BRAVE_API_KEY
    startup:
      command: "cd /root/.openclaw/workspace/neko-futures-trader && nohup bash -c 'while true; do source .env && python3 scanner-v8.py; echo \"---\"; sleep 300; done' > ../scanner.log 2>&1 &"
      type: "background"
---

# Neko Futures Trader 🐱📈

Complete Binance Futures automated trading system.

## Quick Setup

```bash
# 1. Clone
git clone https://github.com/lukmanc405/neko-futures-trader.git

# 2. Install
pip install requests hmac hashlib

# 3. Configure
cp .env.example .env
nano .env

# 4. Run
nohup python3 scanner-v8.py &
nohup python3 price-monitor.py &
```

## Environment Variables

Create `.env` file:

```bash
BINANCE_API_KEY=your_binance_api_key
BINANCE_SECRET=your_binance_secret
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHANNEL=your_channel_id
BRAVE_API_KEY=your_brave_api_key
```

## Scripts

### scanner-v8.py

Finds trading signals:
- Scans 500+ USDT pairs
- Runner detection (volume + momentum + breakout)
- Real news via Brave Search
- Posts to Telegram
- Auto-executes trades

```bash
nohup python3 scanner-v8.py > scanner.log 2>&1 &
```

### price-monitor.py

Monitors positions:
- Checks every 60 seconds
- Auto-closes when SL/TP hit
- Fibonacci+ATR based levels
- Emoji alerts to Telegram

```bash
nohup python3 price-monitor.py > price-monitor.log 2>&1 &
```

## Fibonacci+ATR SL/TP

| Level | Formula |
|-------|---------|
| SL | Entry - 1.5×ATR |
| TP1 | Entry + 3×ATR (Fib 1.272) |
| TP2 | Entry + 4.5×ATR (Fib 1.618) |

## Alert Templates

### Signal Alert

```
🟢 LONG SIGNAL 🟢

📈 BTCUSDT TECHNICAL ANALYSIS 📊
📊 Chart: https://www.tradingview.com/chart/?symbol=BINANCE:BTCUSDT

📐 MULTI-TF CONFIRMATION:
• Trend 1H: BULLISH
• Structure: BREAKOUT
📊 24h Change: +5.2%

📐 INDICATORS:
• RSI (14): 65.3
• EMA 21: 71234.56
• EMA 50: 70890.12
• ATR: 1234.56

🔊 VOLUME: Volume Spike (2.5x)

📊 STRUCTURE:
• Support: 70000.00
• Resistance: 72000.00

🎯 RUNNER METRICS:
• 1H Momentum: +3.2%
• Volume Spike: 2.5x
• Breakout: ✅ Yes
• Score: 7/10 🚀

💡 INSIGHT: LONG | BREAKOUT | RSI: 65.3
🎯 Entry: $71000.00
📈 TP: $74500.00
🛡 SL: $68000.00
⏰ Timeframe: 1H

📰 Bitcoin surges past $71K as...

✅ ORDER EXECUTED: LONG
📋 Order ID: 123456789 | Status: NEW
```

### Profit Alert

```
🎉💰 PROFIT TAKEN! 💰🎉

🟢 TIAUSDT LONG
📈 +5.02% ($5.02)
Entry: $0.364600 → Exit: $0.382940
Target: $0.390323 (TP1) 🎯

#TakeProfit #Winning #Crypto
```

### Stop Loss Alert

```
❌ STOP HIT

🔴 AXSUSDT LONG
📈 -3.12% (-$3.50)
Entry: $1.237000 → Exit: $1.199000
Target: $1.199890 (SL) 🎯

#StopLoss #Trading #Crypto
```

## Configuration

### scanner-v8.py

```python
LEVERAGE = 10           # 10x leverage
MAX_POSITIONS = 8       # Max open positions
ENTRY_PERCENT = 5       # % of margin per trade
MIN_GAIN = 0.5          # Min 24h change %
```

### price-monitor.py

```python
CHECK_INTERVAL = 60      # Seconds between checks
```

## Runner Detection

| Criteria | Weight |
|----------|--------|
| Volume Spike 3x+ | +2 |
| Volume Spike 2x+ | +1 |
| 24h Change 10%+ | +2 |
| 24h Change 5%+ | +1 |
| 1H Momentum 3%+ | +1 |
| Breakout | +2 |

Minimum: 3/10 to trigger

## Files

- `scanner-v8.py` - Main scanner
- `price-monitor.py` - Auto-close monitor
- `.env.example` - Template
- `README.md` - Full docs
- `SKILL.md` - This file

## Safety

⚠️ Trading futures involves substantial risk. Only trade with capital you can afford to lose. Monitor positions regularly.

---
*Skill by Neko Sentinel* 🐱🛡️
