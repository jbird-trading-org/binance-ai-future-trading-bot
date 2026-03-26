---
name: neko-futures-trader
description: |
  Professional Binance Futures automated trading system with AI-powered signal detection.
  
  🎯 CORE FEATURES:
  - Auto Entry: Scanner finds signals every 5 minutes
  - Auto SL/TP: Price monitor checks every 1 second
  - Auto Cache Cleanup: Removes expired entries on startup
  - Auto Breakeven: Moves SL to entry at +5%
  - Auto Trailing TP: Activates at +10%
  - Auto Delisting: Blocks delisted tokens
  - Auto Recovery: Self-heals from errors
  
  📊 STRATEGY:
  - Multi-TP: 40% @ +10%, 30% @ +15%, 30% @ +20%
  - Dynamic ATR: SL/TP adjusts to volatility
  - 14 Indicators: RSI, MACD, Bollinger, VWAP, EMA, etc.
  - 64 SAFE_COINS pre-filtered
  
  ⚙️ SETTINGS (in config.py):
  - MAX_POSITIONS = 7
  - ENTRY_PERCENT = 6%
  - MIN_PROFIT_BREAKEVEN = 5.0%
  - MIN_PROFIT_TRAILING_TP = 10.0%
  - CHECK_INTERVAL = 1 second
  
  📁 FILES:
  - scanner-v8.py (main scanner)
  - price-monitor.py (TP/SL executor)
  - config.py (all settings)
  - advanced_analysis.py (indicators)
  - error_handling.py (self-healing)
  - delisting_monitor.py (safety)
  - position_command.py (/position command)
  
  🔑 REQUIRED ENV:
  - BINANCE_API_KEY
  - BINANCE_SECRET
  - TELEGRAM_BOT_TOKEN
  - TELEGRAM_CHANNEL
  
  💰 BALANCE: ~$392 (as of 2026-03-19)
  
  Use when: user wants automated futures trading or asks about positions.
  
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
    startup:
      # Scanner via systemd (recommended)
      command: "systemctl start neko-scanner neko-monitor || (cp scanner-v8.py price-monitor.py config.py .env advanced_analysis.py error_handling.py delisting_monitor.py signal_filter.py ict_indicators.py whale_tracker.py /root/.openclaw/workspace/neko-futures-trader/ && systemctl daemon-reload && systemctl enable neko-scanner neko-monitor && systemctl start neko-scanner neko-monitor)"
      type: "service"
---

# Neko Futures Trader 🐱📈

## Quick Install (For New Agent)

```bash
# 1. Copy skill files to workspace
mkdir -p /root/.openclaw/workspace/neko-futures-trader
cp scanner-v8.py price-monitor.py config.py .env advanced_analysis.py error_handling.py delisting_monitor.py signal_filter.py ict_indicators.py whale_tracker.py /root/.openclaw/workspace/neko-futures-trader/

# 2. Setup .env (copy from skills folder if not exists)
cp /root/.openclaw/skills/neko-futures-trader/.env /root/.openclaw/workspace/neko-futures-trader/.env 2>/dev/null

# 3. Install systemd services (recommended)
# See Systemd Services section below

# 4. Or start manually
cd /root/.openclaw/workspace/neko-futures-trader
nohup python3 scanner-v8.py &
nohup python3 price-monitor.py &

# 5. Check status
python3 position_command.py
```

## Auto Features (All Running)

| Feature | Status | Description |
|---------|--------|-------------|
| 🔍 Auto Entry | ✅ ON | Scanner runs every 5 min |
| ⏱️ Auto TP/SL | ✅ ON | Price monitor every 1 sec |
| 🧹 Auto Cache | ✅ ON | Cleans 24h old entries on startup |
| 🛡 Auto Breakeven | ✅ ON | SL → Entry at +5% |
| 🎯 Auto Trailing | ✅ ON | TP trails at +10% |
| 🚫 Auto Delisting | ✅ ON | Blocks bad tokens |
| 🔄 Auto Recovery | ✅ ON | Self-heals from errors |
| 📱 Auto Notify | ✅ ON | Telegram alerts |

