# === Neko Futures Trader - CONFIGURATION ===
# Scanner v1.0.41 - Dynamic Coin List + Auto-add/Remove

# ── TRADING ──────────────────────────────────────────────────────────────────
LEVERAGE = 10                    # Futures leverage (10x)
MAX_POSITIONS = 8                # Max concurrent positions
AUTO_FILL_EMPTY_SLOTS = True     # Auto-find entries when positions < MAX
ENTRY_PERCENT = 8                # % of balance per trade (NORMAL mode)

# ── SLEEP MODE ───────────────────────────────────────────────────────────────
SLEEP_MODE = False              # Sleep mode toggle (use ./sleepmode command)
MAX_POSITIONS_SLEEP = 4          # Max positions in SLEEP mode
ENTRY_PERCENT_SLEEP = 5          # Entry % in SLEEP mode
MIN_SCORE_SLEEP = 7             # Min score to enter in SLEEP mode

# ── NORMAL MODE ──────────────────────────────────────────────────────────────
MIN_SCORE_NORMAL = 8             # 2026-06-02: Cuma masuk setup super bagus

# ── SL/TP STRATEGY ────────────────────────────────────────────────────────────
PRICE_TP = 15.0                 # Take Profit: +15% for LONG, -15% for SHORT
PRICE_SL = 5.0                  # Stop Loss: -5% for LONG, +5% for SHORT

# ── BREAKEVEN & TRAILING ─────────────────────────────────────────────────────
MIN_PROFIT_BREAKEVEN = 5.0       # % profit to start trailing SL
TRAIL_SL_LOCK = 2.0              # % profit to lock when trailing (SL = entry + this %)
TRAIL_SL_DISTANCE = 2.0          # SL trails this % below current price
MIN_PROFIT_TRAILING_TP = 10.0   # % profit to activate trailing TP
TRAIL_PERCENT = 2.0             # Trail TP by this % when trailing

# ── PARTIAL TP ──────────────────────────────────────────────────────────────
TP1_PERCENT = 5.0               # Close 25% at this % profit
TP1_CLOSE_PCT = 0.25
TP2_PERCENT = 10.0              # Close another 25% at this % profit
TP2_CLOSE_PCT = 0.25
# Remaining 50% runs to PRICE_TP (15%) or trailing TP

# ── NOTIFICATIONS ─────────────────────────────────────────────────────────────
POST_SIGNALS_TO_TELEGRAM = True
NOTIFY_ON_OPEN = True
NOTIFY_ON_CLOSE = True
NOTIFY_ON_BREAKEVEN = False
NOTIFY_ON_TRAILING_SL = False
NOTIFY_ON_TRAILING_TP = False

# ── SCANNER ──────────────────────────────────────────────────────────────────
SCAN_INTERVAL = 300             # Scanner run every 5 minutes
MIN_PRICE_CHANGE = 3.0          # Min % price change for signal
SKIP_RECENT_HOURS = 24          # Skip re-entry for 24h after close

# ── DYNAMIC COIN LIST ────────────────────────────────────────────────────────
# Auto-fetches all tradeable Binance Futures symbols, filters by volume,
# excludes settling/delisting pairs. Refreshes every hour.
# See dynamic_coins.py for implementation.
DYNAMIC_COINS_ENABLED = False   # Use static SAFE_COINS (not dynamic)
DYNAMIC_MIN_VOLUME = 2_000_000  # Minimum 24h volume in USDT ($2M)

# ── LLM ANALYZER ────────────────────────────────────────────────────────────
LLM_ENABLED = False              # LLM rejecting 98.5% of signals
LLM_MODEL = "xiaomi/mimo-v2-pro"
LLM_MIN_SCORE = 4
LLM_TEMPERATURE = 0.1
LLM_BASE_URL = "https://inference-api.nousresearch.com/v1/chat/completions"
LLM_TIMEOUT = 15

LLM_FALLBACK1_ENABLED = True
LLM_FALLBACK1_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
LLM_FALLBACK1_MODEL = "nousresearch/hermes-4-70b"

LLM_FALLBACK2_ENABLED = True
LLM_FALLBACK2_BASE_URL = "https://api.minimaxi.chat/v1/chat/completions"
LLM_FALLBACK2_MODEL = "MiniMax-M2.5"

# ── RISK ─────────────────────────────────────────────────────────────────────
MAX_MARGIN_PERCENT = 40
MAX_RISK_PERCENT = 1.5

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
    'FETUSDT','WLDUSDT','JUPUSDT','1000PEPEUSDT','1000SHIBUSDT',
    '1000BONKUSDT','ENAUSDT','PENGUUSDT','TRUMPUSDT','TONUSDT',
    'HYPEUSDT','POLUSDT',
    # === STOCK PERPS ===
    'TSLAUSDT','NVDAUSDT','AAPLUSDT','AMZNUSDT','GOOGLUSDT','METAUSDT',
    'MSFTUSDT','AMDUSDT','COINUSDT','MSTRUSDT','HOODUSDT','CRCLUSDT',
    'PLTRUSDT','BABAUSDT','INTCUSDT','TSMUSDT','AVGOUSDT','QCOMUSDT',
    'MUUSDT','BILLUSDT','SNDKUSDT','EWYUSDT',
    # === STOCK INDICES ===
    'QQQUSDT','SPYUSDT',
    # === CRYPTO INDICES ===
    'BTCDOMUSDT','ALLUSDT',
    # === COMMODITIES ===
    'XAUUSDT','XAGUSDT','XPTUSDT','XPDUSDT',
    'CLUSDT','BZUSDT','NATGASUSDT','COPPERUSDT',
]
