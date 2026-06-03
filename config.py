# === Neko Futures Trader - CONFIGURATION ===
# Scanner v1.0.42 - Innovation Config 2026-06-01

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
MIN_SCORE_NORMAL = 8  # 2026-06-02: Naik dari 7→8, cuma masuk setup super bagus (WR 57% tapi avg loss > avg win)
MIN_SCORE_SHORT_BEAR = 6  # 2026-06-02: SHORT di bear market lebih longgar, crash tanpa volume tinggi

# ── SL/TP STRATEGY (2026-05-18 OVERHAUL) ────────────────────────────────────
PRICE_TP = 6.0                  # 2026-05-23: TP 6% — lebih sering kena TP, win rate naik
PRICE_SL = 3.0                  # Stop Loss: -3% for LONG, +3% for SHORT

# ── ATR-BASED DYNAMIC SL/TP (2026-06-01 INNOVATION) ─────────────────────────
USE_ATR_SLTP = True             # Use ATR for dynamic SL/TP per coin volatility
SL_ATR_MULTIPLIER = 1.5         # SL = 1.5 × ATR%
TP_ATR_MULTIPLIER = 3.0         # TP = 3 × ATR% (R:R = 1:2)
SL_MIN = 1.5                    # Floor SL%
SL_MAX = 5.0                    # Cap SL%
TP_MIN = 3.0                    # Floor TP%
TP_MAX = 10.0                   # Cap TP%

# ── BREAKEVEN & TRAILING ─────────────────────────────────────────────────────
MIN_PROFIT_BREAKEVEN = 1.5       # 2026-05-27: 3.0→1.5 — trailing starts earlier
TRAIL_SL_LOCK = 1.0              # 2026-05-27: 1.5→1.0 — lock less at start
TRAIL_SL_DISTANCE = 1.0          # 2026-05-27: 1.5→1.0 — tighter trail
MIN_PROFIT_TRAILING_TP = 6.0    # % profit to activate trailing TP (was 10%)
TRAIL_PERCENT = 1.5             # Trail TP by this % when trailing (was 2%)

# ── PARTIAL TP (2026-05-18: 3-stage exit) ───────────────────────────────────
TP1_PERCENT = 4.0               # Close 25% at this % profit
TP1_CLOSE_PCT = 0.25
TP2_PERCENT = 6.0               # Close another 25% at this % profit
TP2_CLOSE_PCT = 0.25
# Remaining 50% runs to PRICE_TP or trailing TP

# ── CONFIDENCE-BASED SIZING (2026-06-01 INNOVATION) ──────────────────────────
CONFIDENCE_SIZING = True        # Size positions based on LLM confidence
CONFIDENCE_LOW = 0.5            # Below this = skip trade entirely
CONFIDENCE_MED = 0.7            # Medium = ENTRY_PERCENT × 0.75
CONFIDENCE_HIGH = 0.85          # High = ENTRY_PERCENT × 1.0

# ── WIN/LOSS RATIO GUARD (2026-06-01 INNOVATION) ─────────────────────────────
MIN_WINLOSS_RATIO = 1.0         # Block entry if avg W/L ratio < 1.0
WL_RATIO_WINDOW = 50            # Check from last 50 trades
WL_RATIO_PAUSE_HOURS = 6        # Pause trading if ratio is bad

# ── COOLDOWN ESCALATION (2026-06-01 INNOVATION) ──────────────────────────────
COOLDOWN_LOSS_1 = 24            # Hours cooldown after 1 loss on symbol
COOLDOWN_LOSS_2 = 72            # After 2 consecutive losses
COOLDOWN_LOSS_3 = 168           # After 3 consecutive losses (1 week)

# ── AUTO-BLACKLIST (2026-06-01 INNOVATION) ───────────────────────────────────
AUTO_BLACKLIST_ENABLED = True
AUTO_BLACKLIST_CONSECUTIVE_LOSSES = 3  # Auto-blacklist after 3 losses without a win

# ── NOTIFICATIONS ─────────────────────────────────────────────────────────────
POST_SIGNALS_TO_TELEGRAM = True
NOTIFY_ON_OPEN = True
NOTIFY_ON_CLOSE = True
NOTIFY_ON_BREAKEVEN = False
NOTIFY_ON_TRAILING_SL = False
NOTIFY_ON_TRAILING_TP = False

# ── SCANNER ──────────────────────────────────────────────────────────────────
SCAN_INTERVAL = 300             # Scanner run every 5 minutes
MIN_PRICE_CHANGE = 2.0          # Min % price change for signal
SKIP_RECENT_HOURS = 24          # Skip re-entry for 24h after close
LOSS_COOLDOWN_HOURS = 48        # Skip re-entry 48h after a LOSS
MIN_VOLUME_RATIO = 1.5          # Min volume ratio vs 24h avg
CHASE_LIMIT_CRYPTO = 3.5        # Max % change for crypto entries
CHASE_LIMIT_TRADFI = 5.0        # Max % change for TradFi entries
MACD_FLAT_CRYPTO = 0.012        # MACD histogram threshold — below = "flat"
MACD_FLAT_TRADFI = 0.001        # MACD flat threshold for TradFi (tighter)
EMA_POSITION_LIMIT_CRYPTO = 65  # EMA position limit — reject if ema_position > this (LONG only)
EMA_POSITION_LIMIT_TRADFI = 80  # EMA position limit for TradFi (more lenient)
BTC_REGIME_CHECK = True         # 2026-05-8: Skip LONG if BTC 4H trend is bearish

