# === Neko Futures Trader - CONFIGURATION ===
# Scanner v1.0.41 - Dynamic Coin List + Auto-add/Remove

# ── TRADING ──────────────────────────────────────────────────────────────────
LEVERAGE = 10                    # Futures leverage (10x)
MAX_POSITIONS = 3                # 2026-05-30: REAL WR=54.8% (-148 USDT). AUTO-TUNER: WR>60%→5, WR<55%→3
MAX_SAME_DIRECTION = 2           # MAX_POSITIONS-1
AUTO_FILL_EMPTY_SLOTS = True     # Auto-find entries when positions < MAX
ENTRY_PERCENT = 8                # % of balance per trade (NORMAL mode)

# ── SLEEP MODE ───────────────────────────────────────────────────────────────
SLEEP_MODE = False              # Sleep mode toggle (use ./sleepmode command)
MAX_POSITIONS_SLEEP = 2          # AUTO-TUNER: MAX_POSITIONS-1 (2026-05-30)
ENTRY_PERCENT_SLEEP = 5          # Entry % in SLEEP mode
MIN_SCORE_SLEEP = 7             # Min score to enter in SLEEP mode

# ── NORMAL MODE ──────────────────────────────────────────────────────────────
MIN_SCORE_NORMAL = 7  # Auto-tuner v2: Revert to minimum safe threshold (was 6.0)

# ── SL/TP STRATEGY (2026-05-18 OVERHAUL) ────────────────────────────────────
# Old: SL=5%, TP=15% → 22% WR, big losses. New: SL=3%, TP=8% → tighter risk, better R:R
PRICE_TP = 6.0                  # 2026-05-23: TP 6% — lebih sering kena TP, win rate naik
PRICE_SL = 3.0                  # Stop Loss: -3% for LONG, +3% for SHORT

# ── BREAKEVEN & TRAILING ─────────────────────────────────────────────────────
MIN_PROFIT_BREAKEVEN = 1.5       # 2026-05-27: 3.0→1.5 — trailing starts earlier, lock small profits > lose big
TRAIL_SL_LOCK = 1.0              # 2026-05-27: 1.5→1.0 — lock less at start (earlier activation)
TRAIL_SL_DISTANCE = 1.0          # 2026-05-27: 1.5→1.0 — tighter trail to protect small profits
MIN_PROFIT_TRAILING_TP = 6.0    # % profit to activate trailing TP (was 10%)
TRAIL_PERCENT = 1.5             # Trail TP by this % when trailing (was 2%)

# ── PARTIAL TP (2026-05-18: 3-stage exit) ───────────────────────────────────
TP1_PERCENT = 4.0               # Close 25% at this % profit (was 5%)
TP1_CLOSE_PCT = 0.25
TP2_PERCENT = 6.0               # Close another 25% at this % profit (was 10%)
TP2_CLOSE_PCT = 0.25
# Remaining 50% runs to PRICE_TP (8%) or trailing TP

# ── NOTIFICATIONS ─────────────────────────────────────────────────────────────
POST_SIGNALS_TO_TELEGRAM = True
NOTIFY_ON_OPEN = True
NOTIFY_ON_CLOSE = True
NOTIFY_ON_BREAKEVEN = False
NOTIFY_ON_TRAILING_SL = False
NOTIFY_ON_TRAILING_TP = False

# ── SCANNER ──────────────────────────────────────────────────────────────────
SCAN_INTERVAL = 300             # Scanner run every 5 minutes
MIN_PRICE_CHANGE = 2.0          # Min % price change for signal (was 3.0, too strict for sideways market)
SKIP_RECENT_HOURS = 24          # Skip re-entry for 24h after close
LOSS_COOLDOWN_HOURS = 48        # 2026-05-18: Skip re-entry 48h after a LOSS (prevent revenge trading)
MIN_VOLUME_RATIO = 1.5  # Auto-tuned: 1.5→1.2 (relax volume filter)
CHASE_LIMIT_CRYPTO = 3.5  # Auto-tuned: 4.0→5.0 (relax chase limit)
CHASE_LIMIT_TRADFI = 5.0        # Max % change for TradFi entries
BTC_REGIME_CHECK = True         # 2026-05-8: Skip LONG if BTC 4H trend is bearish

