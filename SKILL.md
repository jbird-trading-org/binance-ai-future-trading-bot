# SKILL.md - Neko Futures Trader

## Overview
Automated futures trading bot with scanning, SL/TP, and trailing.

**Emoji:** 🐱📈
**Requires:** Python 3.8+, Binance Futures API

---

## 📁 File Structure

```
neko-futures-trader/
├── scanner-v8.py           # Scanner (5min intervals)
├── price-monitor.py        # SL/TP monitor (1sec)
├── position_command.py     # Position checker
├── dashboard_api.py         # Dashboard API
├── emergency_close.py      # Emergency closer
├── daily_eval.py          # Daily evaluation
├── config.py              # Trading parameters
├── lib/                   # Helper modules
│   ├── signal_filter.py
│   ├── ict_indicators.py
│   ├── advanced_analysis.py
│   ├── delisting_monitor.py
│   └── error_handling.py
└── static/
    └── neko-light.html    # Dashboard UI
```

---

## 🚀 Setup

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
TELEGRAM_CHANNEL=your_channel_id
```

### 4. Setup Workspace
```bash
mkdir -p /root/.openclaw/workspace/neko-futures-trader/{logs,data}
cp .env /root/.openclaw/workspace/neko-futures-trader/
```

---

## ⚙️ Systemd Services

### Scanner
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

### Monitor
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

### Enable
```bash
systemctl daemon-reload
systemctl enable neko-scanner neko-monitor
systemctl start neko-scanner neko-monitor
```

---

## 🌐 Dashboard

### Setup
```bash
# Copy HTML
cp static/neko-light.html /var/www/html/

# Nginx (port 8443 SSL)
# See nginx config in repository

# Start service
systemctl start neko-dashboard
```

### Access
`https://YOUR_IP:8443/neko-light.html`

---

## 📊 Commands

```bash
# Check positions
python3 position_command.py

# Daily evaluation  
python3 daily_eval.py

# Emergency close
python3 emergency_close.py

# Service management
systemctl status neko-scanner neko-monitor
systemctl restart neko-scanner
journalctl -u neko-scanner -f
```

---

## ⚙️ Trading Parameters

| Param | Default | Description |
|-------|---------|-------------|
| MAX_POSITIONS | 5 | Max open positions |
| MAX_MARGIN | 30% | Max margin usage |
| MAX_RISK_PERCENT | 1.5% | Max risk per trade |
| LEVERAGE | 10x | Leverage |
| MIN_SCORE | 3 | Signal threshold |
| BREAKEVEN | +5% | Move SL to entry |
| TRAILING | +10% | Activate trailing |

### ATR-Based System

**ATR (Average True Range)** measures market volatility. Our SL/TP adapts to market conditions:

| Market | ATR Range | SL | TP |
|--------|-----------|-----|-----|
| HIGH | > 10% | 3× ATR | 6× ATR |
| NORMAL | 5-10% | 2.5× ATR | 5× ATR |
| LOW | < 5% | 2× ATR | 4× ATR |

**Example:** Entry $100, ATR $2
- HIGH: SL=$94, TP=$112 (wider for volatility)
- LOW: SL=$96, TP=$108 (tighter for calm markets)

**Advantages:** Adaptive, noise-filtering, dynamic adjustment

### SL/TP (ATR-based)
| Vol | SL | TP |
|-----|----|----|
| HIGH | 3×ATR | 6×ATR |
| NORMAL | 2.5×ATR | 5×ATR |
| LOW | 2×ATR | 4×ATR |

---

## 🐛 Bug Fixes

1. **Algo API:** `/fapi/v1/algoOrder` (not `/orderAlg`)
2. **Params:** `algoType=CONDITIONAL`, `triggerPrice`, `stopPrice`
3. **Precision:** Rounds to tickSize per symbol
4. **Quantity:** Uses `quantity=0` with `closePosition=true`

---

## metadata

```yaml
metadata:
  openclaw:
    emoji: 🐱📈
    requires:
      bins: [python3]
      env: [BINANCE_API_KEY, BINANCE_SECRET, TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL]
    startup:
      command: "systemctl start neko-scanner neko-monitor"
      type: service
```