# ── DYNAMIC COIN LIST ────────────────────────────────────────────────────────
DYNAMIC_COINS_ENABLED = True
DYNAMIC_MIN_VOLUME = 2_000_000  # Minimum 24h volume in USDT ($2M)
BLACKLISTED_SYMBOLS = [
    # === ORIGINAL BLACKLIST ===
    "TRUSTUSDT", "B2USDT", "PROMPTUSDT", "MITOUSDT", "MAGMAUSDT",
    "FETUSDT", "XPLUSDT", "LABUSDT", "RVNUSDT", "INTCUSDT",
    "NAORISUSDT", "CLOUSDT", "FHEUSDT", "PLAYUSDT", "GWEIUSDT",
    "UAIUSDT", "AINUSDT", "VELVETUSDT", "MIRAUSDT", "AKTUSDT",
    "BIOUSDT", "DODOXUSDT", "CVCUSDT", "SIRENUSDT", "FUSDT",
    # === 2026-06-01: STRUCTURAL FAILURES (0 wins, ≥3 losses) ===
    "PRLUSDT",       # 0W/20L, -78.30 USDT
    "DUSKUSDT",      # 0W/18L, -43.63 USDT
    "PENDLEUSDT",    # 0W/16L, -41.24 USDT
    "GTCUSDT",       # 0W/4L,  -48.83 USDT
    "DEEPUSDT",      # 0W/9L,  -42.70 USDT
    "LAUSDT",        # 0W/8L,  -41.66 USDT
    "CGPTUSDT",      # 0W/14L, -40.92 USDT
    "BEAMXUSDT",     # 0W/8L,  -43.33 USDT
    "XPINUSDT",      # 0W/14L, -35.01 USDT
    "HIGHUSDT",      # 0W/11L, -31.55 USDT
    "VVVUSDT",       # 0W/10L, -30.94 USDT
    "EWYUSDT",       # 0W/15L, -38.29 USDT (stock perps)
    # === 2026-06-02: AUTO-TUNER new structural failures ===
    "BANUSDT",       # AUTO-TUNER: blacklisted BANUSDT (0W/11L, -27.59 USDT) — 2026-06-02
    "ORDIUSDT",      # AUTO-TUNER: blacklisted ORDIUSDT (0W/10L, -24.43 USDT) — 2026-06-02
]

# ── LLM ANALYZER ────────────────────────────────────────────────────────────
LLM_ENABLED = True               # Re-enabled 2026-05-15 with volume filter
LLM_MODEL = "anthropic/claude-haiku-4.5"
LLM_MIN_SCORE = 4
LLM_TEMPERATURE = 0.1
LLM_BASE_URL = "https://inference-api.nousresearch.com/v1/chat/completions"
LLM_TIMEOUT = 15
LLM_CACHE_TTL = 300              # LLM response cache TTL in seconds (5 min)
LLM_MIN_CONFIDENCE = 0.6         # Minimum LLM confidence to approve (0.0-1.0)

LLM_FALLBACK1_ENABLED = False     # 2026-05-22: disabled — 9router 403 quota issues
LLM_FALLBACK1_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
LLM_FALLBACK1_MODEL = "nousresearch/hermes-4-70b"

LLM_FALLBACK2_ENABLED = False     # 2026-05-22: disabled — MiniMax consistently failing
LLM_FALLBACK2_BASE_URL = "https://api.minimaxi.chat/v1/chat/completions"
LLM_FALLBACK2_MODEL = "MiniMax-M2.5"

# ── RISK ─────────────────────────────────────────────────────────────────────
MAX_MARGIN_PERCENT = 45
MAX_RISK_PERCENT = 1.5

# ── SAFE COINS (FALLBACK — only used if DYNAMIC_COINS_ENABLED = False) ───────
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
    'RENDERUSDT','TAOUSDT','ONDOUSDT','STXUSDT',
    'TRXUSDT','EIGENUSDT','DYDXUSDT','CAKEUSDT','ENSUSDT',
    'WLDUSDT','JUPUSDT','1000PEPEUSDT','1000SHIBUSDT',
    '1000BONKUSDT','ENAUSDT','PENGUUSDT','TRUMPUSDT','TONUSDT',
    'HYPEUSDT','POLUSDT',
    # === STOCK PERPS ===
    'TSLAUSDT','NVDAUSDT','AAPLUSDT','AMZNUSDT','GOOGLUSDT','METAUSDT',
    'MSFTUSDT','AMDUSDT','COINUSDT','MSTRUSDT','HOODUSDT','CRCLUSDT',
    'PLTRUSDT','BABAUSDT','TSMUSDT','AVGOUSDT','QCOMUSDT',
    'MUUSDT','BILLUSDT','SNDKUSDT',
    # === STOCK INDICES ===
    'QQQUSDT','SPYUSDT',
    # === CRYPTO INDICES ===
    'BTCDOMUSDT','ALLUSDT',
    # === COMMODITIES ===
    'XAUUSDT','XAGUSDT','XPTUSDT','XPDUSDT',
    'CLUSDT','BZUSDT','NATGASUSDT','COPPERUSDT',
]
