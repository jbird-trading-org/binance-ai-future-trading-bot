#!/usr/bin/env python3
"""
Neko Sentinel - Binance Futures Signal Scanner v3
Improved Framework:
- Multi-timeframe confirmation (1H + 4H)
- Volume analysis
- Market structure (HH/HL or LH/LL)
- ATR-based SL
- Better entry filters
"""

import hmac, hashlib, time, requests, json, os
from datetime import datetime

# Config
API_KEY = 'Vi9YDQ8qFK4a3he1vbv9gXFYYok75CK3GlU21LmkPZRf0Y8dAWQicqtKic8AEKPp'
SECRET = 'f6wzxpMtieMkEqBLxDwswocfQCvSSpxEFbggF9T9s6zjYet62NlXfHKCxQq4pdN7'
TELEGRAM_CHANNEL = "-1003847994290"
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

# Trading config
LEVERAGE = 10
MAX_POSITIONS = 8
MAX_MARGIN_PERCENT = 40
ENTRY_PERCENT = 5
TEST_MODE = False

# Load symbols
with open('/root/.openclaw/workspace/binance-futures/futures_symbols.json') as f:
    SYMBOLS = json.load(f)

SYMBOLS = [s for s in SYMBOLS if 'USDT' in s and 'USDC' not in s and len(s) < 20][:40]

def get_signature(params):
    return hmac.new(SECRET.encode(), params.encode(), hashlib.sha256).hexdigest()

def get_balance():
    ts = int(time.time() * 1000)
    params = f"timestamp={ts}"
    sig = get_signature(params)
    r = requests.get(f"https://fapi.binance.com/fapi/v3/account?{params}&signature={sig}",
                     headers={"X-MBX-APIKEY": API_KEY}, timeout=15)
    if r:
        try:
            return float(r.json().get('availableBalance', 0))
        except:
            return 0
    return 0

def get_positions():
    ts = int(time.time() * 1000)
    params = f"timestamp={ts}"
    sig = get_signature(params)
    r = requests.get(f"https://fapi.binance.com/fapi/v2/positionRisk?{params}&signature={sig}",
                     headers={"X-MBX-APIKEY": API_KEY}, timeout=15)
    if r:
        try:
            return r.json()
        except:
            return []
    return []

def set_leverage(symbol, leverage=10):
    ts = int(time.time() * 1000)
    params = f"symbol={symbol}&leverage={leverage}&timestamp={ts}"
    sig = get_signature(params)
    try:
        r = requests.post(f"https://fapi.binance.com/fapi/v1/leverage?{params}&signature={sig}",
                          headers={"X-MBX-APIKEY": API_KEY}, timeout=15)
        return r is not None
    except:
        return False

def place_order(symbol, side, quantity):
    ts = int(time.time() * 1000)
    set_leverage(symbol, LEVERAGE)
    
    # Add order type (MARKET)
    params = f"symbol={symbol}&side={side}&quantity={quantity}&type=MARKET&timestamp={ts}"
    sig = get_signature(params)
    
    if TEST_MODE:
        print(f"  [TEST] Would {side} {quantity} {symbol}")
        return {"orderId": "test123", "status": "NEW"}
    
    try:
        r = requests.post(f"https://fapi.binance.com/fapi/v1/order?{params}&signature={sig}",
                          headers={"X-MBX-APIKEY": API_KEY}, timeout=15)
        if r.status_code == 200:
            return r.json()
        else:
            print(f"  Order error: {r.text}")
            return None
    except Exception as e:
        print(f"  Order exception: {e}")
        return None

def get_klines(symbol, interval='1h', limit=200):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    r = requests.get(url, timeout=10)
    if not r:
        return []
    try:
        # [open, high, low, close, volume]
        return [[float(c[1]), float(c[2]), float(c[3]), float(c[4]), float(c[5])] for c in r.json()]
    except:
        return []

