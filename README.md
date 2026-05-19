<div align="center">

# 🐱 Neko Futures Trader

**Autonomous Binance Futures bot with adaptive bear-market signal detection**

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![WR](https://img.shields.io/badge/Win_Rate-67%25-brightgreen.svg)](#performance-snapshot)
[![Status](https://img.shields.io/badge/status-active-success.svg)](#)

*Quant-grade signal scoring · Real-time risk management · Self-tuning filters*

</div>

---

## 📊 Performance Snapshot

| Metric | Value |
|--------|-------|
| **Win Rate** (last 100 trades) | **67.0%** |
| **Realized PNL** (recent window) | +61.02 USDT |
| **Unrealized PNL** (live) | +196.13 USDT |
| **Risk:Reward** | 1:2.67 (3% SL / 8% TP) |
| **Max Drawdown** (recent) | -13.1% (recovered) |
| **Iteration Cycle** | Daily evaluation + autonomous parameter tuning |

> Performance fluctuates with market regime. The system is designed to **adapt filters to BTC trend** rather than pretend any single configuration is universal.

---

## 🎯 What Makes Neko Different

Most trading bots use static thresholds. Neko **detects market regime** (bullish / bearish / neutral via BTC 4H EMA9 vs EMA21) and **morphs its filter chain** accordingly:

```
                ┌─────────────────────────────────┐
                │   BTC 4H Regime Detection       │
                └────────────┬────────────────────┘
                             │
        ┌────────────────────┴────────────────────┐
        ▼                                         ▼
┌───────────────┐                      ┌───────────────────┐
│ BULL/NEUTRAL  │                      │      BEARISH      │
│ ──────────    │                      │ ────────────────  │
│ chase: 4%     │                      │ chase SHORT: 6%   │
│ vol: 1.5x     │                      │ vol: 1.0x         │
│ MACD strict   │                      │ MACD lenient      │
│ red ≥ 1       │                      │ red filter: skip  │
│ RSI guard 35  │                      │ RSI guard 15      │
│ range >40%    │                      │ range >40% (NEW)  │
│ LONG: allowed │                      │ LONG: blocked     │
└───────────────┘                      └───────────────────┘
```

This morph took the win rate from **19% → 67%** during the May 2026 bear market overhaul.

---

## 🧠 Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                       Binance Futures API                        │
└──────────────┬──────────────────────────────────┬────────────────┘
               │                                  │
       ┌───────▼────────┐                ┌────────▼─────────┐
       │   scanner.py   │                │ price-monitor.py │
       │   (signals)    │                │  (SL/TP/trail)   │
       │   60s cycle    │                │   15s / 5s adp.  │
       └───────┬────────┘                └────────┬─────────┘
               │                                  │
       ┌───────▼─────────┐                ┌───────▼──────────┐
       │ llm_analyzer.py │                │ algoOrder API    │
       │  (LLM gate)     │                │ (SL/TP placement)│
       └───────┬─────────┘                └──────────────────┘
               │
       ┌───────▼─────────────────────────────────────────────┐
       │              Multi-stage Filter Chain               │
       │  BTC regime → score → vol → chase → RSI → MACD →   │
       │  EMA → range → near-extreme → trend → MACD hist    │
       └─────────────────────────────────────────────────────┘
```

### Core services (systemd)
- `neko-scanner.service` — scanner.py · 60s cycle
- `neko-monitor.service` — price-monitor.py · 15s default, **5s adaptive when in-profit**
- `neko-dashboard.service` — dashboard_api.py · port 8080

---

## 🔬 Signal Pipeline

For every coin in the **dynamic universe** (auto-fetched from `/fapi/v1/exchangeInfo`, filtered by ≥ $2M 24h volume), the scanner:

1. **Fetch** klines (1H, 4H), 24h ticker, OI, funding rate
2. **Calculate indicators**: RSI(14), MACD(12,26,9), EMA(9,21,50), ADX(14), StochRSI, Bollinger Bands + squeeze, VWAP, Fisher Transform, range position, taker ratio, top-trader ratio
3. **Determine direction** — `price_change > 0 → LONG`, `< 0 → SHORT` with EMA + 4H trend conflict checks
4. **BTC regime gate** — skip LONGs entirely in BEARISH regime
5. **Hard filters** — chase, volume, RSI, MACD histogram, EMA position, range position, near-extreme, trend
6. **Score signal** — weighted indicators (max ~19), require ≥ 7 (crypto) or ≥ 6 (TradFi)
7. **Bonus points** — Bollinger squeeze, taker imbalance, top-trader positioning (+3 max), then re-check score
8. **LLM gate** (Nous MiMo-v2-pro primary, Hermes-4-70B and MiniMax-M2.5 fallbacks) — quality review with fail-open
9. **Sector exposure** — max 1 position per sector (gaming, DeFi, layer1, meme, AI, storage)
10. **Place order** — MARKET entry + algo SL/TP via `/fapi/v1/algoOrder`

### Coin universe selection

```python
DYNAMIC_COINS_ENABLED = True
DYNAMIC_MIN_VOLUME = 2_000_000  # $2M USDT 24h volume

# Per cycle:
top_gainers   = movers_filtered[:50]    # LONG candidates
bottom_losers = movers_filtered[-75:]   # SHORT candidates
# Deduplicated, then scanned (~125 coins per cycle)
```

> The `SAFE_COINS` list still exists in `config.py` as a fallback if dynamic coin fetch fails.

### Filter rejection telemetry (sample)

```
Checking SYSUSDT (-19.7%)... (chase_short=-19.7%<-6%) no signal
Checking BILLUSDT (-16.0%)... (rsi_short_low=11.66<35,btc=BEARISH) no signal
Checking MUUSDT (-6.7%)... (hist=1.2925>0) no signal
Checking ESPORTSUSDT (-6.4%)... (score=6/7) no signal
Checking MITOUSDT (-4.9%)... ✅ SIGNAL! SHORT
```

Every rejection logs the exact failing condition — making bug audits and filter tuning quantitative rather than vibes-based.

---

## 📈 Performance Engineering Highlights

### Multi-stage Take Profit (3-stage exit)

```
Entry → +4% (close 25%) → +6% (close 25%) → +8% target / trailing on remaining 50%
```

Combines partial profit-taking (capture spikes) with trailing on the runner. Locks profit at +3% breakeven, trails at 1.5% distance once +6% profit hit.

### Adaptive Price Monitor

The price monitor switches its polling interval based on position state:
- **15s** default (idle / out-of-profit positions)
- **5s** when any position is in profit (catch TP1 spikes, never miss exits)

Combined with persisted `peak_profit` per position, this prevents missed TPs from price wicks between cycles.

### Daily Self-Evaluation

`scripts/daily_eval.py` runs at 00:00 UTC and:

- Aggregates `REALIZED_PNL` from Binance income history
- Counts win/loss per symbol
- Categorizes filter rejections from `scanner.log`
- **Auto-tightens filters when WR < 40%**
- **Preserves filters when WR > 55%** (don't fix what works)
- Posts a Telegram report with bug audit + parameter changes

### Autonomous Health Check (every 4h via cron)

Detects and auto-fixes:

| Issue | Detection | Auto-Fix |
|-------|-----------|----------|
| Service crash | `systemctl is-active` | Restart + journal capture |
| Position without SL/TP | `openAlgoOrders` empty | Place 3% SL / 8% TP |
| Duplicate SL/TP | Multiple algo orders | Cancel extras, keep most-protective |
| Quantity precision error | Binance -1111 | Format to step_size decimals |
| Stale `__pycache__` | NameError on known function | Cleanup + restart |

---

## 🚀 Quick Start

### 1. Clone

```bash
git clone https://github.com/lukmanc405/neko-futures-trader.git
cd neko-futures-trader
```

### 2. Install dependencies

```bash
pip install requests numpy pandas python-dotenv scipy
```

### 3. Configure

Copy `.env.example` to `.env` and fill in:

```bash
BINANCE_API_KEY=your_key
BINANCE_SECRET=your_secret
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHANNEL=your_chat_id

# Optional LLM gate (recommended)
NOUS_API_KEY=your_nous_key             # Primary: xiaomi/mimo-v2-pro
OPENROUTER_API_KEY=your_openrouter_key # Fallback 1: nousresearch/hermes-4-70b
MINIMAX_API_KEY=your_minimax_key       # Fallback 2: MiniMax-M2.5
```

> ⚠️ **Important:** Never commit `.env`. Use Binance API keys with **Futures trading only** permission. **Disable Withdrawals** on the API key.

### 4. Create systemd services

Sample `neko-scanner.service`:

```ini
[Unit]
Description=Neko Futures Scanner
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/path/to/neko-futures-trader
ExecStart=/usr/bin/python3 /path/to/neko-futures-trader/scanner.py
Restart=always
RestartSec=10
StandardOutput=append:/path/to/neko-futures-trader/logs/scanner.log
StandardError=append:/path/to/neko-futures-trader/logs/scanner.log

[Install]
WantedBy=multi-user.target
```

Repeat for `neko-monitor.service` (`price-monitor.py`) and `neko-dashboard.service` (`dashboard_api.py`).

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now neko-scanner neko-monitor neko-dashboard
```

### 5. Verify

```bash
sudo systemctl status neko-scanner.service
tail -f logs/scanner.log
```

---

## ⚙️ Configuration Reference

| Parameter | Default | Description |
|-----------|---------|-------------|
| `MIN_SCORE_NORMAL` | 7 | Min signal score (crypto, TradFi uses 6) |
| `MIN_PRICE_CHANGE` | 2.0% | Min 24h price change |
| `PRICE_SL` / `PRICE_TP` | 3% / 8% | Stop / Take Profit |
| `MIN_VOLUME_RATIO` | 1.5x | Min volume ratio (relaxed to 1.0x for bear-SHORT) |
| `CHASE_LIMIT_CRYPTO` | 4% | Max 24h move (6% for bear-SHORT) |
| `CHASE_LIMIT_TRADFI` | 5% | TradFi chase ceiling (7% for bear-SHORT) |
| `MAX_POSITIONS` | 8 | Max concurrent positions |
| `MAX_MARGIN_PERCENT` | 40% | Max margin usage (scanner pauses above) |
| `MAX_RISK_PERCENT` | 1.5% | Max risk per trade |
| `LEVERAGE` | 10x | Default leverage |
| `BTC_REGIME_CHECK` | true | Skip LONG if BTC 4H bearish |
| `LOSS_COOLDOWN_HOURS` | 48 | Cooldown after a losing trade |
| `MAX_DAILY_LOSS` | -30 USDT | Stop trading for the day if hit |
| `DYNAMIC_COINS_ENABLED` | true | Auto-discover coin universe |
| `DYNAMIC_MIN_VOLUME` | $2M | Min 24h USDT volume to include |
| `SCAN_INTERVAL` | 60s | Scanner cycle (legacy `300` constant; actual `time.sleep(60)`) |

---

## 🛡️ Risk Management

- **Per-trade risk capped** at 1.5% of balance
- **Margin ceiling** at 40% (scanner pauses above)
- **Daily loss limit** stops trading at -30 USDT (resumes at midnight UTC)
- **Loss cooldown** — losing trades get 48h before re-entry on same symbol
- **Sector limit** — max 1 position per sector (gaming, DeFi, layer1, meme, AI, storage)
- **All positions get SL/TP** — orphan position detection runs every 4h via health check

---

## 📊 Diagnostic Commands

```bash
# Live scanner output
tail -f logs/scanner.log

# Daily evaluation report
python3 scripts/daily_eval.py

# Trade history analysis
python3 scripts/analyze_trades.py

# Open positions
python3 position_command.py

# Account balance
python3 scripts/check_balance.py

# Backtest
python3 scripts/backtester.py
```

Filter rejection breakdown (one-liner):

```bash
tail -5000 logs/scanner.log | grep -oE "\([a-z_]+=" | sort | uniq -c | sort -rn | head -10
```

---

## 🐛 Notable Bug Fixes (Public Changelog)

| Date | Issue | Fix |
|------|-------|-----|
| 2026-05-19 | SHORT entries at range bottom kept bouncing | Added range_position ≥ 40% filter for SHORT |
| 2026-05-19 | `datetime` UnboundLocalError on SL/TP save | Removed inner `from datetime import datetime` shadowing module import |
| 2026-05-18 | Win rate dropped to 19% during bear market | Bear-market SHORT filter relaxation overhaul |
| 2026-05-17 | Static `SAFE_COINS` list missed 82% of market | Enabled `DYNAMIC_COINS_ENABLED` for auto-universe |
| 2026-05-15 | Only TradFi entries, no crypto signals | Scanner coverage expanded `[:50]` → `[:100]` |
| 2026-05-13 | 5-6% pumps bypassed safety filters as "breakouts" | Raised exception threshold 5% → 7% |
| 2026-05-12 | Fake breakouts entering at flat MACD + 3% pump | Hard reject if `abs(histogram) < 0.005` AND `price_change > 3%` |
| 2026-05-11 | 4/5 entries at upper range (chasing) | Position range filter ≤ 70% (LONG) |

Full changelog and reasoning in commit history.

---

## 🏗️ Tech Stack

- **Language:** Python 3.11+
- **Trading:** Binance Futures USDT-M (`/fapi/v1/algoOrder` for SL/TP)
- **LLM Gate:** xiaomi/mimo-v2-pro (Nous primary), nousresearch/hermes-4-70b (OpenRouter fallback), MiniMax-M2.5 (fallback)
- **Indicators:** Custom NumPy implementations (no TA-Lib dependency)
- **Process:** systemd services + journald
- **Logging:** Append-only logs + structured rejection telemetry
- **Notifications:** Telegram bot for signals, fills, daily reports
- **Dashboard:** Vanilla HTML/CSS/JS served via aiohttp on port 8080

---

## 📁 Project Structure

```
neko-futures-trader/
├── scanner.py              # Main signal scanner (60s cycle)
├── price-monitor.py        # SL/TP + trailing monitor (15s/5s adaptive)
├── dashboard_api.py        # Web dashboard server
├── llm_analyzer.py         # LLM signal review gate (3 providers)
├── dynamic_coins.py        # Coin universe auto-discovery
├── delisting_monitor.py    # Avoid coins flagged for delisting
├── signal_filter.py        # Filter chain helpers
├── ict_indicators.py       # Custom indicators
├── advanced_analysis.py    # Multi-timeframe analysis
├── error_handling.py       # Retry / backoff utilities
├── position_command.py     # CLI: list open positions
├── config.py               # Trading parameters
├── scripts/
│   ├── daily_eval.py       # Daily PNL + auto-tuning
│   ├── analyze_trades.py   # Per-symbol trade analytics
│   ├── check_balance.py    # Account balance checker
│   ├── check_positions.py  # Position checker (alt)
│   ├── dashboard_api.py    # API server (alt entry)
│   └── backtester.py       # Monte Carlo backtest
├── static/                 # Dashboard UI
└── logs/                   # Scanner / monitor logs (gitignored)
```

---

## ⚠️ Disclaimer

**This is a personal trading project, not financial advice.** Crypto futures trading carries substantial risk and can result in total loss of funds. Past performance does not guarantee future results. Run on a small allocation, validate the strategy on testnet first, and only risk what you can afford to lose.

The author is not liable for any trading losses incurred by use of this software.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

**Built with care by [@lukmanc405](https://github.com/lukmanc405)** · *Iterating in public 🐱*

</div>
