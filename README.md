# Neko Futures Trader 🐱📈

Automated Binance Futures trading bot with runner detection and price monitor.

## Overview

This is a complete trading system for Binance Futures that:
- 🔍 Scans for runner signals (momentum + volume + breakout)
- 📰 Fetches real crypto news via Brave Search
- 🛡️ Uses Fibonacci+ATR based SL/TP
- 🔔 Auto-closes positions when SL/TP is hit
- 📱 Sends emoji-heavy Telegram alerts

## Prerequisites

```bash
- Python 3.8+
- Binance Futures account
- Telegram Bot
- Brave Search API key (optional, for news)
```

---

## Installation

### 1. Clone Repository

```bash
git clone https://github.com/lukmanc405/neko-futures-trader.git
cd neko-futures-trader
```

### 2. Install Dependencies

```bash
pip install requests hmac hashlib
```

### 3. Create Environment File

Create a `.env` file in the project root:

```bash
cp .env.example .env
nano .env
```

Add your credentials:

```env
BINANCE_API_KEY=your_binance_api_key
BINANCE_SECRET=your_binance_secret
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHANNEL=your_channel_id
BRAVE_API_KEY=your_brave_api_key
```

### 4. Get API Keys

**Binance API:**
1. Go to https://www.binance.com/en/futures
2. Account → API Management
3. Create new API key
4. Enable: Read, Spot & Margin Trading, Futures Trading
5. Set IP restriction to your server IP

**Telegram Bot:**
1. @BotFather on Telegram
2. /newbot
3. Get bot token

**Brave Search (optional):**
1. https://brave.com/search/api/
2. Get free API key

---

## Running the Scripts

### Option 1: Run Both Scripts

```bash
# Terminal 1: Scanner (finds signals every 5 min)
nohup python3 scanner-v8.py > scanner.log 2>&1 &

# Terminal 2: Price Monitor (auto-close every 60 sec)
nohup python3 price-monitor.py > price-monitor.log 2>&1 &
```

### Option 2: With Environment File

```bash
source .env
nohup python3 scanner-v8.py > scanner.log 2>&1 &
nohup python3 price-monitor.py > price-monitor.log 2>&1 &
```

### Option 3: Auto-Restart Loop

```bash
# Scanner - restarts every 5 minutes
nohup bash -c 'while true; do source .env && python3 scanner-v8.py; echo "---"; sleep 300; done' > scanner.log 2>&1 &

# Price Monitor - runs continuously
nohup bash -c 'while true; do source .env && python3 price-monitor.py; sleep 60; done' > price-monitor.log 2>&1 &
```

---

## Scripts

### scanner-v8.py

Main scanner that:
- Scans all USDT pairs for momentum runners
- Uses Brave Search for real crypto news
- Posts signals to Telegram
- Auto-executes trades (optional)

**Configuration:**

```python
LEVERAGE = 10           # 10x leverage
MAX_POSITIONS = 8       # Maximum open positions
ENTRY_PERCENT = 5       # 5% of margin per trade
MIN_GAIN = 0.5          # Minimum 24h change %
```

### price-monitor.py

Monitors open positions and auto-closes when SL/TP is hit:
- Checks every 60 seconds (configurable)
- Uses Fibonacci+ATR for SL/TP levels
- Sends emoji-heavy alerts to Telegram
- No algo orders needed - uses market orders

**Configuration:**

```python
CHECK_INTERVAL = 60  # Check every 60 seconds
```

---

## Fibonacci+ATR SL/TP System

The bot uses professional risk management:

| Level | Formula | Description |
|-------|---------|-------------|
| **SL** | Entry - 1.5×ATR | Stop Loss |
| **TP1** | Entry + 3×ATR | Take Profit 1 (Fib 1.272) |
| **TP2** | Entry + 4.5×ATR | Take Profit 2 (Fib 1.618) |

**Example:**
- Entry: $100
- ATR: $2
- SL: $97 (1.5×ATR)
- TP1: $106 (3×ATR)
- TP2: $109 (4.5×ATR)

---

## Telegram Alert Templates

### Signal Alert (from scanner)

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

### Profit Alert (from price monitor)

```
🎉💰 PROFIT TAKEN! 💰🎉

🟢 TIAUSDT LONG
📈 +5.02% ($5.02)
Entry: $0.364600 → Exit: $0.382940
Target: $0.390323 (TP1) 🎯

#TakeProfit #Winning #Crypto
```

### Stop Loss Alert (from price monitor)

```
❌ STOP HIT

🔴 AXSUSDT LONG
📈 -3.12% (-$3.50)
Entry: $1.237000 → Exit: $1.199000
Target: $1.199890 (SL) 🎯

#StopLoss #Trading #Crypto
```

---

## Runner Detection Criteria

The scanner finds momentum runners using these weights:

| Criteria | Weight | Must Have |
|----------|--------|-----------|
| Volume Spike 3x+ | +2 pts | Optional |
| Volume Spike 2x+ | +1 pt | Optional |
| 24h Change 10%+ | +2 pts | Yes |
| 24h Change 5%+ | +1 pt | Optional |
| 1H Momentum 3%+ | +1 pt | Optional |
| Breakout (new high) | +2 pts | Optional |

**Minimum Score: 3/10** to trigger a signal

---

## Files

| File | Description |
|------|-------------|
| `scanner-v8.py` | Main trading scanner |
| `price-monitor.py` | Auto-close monitor |
| `position-monitor.py` | Position watcher (legacy) |
| `.env.example` | Environment template |
| `README.md` | This file |
| `SKILL.md` | OpenClaw skill definition |

---

## Troubleshooting

### Scanner not running

```bash
# Check if process is running
ps aux | grep scanner-v8

# Start scanner
nohup python3 scanner-v8.py &
```

### No signals found

- Check market conditions (need momentum)
- Lower MIN_GAIN in scanner-v8.py
- Ensure API keys are correct

### Price monitor not closing positions

- Check API permissions
- Ensure Binance Futures trading is enabled
- Manual close may be needed

### Telegram not receiving messages

- Verify bot token
- Check channel ID
- Bot must be admin in channel

---

## Safety Warning

⚠️ **Important:**

1. Always use a test account first
2. Never risk more than you can afford
3. Monitor positions regularly
4. Understand leveraged trading risks
5. Keep API keys secure - never commit to git

---

## Support

- GitHub: https://github.com/lukmanc405/neko-futures-trader
- Telegram: @NekoSentinelBot

---

*Built by Neko Sentinel* 🐱🛡️