def get_volume(symbol, interval='1h', limit=50):
    """Get average volume"""
    candles = get_klines(symbol, interval, limit)
    if not candles:
        return 0
    volumes = [c[4] for c in candles]
    return sum(volumes) / len(volumes)

def calculate_ema(prices, period=50):
    if len(prices) < period: return None
    try:
        mul = 2/(period+1)
        ema = sum(prices[:period])/period
        for p in prices[period:]: 
            if p is None: continue
            ema = (p-ema)*mul + ema
        return ema
    except:
        return None

def calculate_atr(candles, period=14):
    """Calculate Average True Range"""
    if len(candles) < period + 1:
        return None
    try:
        trs = []
        for i in range(1, min(period+1, len(candles))):
            high = candles[-i][1]
            low = candles[-i][2]
            prev_close = candles[-i-1][3]
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            trs.append(tr)
        return sum(trs) / len(trs) if trs else None
    except:
        return None

def check_market_structure(candles):
    """Check for Higher Highs/Lower Lows (trend confirmation)"""
    if len(candles) < 20:
        return None
    
    highs = [c[1] for c in candles[-20:]]
    lows = [c[2] for c in candles[-20:]]
    
    # Check last 5 candles
    recent_highs = highs[-5:]
    recent_lows = lows[-5:]
    
    # Higher Highs + Higher Lows = Uptrend
    hh = recent_highs[-1] > recent_highs[-2] > recent_highs[-3]
    hl = recent_lows[-1] > recent_lows[-2] > recent_lows[-3]
    
    # Lower Highs + Lower Lows = Downtrend
    lh = recent_highs[-1] < recent_highs[-2] < recent_highs[-3]
    ll = recent_lows[-1] < recent_lows[-2] < recent_lows[-3]
    
    if hh and hl:
        return "UPTREND"
    elif lh and ll:
        return "DOWNTREND"
    else:
        return "CONSOLIDATION"