# ── DYNAMIC COIN LIST ────────────────────────────────────────────────────────
# Auto-fetches all tradeable Binance Futures symbols, filters by volume,
# excludes settling/delisting pairs. Refreshes every hour.
# See dynamic_coins.py for implementation.
DYNAMIC_COINS_ENABLED = True    # 2026-05-17: Enabled — static SAFE_COINS only covers 18% of market, missing 97% of volatile movers
DYNAMIC_MIN_VOLUME = 2_000_000  # Minimum 24h volume in USDT ($2M)
BLACKLISTED_SYMBOLS = ["TRUSTUSDT", "B2USDT", "PROMPTUSDT", "MITOUSDT", "MAGMAUSDT", "FETUSDT", "XPLUSDT", "LABUSDT", "RVNUSDT", "INTCUSDT", "NAORISUSDT", "CLOUSDT", "FHEUSDT", "PLAYUSDT", "GWEIUSDT", "UAIUSDT", "AINUSDT", "VELVETUSDT", "MIRAUSDT", "AKTUSDT", "BIOUSDT", "DODOXUSDT", "CVCUSDT", "SIRENUSDT", "FUSDT"]  # AUTO-TUNER: +SIRENUSDT (0W/3L, -26.21 USDT) +FUSDT (0W/18L, -24.13 USDT) — 2026-05-31

# ── LLM ANALYZER ────────────────────────────────────────────────────────────
LLM_ENABLED = True               # Re-enabled 2026-05-15 with volume filter
LLM_MODEL = "anthropic/claude-haiku-4.5"
LLM_MIN_SCORE = 4
LLM_TEMPERATURE = 0.1
LLM_BASE_URL = "https://inference-api.nousresearch.com/v1/chat/completions"
LLM_TIMEOUT = 15

LLM_FALLBACK1_ENABLED = False     # 2026-05-22: disabled — 9router 403 quota issues
LLM_FALLBACK1_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
LLM_FALLBACK1_MODEL = "nousresearch/hermes-4-70b"

LLM_FALLBACK2_ENABLED = False     # 2026-05-22: disabled — MiniMax consistently failing
LLM_FALLBACK2_BASE_URL = "https://api.minimaxi.chat/v1/chat/completions"
LLM_FALLBACK2_MODEL = "MiniMax-M2.5"

# ── RISK ─────────────────────────────────────────────────────────────────────
MAX_MARGIN_PERCENT = 45
MAX_RISK_PERCENT = 1.5
MAX_DAILY_LOSS = -30               # Disabled 2026-05-25 per user request (was -30 USDT)

# ── SAFE COINS (FALLBACK — only used if DYNAMIC_COINS_ENABLED = False) ───────
# Static list as backup. Dynamic mode fetches live from Binance API.
SAFE_COINS = [
    # === CRYPTO (blue-chip + mid-cap) ===
    'BTCUSDT','ETHUSDT','BNBUSDT','SOLUSDT','XRPUSDT','DOGEUSDT',
    'ADAUSDT','AVAXUSDT','DOTUSDT','LINKUSDT','LTCUSDT','BCHUSDT',
    'ATOMUSDT','UNIUSDT','ETCUSDT','XLMUSDT','FILUSDT',
    'APTUSDT','NEARUSDT','ARBUSDT','OPUSDT','AAVEUSDT','MKRUSDT',
    'GRTUSDT','SNXUSDT','IMXUSDT','ALGOUSDT','SANDUSDT',
    'MANAUSDT','AXSUSDT','CHZUSDT','ENJUSDT','NEOUSDT','ZECUSDT',
    'EOSUSDT','THETAUSDT','KAVAUSDT','ZILUSDT','KSMUSDT',
    'RUNEUSDT','MINAUSDT','QNTUSDT','LDOUSDT','SUIUSDT',
    'SEIUSDT','TIAUSDT','INJUSDT','WIFUSDT','ORDIUSDT',
    'RENDERUSDT','TAOUSDT','ONDOUSDT','PENDLEUSDT','STXUSDT',
    'TRXUSDT','EIGENUSDT','DYDXUSDT','CAKEUSDT','ENSUSDT',
    'WLDUSDT','JUPUSDT','1000PEPEUSDT','1000SHIBUSDT',
    '1000BONKUSDT','ENAUSDT','PENGUUSDT','TRUMPUSDT','TONUSDT',
    'HYPEUSDT','POLUSDT',
    # === STOCK PERPS ===
    'TSLAUSDT','NVDAUSDT','AAPLUSDT','AMZNUSDT','GOOGLUSDT','METAUSDT',
    'MSFTUSDT','AMDUSDT','COINUSDT','MSTRUSDT','HOODUSDT','CRCLUSDT',
    'PLTRUSDT','BABAUSDT','TSMUSDT','AVGOUSDT','QCOMUSDT',
    'MUUSDT','BILLUSDT','SNDKUSDT','EWYUSDT',
    # === STOCK INDICES ===
    'QQQUSDT','SPYUSDT',
    # === CRYPTO INDICES ===
    'BTCDOMUSDT','ALLUSDT',
    # === COMMODITIES ===
    'XAUUSDT','XAGUSDT','XPTUSDT','XPDUSDT',
    'CLUSDT','BZUSDT','NATGASUSDT','COPPERUSDT',
]