## Configuration (config.py)

```python
# === TRADING ===
MAX_POSITIONS = 7
AUTO_FILL_EMPTY_SLOTS = True
ENTRY_PERCENT = 6%
LEVERAGE = 10

# === RISK ===
MIN_PROFIT_BREAKEVEN = 5.0      # SL → Entry at +5%
MIN_PROFIT_TRAILING_TP = 10.0   # Trail at +10%

# === MULTI-TP (1:2 R/R) ===
TP1_PERCENT = 10.0   # Close 40% @ +10%
TP2_PERCENT = 15.0   # Close 30% @ +15%
TP3_PERCENT = 20.0   # Close 30% @ +20%

# === DYNAMIC ATR ===
ATR_MULTIPLIER_SL_HIGH = 2.0    # High vol: SL 2×ATR
ATR_MULTIPLIER_TP_HIGH = 4.0    # High vol: TP 4×ATR
ATR_MULTIPLIER_SL_NORMAL = 1.5  # Normal: SL 1.5×ATR
ATR_MULTIPLIER_TP_NORMAL = 3.0  # Normal: TP 3×ATR
ATR_MULTIPLIER_SL_LOW = 1.0     # Low vol: SL 1×ATR
ATR_MULTIPLIER_TP_LOW = 2.5     # Low vol: TP 2.5×ATR

# === MONITOR ===
CHECK_INTERVAL = 1  # seconds
```

## Signal Indicators (v1.0.36)

| # | Indicator | Condition | Score |
|---|-----------|-----------|-------|
| 1 | Volume Spike | >3x avg | +2 |
| 2 | Price Change | >10% | +2 |
| 3 | 1H Change | >3% | +1 |
| 4 | Breakout | HH/HL broken | +2 |
| 5 | Breakdown | LH/LL broken | +2 |
| 6 | OI Increase | >20% | +2 |
| 7 | Weekly Change | >20% | +3 |
| 8 | Pocket Pivot | Yes | +2 |
| 9 | RSI | <30 or >70 | +1 |
| 10 | MACD Cross | Histogram | +1 |
| 11 | Bollinger | Band touch | +1 |
| 12 | VWAP Cross | Price cross | +1 |
| 13 | Volume 5x | Extra spike | +2 |
| 14 | DCR | >20% | +1 |

**Minimum Score: 3 to trigger signal**

## File Structure

```
neko-futures-trader/
├── scanner-v8.py          # Main scanner (auto entry)
├── price-monitor.py       # TP/SP executor (auto close)
├── config.py             # All settings
├── advanced_analysis.py   # RSI, MACD, etc.
├── error_handling.py     # Circuit breaker, rate limiter
├── delisting_monitor.py   # Auto block delisted
├── position_command.py    # /position command
├── .env                  # API keys (SECRET)
├── .positions_sl_tp.json # Position cache
├── .recently_closed      # Closed cache (24h)
├── .posted_signals       # Posted cache
├── README.md             # Documentation
└── SKILL.md              # This file
```

## Systemd Services (Recommended)

All services auto-start on boot and auto-recover on failure.

