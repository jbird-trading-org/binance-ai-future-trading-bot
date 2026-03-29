---
name: neko-futures-trader
description: Automated Binance Futures trading bot with scanning, SL/TP automation, and backtesting. Use when user mentions futures trading, crypto trading bot, Binance automated trading, or needs help with trading system setup/maintenance.
---

# 🐱 Neko Futures Trader

## Overview

Automated Binance Futures trading bot with advanced signal detection, risk management, and comprehensive backtesting capabilities.

**Emoji:** 🐱📈  
**Requires:** Python 3.8+, Binance Futures API, systemd

---

## When to Use

Trigger when user mentions:
- "futures trading" or "crypto bot"
- "Binance automated trading"
- "trading scanner" or "SL/TP automation"
- "backtesting" or "strategy validation"
- Dashboard setup/maintenance
- Signal indicator questions

---

## 📁 File Structure

```
neko-futures-trader/
├── scanner-v8.py              # Scanner (5min intervals)
├── price-monitor.py           # SL/TP monitor (1sec)
├── position_command.py        # Position checker
├── dashboard_api.py           # Dashboard API
├── emergency_close.py         # Emergency closer
├── daily_eval.py              # Daily evaluation
├── backtester.py              # Monte Carlo backtesting
├── config.py                 # Trading parameters
├── lib/                      # Helper modules
│   ├── signal_filter.py
│   ├── ict_indicators.py
│   ├── advanced_analysis.py
│   ├── delisting_monitor.py
│   └── error_handling.py
└── static/
    └── neko-light.html       # Dashboard UI
```

---

## 🚀 Setup

### 1. Install
```bash
git clone https://github.com/lukmanc405/neko-futures-trader.git \
  /root/.openclaw/skills/neko-futures-trader
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

### 4. Workspace Setup
```bash
mkdir -p /root/.openclaw/workspace/neko-futures-trader/{logs,data}
cp .env /root/.openclaw/workspace/neko-futures-trader/
```

---

## ⚙️ Systemd Services

### Scanner Service
```ini
[Unit]
Description=Neko Futures Scanner
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/.openclaw/workspace/neko-futures-trader
ExecStart=/usr/bin/python3 /root/.openclaw/skills/neko-futures-trader/scanner-v8.py
Restart=always
RestartSec=10
StandardOutput=append:/root/.openclaw/workspace/neko-futures-trader/logs/scanner.log
StandardError=append:/root/.openclaw/workspace/neko-futures-trader/logs/scanner.log

[Install]
WantedBy=multi-user.target
```

### Monitor Service
```ini
[Unit]
Description=Neko Futures Monitor
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/.openclaw/workspace/neko-futures-trader
ExecStart=/usr/bin/python3 /root/.openclaw/skills/neko-futures-trader/price-monitor.py
Restart=always
RestartSec=10
StandardOutput=append:/root/.openclaw/workspace/neko-futures-trader/logs/pm.log
StandardError=append:/root/.openclaw/workspace/neko-futures-trader/logs/pm.log

[Install]
WantedBy=multi-user.target
```

### Enable Services
```bash
systemctl daemon-reload
systemctl enable neko-scanner neko-monitor neko-dashboard
systemctl start neko-scanner neko-monitor neko-dashboard
```

---

## 📊 Commands

```bash
# Check positions
python3 position_command.py

# Daily evaluation
python3 daily_eval.py

# Backtesting (Monte Carlo)
python3 backtester.py

# Emergency close
python3 emergency_close.py

# Service management
systemctl status neko-scanner neko-monitor
systemctl restart neko-scanner
journalctl -u neko-scanner -f
```

---

## 🌐 Dashboard

Access at: `https://YOUR_IP:8443/neko-light.html`

### Features
- Real-time positions, balance, PnL
- Win rate & closed PnL (7-day history)
- Glassmorphism UI with particles
- Dark/Light theme toggle
- Sparkline charts
- Toast notifications
- Responsive design

---

## 📈 Indicators

### Active Indicators

| Indicator | Score | Description |
|-----------|-------|-------------|
| Volume Spike | +2 | >3x average volume |
| Price Change | +1 to +2 | >5% or >10% change |
| OI Change | +2 | >20% open interest change |
| Weekly Change | +1 to +2 | >5% or >20% weekly change |

### Filters (Reject Signals)

| Filter | Condition | Action |
|--------|-----------|--------|
| RSI | LONG when RSI > 70 | Reject LONG |
| RSI | SHORT when RSI < 30 | Reject SHORT |
| MACD Histogram | Contradicts direction | Reject |
| Bollinger Squeeze | No squeeze + weak move | Reject (chop) |
| EMA Extended | Price too extended | Reject (chase) |

### Removed (Poor Accuracy)

- ❌ Breakout/Breakdown
- ❌ Pocket Pivot

---

## ⚙️ Trading Parameters

| Param | Default | Description |
|-------|---------|-------------|
| MAX_POSITIONS | 5 | Max open positions |
| MAX_MARGIN | 30% | Max margin usage |
| LEVERAGE | 10x | Leverage |
| MIN_SCORE | 3 | Signal threshold |

### R:R Ratio 1:4

| Volatility | ATR Range | SL | TP |
|------------|-----------|-----|-----|
| HIGH | > 10% | 2x ATR | 8x ATR |
| NORMAL | 5-10% | 2x ATR | 8x ATR |
| LOW | < 5% | 1.5x ATR | 6x ATR |

---

## 🐛 Bug Fixes

1. **Algo API:** `/fapi/v1/algoOrder`
2. **Params:** `algoType=CONDITIONAL`, `quantity=1`, `reduceOnly=true`
3. **Precision:** Rounds to tickSize per symbol
4. **Floating point:** String formatting for SL/TP prices
5. **Income API:** Use `/fapi/v1/income` for accurate winrate

---

## metadata

```yaml
metadata:
  openclaw:
    emoji: 🐱📈
    requires:
      bins: [python3, systemctl]
      env:
        - BINANCE_API_KEY
        - BINANCE_SECRET
        - TELEGRAM_BOT_TOKEN
        - TELEGRAM_CHANNEL
    startup:
      command: systemctl start neko-scanner neko-monitor neko-dashboard
      type: service
    repo: https://github.com/lukmanc405/neko-futures-trader
```