def analyze_symbol(symbol):
    try:
        # Get 1H and 4H data
        candles_1h = get_klines(symbol, '1h', 200)
        candles_4h = get_klines(symbol, '4h', 100)
        
        if not candles_1h or len(candles_1h) < 50:
            return None
        
        closes_1h = [c[3] for c in candles_1h]
        highs_1h = [c[1] for c in candles_1h]
        lows_1h = [c[2] for c in candles_1h]
        current = closes_1h[-1]
        
        # Get 4H trend if available
        trend_4h = None
        if candles_4h and len(candles_4h) >= 50:
            closes_4h = [c[3] for c in candles_4h]
            ema_200_4h = calculate_ema(closes_4h, 200)
            if ema_200_4h:
                trend_4h = "BULLISH" if closes_4h[-1] > ema_200_4h else "BEARISH"
        
        # EMAs (1H)
        ema_21 = calculate_ema(closes_1h, 21)
        ema_50 = calculate_ema(closes_1h, 50)
        ema_200 = calculate_ema(closes_1h, 200)
        
        if not ema_21 or not ema_50 or not ema_200:
            return None
        
        # ATR for dynamic SL
        atr = calculate_atr(candles_1h, 14)
        
        # Market structure
        structure = check_market_structure(candles_1h)
        
        # RSI
        try:
            gains, losses = 0, 0
            for i in range(1, 15):
                if i >= len(closes_1h): break
                diff = closes_1h[-i] - closes_1h[-i-1]
                if diff > 0: gains += diff
                else: losses -= diff
            avg_gain = gains/14 if gains else 0
            avg_loss = losses/14 if losses else 0
            rsi = 100 - (100/(1+(avg_gain/avg_loss))) if avg_loss > 0 else 100
        except:
            rsi = 50
        
        # S/R
        resistance = max(highs_1h[-50:])
        support = min(lows_1h[-50:])
        range_height = resistance - support
        
        # Volume check
        avg_volume = get_volume(symbol, '1h', 20)
        
        # Trend from EMA-200
        ema_trend = "BULLISH" if current > ema_200 else "BEARISH"
        
        # FILTER: Only trade if aligned with 4H trend
        if trend_4h and trend_4h != ema_trend:
            return None  # Reject conflicting timeframes
        
        # FILTER: Need market structure alignment
        if structure == "UPTREND" and ema_trend != "BULLISH":
            return None
        if structure == "DOWNTREND" and ema_trend != "BEARISH":
            return None
        
        # Entry zones with ATR-based SL
        direction = None
        entry = current
        sl = None
        tp1 = None
        tp2 = None
        insight = ""
        
        if current > ema_200:  # Uptrend
            # Support bounce
            if (current - support) / current * 100 < 3:
                direction = "LONG"
                entry = current
                # ATR-based SL (1.5x ATR below support)
                sl_price = min(support * 0.98, current - (atr * 1.5)) if atr else support * 0.98
                sl = sl_price
                tp1 = current + (range_height * 1.272)
                tp2 = current + (range_height * 1.618)
                insight = f"LONG - EMA-200 confirms uptrend. Support bounce + {structure}. RSI: {rsi:.1f}"
            
            # Breakout
            elif (resistance - current) / current * 100 < 5:
                direction = "LONG"
                entry = resistance * 1.002
                sl = min(ema_21, current - (atr * 1.5)) if atr else ema_21
                tp1 = entry + (range_height * 1.272)
                tp2 = entry + (range_height * 1.618)
                insight = f"LONG - Breakout above resistance + {structure}. RSI: {rsi:.1f}"
            else:
                return None
        else:  # Downtrend
            # Resistance rejection
            if (resistance - current) / current * 100 < 3:
                direction = "SHORT"
                entry = current
                sl_price = max(resistance * 1.02, current + (atr * 1.5)) if atr else resistance * 1.02
                sl = sl_price
                tp1 = current - (range_height * 1.272)
                tp2 = current - (range_height * 1.618)
                insight = f"SHORT - EMA-200 confirms downtrend. Resistance rejection + {structure}. RSI: {rsi:.1f}"
            
            # Breakdown
            elif (current - support) / current * 100 < 5:
                direction = "SHORT"
                entry = support * 0.998
                sl = max(ema_21, current + (atr * 1.5)) if atr else ema_21
                tp1 = entry - (range_height * 1.272)
                tp2 = entry - (range_height * 1.618)
                insight = f"SHORT - Breakdown below support + {structure}. RSI: {rsi:.1f}"
            else:
                return None
        
        return {
            'symbol': symbol,
            'current': current,
            'ema_21': ema_21,
            'ema_50': ema_50,
            'ema_200': ema_200,
            'rsi': rsi,
            'atr': atr or 0,
            'trend_1h': ema_trend,
            'trend_4h': trend_4h or "N/A",
            'structure': structure,
            'support': support,
            'resistance': resistance,
            'range': range_height,
            'entry': entry,
            'tp1': tp1,
            'tp2': tp2,
            'sl': sl,
            'insight': insight,
            'direction': direction
        }
    except:
        return None

