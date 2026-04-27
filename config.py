# === Neko Futures Trader - CONFIGURATION ===
# Scanner v1.0.40 - New LONG/SHORT Strategy + Sleep Mode

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
MIN_SCORE_NORMAL = 6             # Min score to enter in NORMAL mode (balanced with new filters)

# ── SL/TP STRATEGY ────────────────────────────────────────────────────────────
# Percentage-based: PRICE_SL / PRICE_TP

PRICE_TP = 15.0                 # Take Profit: +15% for LONG, -15% for SHORT
PRICE_SL = 5.0                  # Stop Loss: -5% for LONG, +5% for SHORT

# ── BREAKEVEN & TRAILING ─────────────────────────────────────────────────────
MIN_PROFIT_BREAKEVEN = 5.0       # % profit to start trailing SL
TRAIL_SL_LOCK = 2.0              # % profit to lock when trailing (SL = entry + this %)
TRAIL_SL_DISTANCE = 2.0          # SL trails this % below current price
MIN_PROFIT_TRAILING_TP = 10.0   # % profit to activate trailing TP
TRAIL_PERCENT = 2.0             # Trail TP by this % when trailing

# ── PARTIAL TP (take profit in stages) ────────────────────────────────────────
TP1_PERCENT = 5.0               # Close 25% at this % profit
TP1_CLOSE_PCT = 0.25            # Percentage to close at TP1
TP2_PERCENT = 10.0              # Close another 25% at this % profit
TP2_CLOSE_PCT = 0.25            # Percentage to close at TP2
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
MIN_PRICE_CHANGE = 2.0          # Min % price change for signal (lowered from 3.0 for choppy markets)
SKIP_RECENT_HOURS = 24          # Skip re-entry for 24h after close

# ── LLM ANALYZER (Hybrid AI Gate) ────────────────────────────────────────────
# Second opinion layer — LLM checks candidates before execution
# Priority: Nous (primary) → OpenRouter (fallback 1) → MiniMax (fallback 2)
LLM_ENABLED = True              # Toggle LLM analysis on/off
LLM_MODEL = "xiaomi/mimo-v2-pro"  # Primary: Nous hosted
LLM_MIN_SCORE = 4               # Only analyze candidates with score >= this
LLM_TEMPERATURE = 0.1           # Low = deterministic
LLM_BASE_URL = "https://inference-api.nousresearch.com/v1/chat/completions"  # Nous endpoint
LLM_TIMEOUT = 15                # Seconds before timeout (fail-open)

# ── LLM FALLBACK 1 (OpenRouter) ──────────────────────────────────────────────
LLM_FALLBACK1_ENABLED = True
LLM_FALLBACK1_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
LLM_FALLBACK1_MODEL = "nousresearch/hermes-4-70b"

# ── LLM FALLBACK 2 (MiniMax) ─────────────────────────────────────────────────
LLM_FALLBACK2_ENABLED = True
LLM_FALLBACK2_BASE_URL = "https://api.minimaxi.chat/v1/chat/completions"
LLM_FALLBACK2_MODEL = "MiniMax-M2.5"

# ── RISK ─────────────────────────────────────────────────────────────────────
MAX_MARGIN_PERCENT = 40         # Max margin usage %
MAX_RISK_PERCENT = 1.5          # Max risk per trade %

# ── SAFE COINS ───────────────────────────────────────────────────────────────
SAFE_COINS = [
    'BNBUSDT','ETHUSDT','BTCUSDT','XRPUSDT','ADAUSDT','DOGEUSDT',
    'SOLUSDT','DOTUSDT','MATICUSDT','LTCUSDT','AVAXUSDT','LINKUSDT',
    'ATOMUSDT','UNIUSDT','ETCUSDT','XLMUSDT','BCHUSDT','FILUSDT',
    'APTUSDT','NEARUSDT','ARBUSDT','OPUSDT','AAVEUSDT','MKRUSDT',
    'GRTUSDT','SNXUSDT','IMXUSDT','ALGOUSDT','FTMUSDT','SANDUSDT',
    'MANAUSDT','AXSUSDT','CHZUSDT','ENJUSDT','NEOUSDT','ZECUSDT',
    'EOSUSDT','THETAUSDT','KAVAUSDT','WAVESUSDT','ZILUSDT','KSMUSDT',
    'RUNEUSDT','KLAYUSDT','MINAUSDT','QNTUSDT','LDOUSDT','SUIUSDT',
    'SEIUSDT','TIAUSDT','INJUSDT','TIAUSD_PERP','WIFUSDT','ORDIUSDT'
]
