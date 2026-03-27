# 🐱 Neko Futures Trader

Automated Bittensor Futures Trading Bot with DCA, SL/TP, and Trailing.

## 📁 Structure

```
neko-futures-trader/
├── scanner-v8.py           # Main scanner (5min intervals)
├── price-monitor.py        # SL/TP monitor (1sec intervals)
├── position_command.py     # Check positions
├── dashboard_api.py        # Dashboard API server
├── emergency_close.py      # Emergency position closer
├── daily_eval.py          # Daily performance evaluation
├── config.py              # Trading parameters
├── lib/                   # Helper modules
│   ├── signal_filter.py
│   ├── ict_indicators.py
│   ├── advanced_analysis.py
│   ├── delisting_monitor.py
│   └── error_handling.py
├── static/
│   └── neko-light.html    # Dashboard UI
├── README.md
└── SKILL.md
```

## 🚀 Quick Start

```bash
# Install dependencies
pip install python-dotenv requests pandas numpy scipy scikit-learn

# Setup .env (copy from .env.example)
cp .env.example .env
nano .env

# Start services
systemctl enable neko-scanner neko-monitor neko-dashboard
systemctl start neko-scanner neko-monitor neko-dashboard
```

## ⚙️ Config (.env)

```bash
BINANCE_API_KEY=your_key
BINANCE_SECRET=your_secret
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHANNEL=your_channel_id
```

## 📊 Commands

```bash
# Check positions
python3 position_command.py

# Daily evaluation
python3 daily_eval.py

# Emergency close all
python3 emergency_close.py

# View logs
tail -f logs/scanner.log
tail -f logs/pm.log
```

## 🌐 Dashboard

`https://YOUR_IP:8443/neko-light.html`

## 📈 ATR-Based SL/TP System

**ATR = Average True Range** - mengukur volatilitas pasar.

### Why ATR-Based?

| Method | Problem |
|--------|---------|
| Fixed % | Salah di market volatil/tenang |
| **ATR-Based** | Adaptive - menyesuaikan dengan kondisi pasar |

### Volatility Tiers

| Market | ATR Range | SL | TP |
|--------|-----------|-----|-----|
| HIGH | > 10% | 3× ATR | 6× ATR |
| NORMAL | 5-10% | 2.5× ATR | 5× ATR |
| LOW | < 5% | 2× ATR | 4× ATR |

### Example

```
Entry: $100
ATR: $2 (2%)

HIGH VOL (SL wider to avoid noise):
  SL = $100 - (3 × $2) = $94
  TP = $100 + (6 × $2) = $112

LOW VOL (tighter SL/TP):
  SL = $100 - (2 × $2) = $96
  TP = $100 + (4 × $2) = $108
```

### Advantages

- ✅ **Adaptive** - menyesuaikan dengan volatilitas
- ✅ **Noise filter** - mengurangi false trigger
- ✅ **Dynamic** - market volatile = SL lebih lebar, tenang = lebih ketat
- ✅ **Backtested** - terbukti lebih baik dari fixed %

---

## ⚙️ Parameters

| Param | Default | Description |
|-------|---------|-------------|
| MAX_POSITIONS | 5 | Max open positions |
| MAX_MARGIN | 30% | Max margin usage |
| LEVERAGE | 10x | Leverage multiplier |
| MIN_SCORE | 3 | Min signal score |

**SL/TP:** ATR-based with volatility adaptation

## 🐛 Fixes Applied

- ✅ `/fapi/v1/algoOrder` endpoint
- ✅ tickSize price rounding
- ✅ `algoType=CONDITIONAL` parameter
- ✅ `quantity=0` with `closePosition=true`