### Install Services
```bash
# Copy script files to workspace
cp scanner-v8.py price-monitor.py config.py .env /root/.openclaw/workspace/neko-futures-trader/
cp advanced_analysis.py error_handling.py delisting_monitor.py signal_filter.py ict_indicators.py whale_tracker.py /root/.openclaw/workspace/neko-futures-trader/

# Create scanner service
cat > /etc/systemd/system/neko-scanner.service << 'EOF'
[Unit]
Description=Neko Futures Trader Scanner
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/.openclaw/workspace/neko-futures-trader
ExecStart=/usr/bin/python3 /root/.openclaw/skills/neko-futures-trader/scanner-v8.py
Restart=always
RestartSec=10
StandardOutput=append:/root/.openclaw/workspace/neko-futures-trader/scanner.log
StandardError=append:/root/.openclaw/workspace/neko-futures-trader/scanner.log

[Install]
WantedBy=multi-user.target
EOF

# Create monitor service
cat > /etc/systemd/system/neko-monitor.service << 'EOF'
[Unit]
Description=Neko Futures Trader Price Monitor
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/.openclaw/workspace/neko-futures-trader
ExecStart=/usr/bin/python3 /root/.openclaw/skills/neko-futures-trader/price-monitor.py
Restart=always
RestartSec=10
StandardOutput=append:/root/.openclaw/workspace/neko-futures-trader/pm.log
StandardError=append:/root/.openclaw/workspace/neko-futures-trader/pm.log

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
systemctl daemon-reload
systemctl enable neko-scanner neko-monitor
systemctl start neko-scanner neko-monitor
```

### Service Commands
```bash
systemctl status neko-scanner    # Check scanner
systemctl status neko-monitor    # Check monitor
systemctl restart neko-scanner   # Restart scanner
systemctl restart neko-monitor   # Restart monitor
systemctl stop neko-scanner      # Stop scanner
systemctl stop neko-monitor      # Stop monitor
journalctl -u neko-scanner -f    # View scanner logs
```

---

## Dashboard (Optional)

### Dashboard API Service
```bash
cat > /etc/systemd/system/neko-dashboard.service << 'EOF'
[Unit]
Description=Neko Futures Trader Dashboard API
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/.openclaw/workspace/neko-futures-trader
ExecStart=/usr/bin/python3 /root/.openclaw/skills/neko-futures-trader/dashboard_api.py
Restart=always
RestartSec=5
StandardOutput=append:/root/.openclaw/workspace/neko-futures-trader/dashboard.log
StandardError=append:/root/.openclaw/workspace/neko-futures-trader/dashboard.log

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable neko-dashboard
systemctl start neko-dashboard
```

### Nginx Configuration for Dashboard
```nginx
server {
    listen 8443 ssl;
    server_name YOUR_IP;

    ssl_certificate /etc/nginx/ssl/ssl.crt;
    ssl_certificate_key /etc/nginx/ssl/ssl.key;

    root /var/www/html;

    location /neko-light.html {
        try_files /neko-light.html =404;
    }

    location /api {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    location / {
        try_files /neko-light.html =404;
    }
}
```

### Copy Static Files
```bash
cp /root/.openclaw/skills/neko-futures-trader/neko-light.html /var/www/html/
```

### Access Dashboard
- Dashboard: `https://YOUR_IP:8443/neko-light.html`
- API: `https://YOUR_IP:8443/api`

---

## Commands

### Start Scanner (manual)
```bash
cd /root/.openclaw/workspace/neko-futures-trader
nohup python3 scanner-v8.py > scanner.log 2>&1 &
```

### Start Price Monitor (manual)
```bash
cd /root/.openclaw/workspace/neko-futures-trader
nohup python3 price-monitor.py > pm.log 2>&1 &
```

### Check Positions
```bash
python3 position_command.py
```

### Check Running
```bash
pgrep -f scanner-v8 && echo "Scanner OK"
pgrep -f price-monitor && echo "Monitor OK"
```

## Current Status (2026-03-19)

- 💰 Balance: ~$392
- 📊 Positions: 2/7 (KAVA, ARB)
- 🔍 Scanner: Running
- ⏱️ Monitor: Running
- 📱 Telegram: Connected

## Safety Features

1. **Cache Auto-Cleanup**: Removes entries >24h old
2. **Recently Closed**: Skips re-entry for 24h
3. **Delisting Monitor**: Auto-blocks bad tokens
4. **Error Handling**: Circuit breaker, rate limiter
5. **Recovery**: Auto-restart on failure

---
*Built by Neko Sentinel* 🐱🛡️
