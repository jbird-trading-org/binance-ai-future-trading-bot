# Neko Futures Trader 🐱📈

Automated Binance Futures trading bot with professional-grade technical analysis.

## Features

### Trading Strategies
- **Momentum Strategy** - Ride hot coins (2-20% daily movers)
- **Technical Strategy** - Multi-timeframe analysis with indicators

### Technical Indicators
| Category | Indicators |
|----------|------------|
| Trend | EMA 21/50/200 (1H + 4H) |
| Momentum | RSI (14), Stochastic, MACD |
| Volatility | ATR, Bollinger Bands |
| Volume | Volume Spike, OBV, VWAP |
| Strength | ADX, Williams %R, CCI |

### Chart Patterns
- Engulfing (Bullish/Bearish)
- Pin Bar (Bullish/Bearish)
- Inside Bar
- Morning/Evening Star
- Doji

### Market Structure
- Higher Highs/Lower Lows (HH/HL)
- Breakout/Breakdown Detection
- Double Top/Bottom
- Ascending/Descending Triangle
- Wedge & Channel

### Risk Management
- Auto Take Profit (Fib 1.272/1.618)
- Auto Stop Loss (ATR-based)
- Max Positions Limit
- Margin Usage Protection

---

## Installation

### Prerequisites
```bash
- Python 3.8+
- Binance Futures Account
- Telegram Bot (for notifications)
```

### Step 1: Clone Repository
```bash
git clone https://github.com/lukmanc405/neko-futures-trader.git
cd neko-futures-trader
```

### Step 2: Install Dependencies
```bash
pip install requests hmac hashlib
```

### Step 3: Configure Environment
```bash
cp .env.example .env
nano .env
```

Edit `.env` file:
```env
BINANCE_API_KEY=your_binance_api_key
BINANCE_SECRET=your_binance_secret
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHANNEL=your_channel_id
```

### Step 4: Run Scanner

**Manual Run:**
```bash
source .env
python3 scanner.py
```

**Background Run:**
```bash
nohup python3 scanner.py > scanner.log 2>&1 &
```

**With Auto-Restart:**
```bash
while true; do
    source .env
    python3 scanner.py
    echo "Restarting in 5 minutes..."
    sleep 300
done
```

---

## Configuration

### Trading Parameters (Edit in scanner.py)
```python
# Trading Config
LEVERAGE = 10
MAX_POSITIONS = 8
MAX_MARGIN_PERCENT = 40
ENTRY_PERCENT = 5

# Momentum Strategy
USE_MOMENTUM = True
MOMENTUM_MIN_GAIN = 2.0
MOMENTUM_MAX_GAIN = 20.0

# Technical Strategy
USE_TECHNICAL = True
TECH_MIN_GAIN = 0.5
```

---

## Signal Template

```
🟢 LONG SIGNAL 🟢

📈 BTCUSDT TECHNICAL ANALYSIS 📊
📊 Chart: https://www.tradingview.com/chart/?symbol=BINANCE:BTCUSDT

📐 MULTI-TF CONFIRMATION:
• Trend 1H: BULLISH
• Trend 4H: BULLISH
• Structure 1H: UPTREND (BREAKOUT)
• Structure 4H: UPTREND
📊 24h Change: 3.45%

📐 INDICATORS:
• RSI (14): 28.5 | Stoch K: 22.3 | Williams %R: -75.2
• EMA 21: 67234.56 | EMA 50: 66890.12 | EMA 200: 65123.45
• MACD: 1234.5 | Signal: 987.6 | Hist: +246.9
• Bollinger: Upper 72000 | Middle 68500 | Lower 65000
• ADX: 42.5 (Strong Trend)

🔊 VOLUME: VOLUME_SPIKE, OBV_UP
🕯 PATTERNS: BULLISH_ENGULFING

📊 STRUCTURE:
• Support: 65000.00
• Resistance: 72000.00

💡 INSIGHT: Bullish | Breakout | RSI Oversold | 4H Aligned
🎯 Entry: $71000.00
📈 TP1: $79896.00 (Fib 1.272)
📈 TP2: $83284.00 (Fib 1.618)
🛡 SL: $68500.00
⏰ Timeframe: 1H

✅ ORDER EXECUTED: LONG
📋 Order ID: 123456789 | Status: NEW
```

---

## Usage Modes

### Mode 1: Signal Only (No Auto-Trade)
Posts signals to Telegram. You execute manually.

### Mode 2: Auto-Trade (Copy Trade)
Posts signal AND automatically executes trade on Binance.

Edit scanner.py to enable:
```python
# For manual trading only - set TEST_MODE = True
# For live trading - set TEST_MODE = False
```

---

## Monitoring

### Check Balance
```bash
python3 -c "
import requests, hmac, hashlib, time
API_KEY = 'your_key'
SECRET = 'your_secret'
ts = int(time.time() * 1000)
params = f'timestamp={ts}'
sig = hmac.new(SECRET.encode(), params.encode(), hashlib.sha256).hexdigest()
r = requests.get(f'https://fapi.binance.com/fapi/v3/account?{params}&signature={sig}', headers={'X-MBX-APIKEY': API_KEY})
print(r.json())
"
```

### Check Scanner Logs
```bash
tail -f scanner.log
```

---

## Safety

⚠️ **Important:**

1. **Start with TEST_MODE = True** to test without real money
2. **Never commit .env** to GitHub (already in .gitignore)
3. **Monitor positions** regularly
4. **Understand the risks** of leveraged trading

---

## Troubleshooting

### Scanner Not Running
```bash
ps aux | grep scanner.py
# If not running:
nohup python3 scanner.py > scanner.log 2>&1 &
```

### No Signals Found
- Check market conditions
- Adjust MIN_GAIN parameters
- Ensure API keys are correct

### Order Failed
- Check balance
- Verify API permissions
- Check precision requirements

---

## Files

| File | Description |
|------|-------------|
| `scanner.py` | Main trading scanner |
| `SKILL.md` | OpenClaw skill definition |
| `.env.example` | Environment template |
| `LICENSE` | MIT License |

---

## License

MIT License - See LICENSE file

---

## Support

- Telegram: @NekoSentinelBot
- GitHub: https://github.com/lukmanc405/neko-futures-trader

---

*Built by Neko Sentinel 🐱🛡️*
