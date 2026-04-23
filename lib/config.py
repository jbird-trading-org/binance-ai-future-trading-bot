# === Neko Futures Trader - CONFIGURATION ===
# Scanner v1.0.40 - Percentage-based SL/TP

# ── TRADING ──────────────────────────────────────────────────────────────────
LEVERAGE = 10                    # Futures leverage (10x)
MAX_POSITIONS = 5                # Max concurrent positions
AUTO_FILL_EMPTY_SLOTS = True     # Auto-find entries when positions < MAX
ENTRY_PERCENT = 6                # % of balance per trade

# ── SL/TP STRATEGY ────────────────────────────────────────────────────────────
# Percentage-based: PRICE_SL / PRICE_TP

PRICE_TP = 15.0                  # Take Profit: +15% for LONG, -15% for SHORT
PRICE_SL = 5.0                   # Stop Loss: -5% for LONG, +5% for SHORT

# ── BREAKEVEN & TRAILING ─────────────────────────────────────────────────────
MIN_PROFIT_BREAKEVEN = 5.0       # % profit to move SL to entry price
MIN_PROFIT_TRAILING_TP = 10.0    # % profit to activate trailing TP
TRAIL_PERCENT = 2.0              # Trail SL by this % when trailing

# ── NOTIFICATIONS ─────────────────────────────────────────────────────────────
POST_SIGNALS_TO_TELEGRAM = True
NOTIFY_ON_OPEN = True
NOTIFY_ON_CLOSE = True
NOTIFY_ON_BREAKEVEN = True
NOTIFY_ON_TRAILING_TP = True

# ── SCANNER ──────────────────────────────────────────────────────────────────
SCAN_INTERVAL = 300             # Scanner run every 5 minutes
MIN_PRICE_CHANGE = 3.0          # Min % price change for signal
MIN_SCORE = 3                    # Min signal score (1-10)
SKIP_RECENT_HOURS = 24           # Skip re-entry for 24h after close

# ── RISK ─────────────────────────────────────────────────────────────────────
MAX_MARGIN_PERCENT = 40          # Max margin usage %
MAX_RISK_PERCENT = 1.5           # Max risk per trade %

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
