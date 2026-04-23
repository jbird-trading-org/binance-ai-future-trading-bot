# 🐱 Neko Futures Trader

Automated Binance Futures trading bot with advanced signal detection, risk management, and comprehensive backtesting.

**Emoji:** 🐱📈  
**Repository:** https://github.com/lukmanc405/neko-futures-trader  
**Dashboard:** `https://YOUR_IP:8443/neko-light.html`

---

## 📁 Structure

```
neko-futures-trader/
├── scanner.py                 # Main scanner (5min intervals)
├── price-monitor.py           # SL/TP monitor (1sec intervals)
├── position_command.py         # Position checker
├── dashboard_api.py            # Dashboard API server
├── emergency_close.py          # Emergency position closer
├── daily_eval.py               # Comprehensive daily evaluation
├── backtester.py              # Monte Carlo backtesting
├── config.py                  # Trading parameters
├── lib/                       # Helper modules
│   ├── signal_filter.py
│   ├── ict_indicators.py
│   ├── advanced_analysis.py
│   ├── delisting_monitor.py
│   └── error_handling.py
├── static/
│   └── neko-light.html        # Dashboard UI
├── scripts/
│   ├── dashboard_api.py       # API server
│   └── backtester.py         # Backtesting engine
├── README.md
└── SKILL.md
```

---

## 🚀 Quick Start

### 1. Install
```bash
git clone https://github.com/lukmanc405/neko-futures-trader.git /root/.openclaw/skills/neko-futures-trader
cd /root/.openclaw/skills/neko-futures-trader
```

### 2. Dependencies
```bash
pip install python-dotenv requests pandas numpy scipy scikit-learn
```

### 3. Configure (.env)
```bash
BINANCE_API_KEY=your_key
BINANCE_SECRET=your_secret
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHANNEL=your_user_id
```

### 4. Setup Workspace
```bash
mkdir -p /root/.openclaw/workspace/neko-futures-trader/{logs,data}
cp .env /root/.openclaw/workspace/neko-futures-trader/
```

### 5. Start Services
```bash
systemctl enable neko-scanner neko-monitor neko-dashboard
systemctl start neko-scanner neko-monitor neko-dashboard
```

---

## 📊 Commands

```bash
# Check positions
python3 position_command.py

# Daily evaluation (comprehensive)
python3 daily_eval.py

# Backtesting (Monte Carlo)
python3 backtester.py

# Emergency close all
python3 emergency_close.py

# View logs
tail -f /root/.openclaw/workspace/neko-futures-trader/logs/scanner.log
tail -f /root/.openclaw/workspace/neko-futures-trader/logs/pm.log
```

---

## 🌐 Dashboard

Access at: `https://YOUR_IP:8443/neko-light.html`

**Features:**
- Real-time positions, balance, PnL
- Win rate, closed PnL, avg win/loss
- Glassmorphism UI with particles
- Dark/Light theme toggle
- Responsive design

---

## 📈 Trading System

### Indicators (Signal Scoring)

| Indicator | Score | Description |
|-----------|-------|-------------|
| Volume Spike | +2 | >3x average volume |
| Price Change | +1 to +2 | >5% or >10% change |
| OI Change | +2 | >20% open interest change |
| Weekly Change | +1 to +2 | >5% or >20% weekly change |
| EMA Position | Filter | Price must be near/below 21EMA |

### Filters (Reject Signals)

| Filter | Condition | Action |
|--------|-----------|--------|
| RSI | LONG when RSI > 70 | Reject LONG |
| RSI | SHORT when RSI < 30 | Reject SHORT |
| MACD Histogram | Contradicts direction | Reject signal |
| Bollinger Squeeze | No squeeze + weak move | Reject (chop) |
| EMA Extended | Price too extended | Reject (chase) |

### Removed (Poor Accuracy)

- ❌ Breakout/Breakdown
- ❌ Pocket Pivot

---

## ⚙️ SL/TP System

**Percentage-based: R:R Ratio 1:3**

| Parameter | Value | Description |
|-----------|-------|-------------|
| SL | 5% | Stop Loss: -5% LONG, +5% SHORT |
| TP | 15% | Take Profit: +15% LONG, -15% SHORT |
| Ratio | 1:3 | Risk:Reward |

### Example
```
Entry: $100

SL = $100 × 0.95 = $95
TP = $100 × 1.15 = $115
Risk: $5 | Reward: $15 = 1:3 ratio ✅
```

---

## ⚙️ Trading Parameters

| Param | Default | Description |
|-------|---------|-------------|
| MAX_POSITIONS | 5 | Max open positions |
| MAX_MARGIN | 30% | Max margin usage |
| LEVERAGE | 10x | Leverage |
| MIN_SCORE | 3 | Signal threshold |

---

## 📊 Backtesting

Monte Carlo simulation for strategy validation:

```bash
python3 backtester.py
```

**Features:**
- Basic metrics (winrate, R:R, expectancy, drawdown)
- Monte Carlo simulation (5000+ iterations)
- Per-symbol analysis
- Kelly Criterion calculation
- JSON export

---

## 🐛 Bug Fixes Applied

- ✅ Algo order endpoint: `/fapi/v1/algoOrder`
- ✅ tickSize price rounding (no precision errors)
- ✅ `quantity=1` + `reduceOnly=true` (works reliably)
- ✅ Floating point precision in SL/TP
- ✅ Income history API for accurate winrate

---

## 🔧 Maintenance

```bash
# Restart services
systemctl restart neko-scanner neko-monitor neko-dashboard

# Check status
systemctl status neko-scanner neko-monitor neko-dashboard

# View logs
journalctl -u neko-scanner -f
journalctl -u neko-monitor -f
```

---

## 📜 License

MIT License - lukmanc405