def format_signal(analysis, order_result=None):
    s = analysis
    symbol = s['symbol'].replace('USDT', '')
    
    order_info = ""
    if order_result:
        status = order_result.get('status', 'UNKNOWN')
        order_id = order_result.get('orderId', 'N/A')
        order_info = f"\n\n✅ ORDER EXECUTED: {s['direction']}\n📋 Order ID: {order_id} | Status: {status}"
    
    emoji = "🟢" if s['direction'] == "LONG" else "🔴"
    
    msg = f"""{emoji} {s['direction']} SIGNAL {emoji}

📈 {symbol}USDT TECHNICAL ANALYSIS 📊
📊 Chart: https://www.tradingview.com/chart/?symbol=BINANCE:{symbol}USDT
📐 MULTI-TF CONFIRMATION:
• Trend 1H: {s['trend_1h']}
• Trend 4H: {s['trend_4h']}
• Structure: {s['structure']}
📐 INDICATORS:
• RSI (14): {s['rsi']:.1f}
• EMA 21: {s['ema_21']:.6f}
• EMA 50: {s['ema_50']:.6f}
• EMA 200: {s['ema_200']:.6f}
• ATR: {s['atr']:.6f}
📊 STRUCTURE:
• Support: {s['support']:.6f}
• Resistance: {s['resistance']:.6f}
• Range: {s['range']:.6f}
💡 INSIGHT: {s['insight']}
🎯 Entry: ${s['entry']:.6f}
📈 TP1: ${s['tp1']:.6f} (Fib 1.272)
📈 TP2: ${s['tp2']:.6f} (Fib 1.618)
🛡 SL: ${s['sl']:.6f} (ATR-based)
⏰ Timeframe: 1H{order_info}"""
    
    return msg

def send_telegram(message):
    if not TELEGRAM_BOT_TOKEN:
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {'chat_id': TELEGRAM_CHANNEL, 'text': message}
    try:
        r = requests.post(url, data=data, timeout=30)
        return r.status_code == 200
    except Exception as e:
        print(f"  Telegram error: {e}")
        return False

LAST_SIGNALS_FILE = '/root/.openclaw/workspace/.last_signals.json'
def load_last_signals():
    try:
        with open(LAST_SIGNALS_FILE) as f:
            return json.load(f)
    except:
        return {}

def save_last_signals(signals):
    with open(LAST_SIGNALS_FILE, 'w') as f:
        json.dump(signals, f)

# Main
print(f"🔍 Scanning {len(SYMBOLS)} symbols [v3 - IMPROVED FRAMEWORK]...")
print(f"  {'🧪 TEST' if TEST_MODE else '🚀 LIVE'}")
print(f"  Filters: Multi-TF + Structure + ATR SL")

balance = get_balance()
print(f"  Balance: ${balance:.2f}")

positions = get_positions()
open_count = len([p for p in positions if float(p.get('positionAmt', 0)) != 0])
print(f"  Open: {open_count}/{MAX_POSITIONS}")

last_signals = load_last_signals()
new_signals = {}

for i, symbol in enumerate(SYMBOLS):
    if open_count >= MAX_POSITIONS:
        print(f"⚠️ Max positions reached")
        break
    
    print(f"  [{i+1}/{len(SYMBOLS)}] {symbol}...", end=" ", flush=True)
    analysis = analyze_symbol(symbol)
    
    if analysis:
        signal_key = f"{symbol}_{analysis['direction']}"
        
        if signal_key not in last_signals:
            # Calculate position size
            trade_amount = (balance * ENTRY_PERCENT / 100) * LEVERAGE
            quantity = round(trade_amount / analysis['current'], 3)
            
            # Execute trade
            side = "BUY" if analysis['direction'] == "LONG" else "SELL"
            print(f"Executing {side}...", end=" ")
            order_result = place_order(symbol, side, quantity)
            
            # Only post if order executed successfully
            if order_result:
                msg = format_signal(analysis, order_result)
                print(f"Posting...", end=" ")
                sent = send_telegram(msg)
                if sent:
                    print(f"✅ Done!")
                    open_count += 1
                else:
                    print(f"❌ Post failed")
                new_signals[signal_key] = msg[:50]
            else:
                print(f"❌ Order failed, not posting")
                new_signals[signal_key] = last_signals.get(signal_key, "")
            
            new_signals[signal_key] = msg[:50]
        else:
            print(f"(already posted)")
            new_signals[signal_key] = last_signals[signal_key]
    else:
        print(f"(no signal)")
        signal_key = f"{symbol}_LONG"
        new_signals[signal_key] = last_signals.get(f"{symbol}_LONG", "")

save_last_signals(new_signals)
print("✅ Scan complete!")
