#!/usr/bin/env python3
"""
Neko Sentinel - Binance Futures Scanner v7
Combined: Momentum (Hot Coins) + Technical Analysis
"""

import hmac, hashlib, time, requests, json, os
from datetime import datetime

# Config
import os
from pathlib import Path

env_file = Path(__file__).parent / "binance-futures" / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, val = line.split('=', 1)
                os.environ.setdefault(key.strip(), val.strip())

API_KEY = os.environ.get("BINANCE_API_KEY", "")
SECRET = os.environ.get("BINANCE_SECRET", "")
TELEGRAM_CHANNEL = os.environ.get("TELEGRAM_CHANNEL", "-1003847994290")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

# Trading config
LEVERAGE = 10
MAX_POSITIONS = 8
MAX_MARGIN_PERCENT = 40
ENTRY_PERCENT = 5

# Strategy Config
USE_MOMENTUM = True
MOMENTUM_MIN_GAIN = 2.0
MOMENTUM_MAX_GAIN = 20.0
MOMENTUM_RR = 2.0

USE_TECHNICAL = True
TECH_MIN_GAIN = 0.5

# Load symbols
with open('/root/.openclaw/workspace/binance-futures/futures_symbols.json') as f:
    SYMBOLS = json.load(f)

SYMBOLS = [s for s in SYMBOLS if 'USDT' in s and 'USDC' not in s and len(s) < 20][:200]

def get_signature(params):
    return hmac.new(SECRET.encode(), params.encode(), hashlib.sha256).hexdigest()

def get_balance():
    ts = int(time.time() * 1000)
    params = "timestamp={}".format(ts)
    sig = get_signature(params)
    r = requests.get("https://fapi.binance.com/fapi/v3/account?{}&signature={}".format(params, sig),
                     headers={"X-MBX-APIKEY": API_KEY}, timeout=15)
    if r:
        try:
            return float(r.json().get('availableBalance', 0))
        except:
            return 0
    return 0

def get_positions():
    ts = int(time.time() * 1000)
    params = "timestamp={}".format(ts)
    sig = get_signature(params)
    r = requests.get("https://fapi.binance.com/fapi/v2/positionRisk?{}&signature={}".format(params, sig),
                     headers={"X-MBX-APIKEY": API_KEY}, timeout=15)
    if r:
        try:
            return r.json()
        except:
            return []
    return []

def set_leverage(symbol, leverage=10):
    ts = int(time.time() * 1000)
    params = "symbol={}&leverage={}&timestamp={}".format(symbol, leverage, ts)
    sig = get_signature(params)
    try:
        requests.post("https://fapi.binance.com/fapi/v1/leverage?{}&signature={}".format(params, sig),
                      headers={"X-MBX-APIKEY": API_KEY}, timeout=15)
    except:
        pass

def get_precision(symbol):
    try:
        r = requests.get("https://fapi.binance.com/fapi/v1/exchangeInfo", timeout=10)
        data = r.json()
        for s in data.get('symbols', []):
            if s.get('symbol') == symbol:
                return s.get('quantityPrecision', 3)
    except:
        pass
    return 3

def get_24h_stats():
    try:
        r = requests.get("https://fapi.binance.com/fapi/v1/ticker/24hr", timeout=10)
        return {t['symbol']: t for t in r.json() if t.get('symbol', '').endswith('USDT')}
    except:
        return {}

def place_order(symbol, side, quantity, tp_price=None, sl_price=None):
    ts = int(time.time() * 1000)
    set_leverage(symbol, LEVERAGE)
    precision = get_precision(symbol)
    quantity = round(quantity, precision)
    
    # Place market order
    params = "symbol={}&side={}&quantity={}&type=MARKET&timestamp={}".format(symbol, side, quantity, ts)
    sig = get_signature(params)
    
    try:
        r = requests.post("https://fapi.binance.com/fapi/v1/order?{}&signature={}".format(params, sig),
                         headers={"X-MBX-APIKEY": API_KEY}, timeout=15)
        if r.status_code == 200:
            result = r.json()
            
            # Set TP/SL if provided
            if tp_price or sl_price:
                time.sleep(1)  # Wait for order to fill
                set_tp_sl(symbol, side, quantity, tp_price, sl_price)
            
            return result
        else:
            return None
    except:
        return None

def set_tp_sl(symbol, side, quantity, tp_price, sl_price):
    """Set Take Profit and Stop Loss"""
    ts = int(time.time() * 1000)
    
    # Set Take Profit
    if tp_price:
        tp_side = "SELL" if side == "BUY" else "BUY"
        tp_params = "symbol={}&side={}&quantity={}&type=LIMIT&price={}&stopPrice={}&timeInForce=GTC&workType=STOP_MARKET&timestamp={}".format(
            symbol, tp_side, quantity, tp_price, tp_price, ts
        )
        tp_sig = get_signature(tp_params)
        try:
            r = requests.post("https://fapi.binance.com/fapi/v1/order?{}&signature={}".format(tp_params, tp_sig),
                            headers={"X-MBX-APIKEY": API_KEY}, timeout=15)
            print("    TP set: ${}".format(tp_price))
        except:
            pass
    
    # Set Stop Loss
    if sl_price:
        sl_side = "SELL" if side == "BUY" else "BUY"
        sl_params = "symbol={}&side={}&quantity={}&type=LIMIT&price={}&stopPrice={}&timeInForce=GTC&workType=STOP_MARKET&timestamp={}".format(
            symbol, sl_side, quantity, sl_price, sl_price, ts
        )
        sl_sig = get_signature(sl_params)
        try:
            r = requests.post("https://fapi.binance.com/fapi/v1/order?{}&signature={}".format(sl_params, sl_sig),
                            headers={"X-MBX-APIKEY": API_KEY}, timeout=15)
            print("    SL set: ${}".format(sl_price))
        except:
            pass

def get_klines(symbol, interval='1h', limit=200):
    url = "https://api.binance.com/api/v3/klines?symbol={}&interval={}&limit={}".format(symbol, interval, limit)
    r = requests.get(url, timeout=10)
    if not r:
        return []
    try:
        return [[float(c[1]), float(c[2]), float(c[3]), float(c[4]), float(c[5])] for c in r.json()]
    except:
        return []

def get_volume_data(symbol, interval='1h', limit=50):
    candles = get_klines(symbol, interval, limit)
    if not candles:
        return {}
    volumes = [c[4] for c in candles]
    avg_volume = sum(volumes) / len(volumes) if volumes else 0
    recent_avg = sum(volumes[-5:]) / 5 if volumes else 0
    return {'avg_volume': avg_volume, 'recent_volume': recent_avg, 'spike': recent_avg > avg_volume * 1.5}

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
    if len(candles) < period + 1:
        return None
    try:
        trs = []
        for i in range(1, min(period+1, len(candles))):
            high = candles[-i][1]
            low = candles[-i][2]
            prev_close = candles[-i-1][3]
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            trs.append(tr)
        return sum(trs) / len(trs) if trs else None
    except:
        return None

def check_market_structure(candles):
    if len(candles) < 20:
        return None
    highs = [c[1] for c in candles[-20:]]
    lows = [c[2] for c in candles[-20:]]
    recent_highs, recent_lows = highs[-5:], lows[-5:]
    hh = recent_highs[-1] > recent_highs[-2] > recent_highs[-3]
    hl = recent_lows[-1] > recent_lows[-2] > recent_lows[-3]
    lh = recent_highs[-1] < recent_highs[-2] < recent_highs[-3]
    ll = recent_lows[-1] < recent_lows[-2] < recent_lows[-3]
    if hh and hl: return "UPTREND"
    elif lh and ll: return "DOWNTREND"
    return "CONSOLIDATION"

def analyze_momentum(symbol, stats, candles, closes):
    if not USE_MOMENTUM:
        return None
    try:
        stat = stats.get(symbol, {})
        price_change = float(stat.get('priceChangePercent', 0))
        
        if price_change < MOMENTUM_MIN_GAIN or price_change > MOMENTUM_MAX_GAIN:
            return None
        
        current = float(stat.get('lastPrice', 0))
        if not current:
            return None
        
        ema_50 = calculate_ema(closes, 50)
        if not ema_50:
            return None
        
        direction = "LONG" if current > ema_50 else "SHORT"
        
        atr = calculate_atr(candles, 14)
        if not atr:
            return None
        
        if direction == "LONG":
            sl = current - (atr * 1.5)
            tp = current + (atr * MOMENTUM_RR * 1.5)
        else:
            sl = current + (atr * 1.5)
            tp = current - (atr * MOMENTUM_RR * 1.5)
        
        vol_data = get_volume_data(symbol)
        vol_confirm = "Volume Spike" if vol_data.get('spike') else ""
        
        return {
            'strategy': 'MOMENTUM',
            'symbol': symbol,
            'direction': direction,
            'current': current,
            'change_24h': price_change,
            'sl': sl,
            'tp': tp,
            'tp2': tp * 1.2,
            'atr': atr,
            'volume_info': vol_confirm,
            'pattern_info': '',
            'insight': "HOT COIN - {}% today! Riding momentum. {}".format(price_change, vol_confirm)
        }
    except:
        return None

def analyze_technical(symbol, stats, candles, closes):
    if not USE_TECHNICAL:
        return None
    try:
        stat = stats.get(symbol, {})
        price_change = float(stat.get('priceChangePercent', 0))
        
        if abs(price_change) < TECH_MIN_GAIN:
            return None
        
        highs = [c[1] for c in candles]
        lows = [c[2] for c in candles]
        current = closes[-1]
        
        ema_21 = calculate_ema(closes, 21)
        ema_50 = calculate_ema(closes, 50)
        ema_200 = calculate_ema(closes, 200)
        
        if not ema_21 or not ema_50 or not ema_200:
            return None
        
        structure = check_market_structure(candles)
        
        resistance = max(highs[-50:])
        support = min(lows[-50:])
        range_height = resistance - support
        
        trend = "BULLISH" if current > ema_200 else "BEARISH"
        
        # RSI
        try:
            gains, losses = 0, 0
            for i in range(1, 15):
                if i >= len(closes): break
                diff = closes[-i] - closes[-i-1]
                if diff > 0: gains += diff
                else: losses -= diff
            avg_gain = gains/14 if gains else 0
            avg_loss = losses/14 if losses else 0
            rsi = 100 - (100/(1+(avg_gain/avg_loss))) if avg_loss > 0 else 50
        except:
            rsi = 50
        
        direction = None
        entry = current
        sl = None
        tp1 = None
        insight = ""
        
        if current > ema_200:  # Uptrend
            if (current - support) / current * 100 < 5:
                direction = "LONG"
                sl = support * 0.98
                tp1 = current + (range_height * 1.272)
                insight = "Trend LONG + Support Bounce. RSI: {:.1f}".format(rsi)
            elif (resistance - current) / current * 100 < 5:
                direction = "LONG"
                entry = resistance * 1.002
                sl = ema_21
                tp1 = entry + (range_height * 1.272)
                insight = "Trend LONG + Breakout Setup. RSI: {:.1f}".format(rsi)
        else:  # Downtrend
            if (resistance - current) / current * 100 < 5:
                direction = "SHORT"
                sl = resistance * 1.02
                tp1 = current - (range_height * 1.272)
                insight = "Trend SHORT + Resistance. RSI: {:.1f}".format(rsi)
            elif (current - support) / current * 100 < 5:
                direction = "SHORT"
                entry = support * 0.998
                sl = ema_21
                tp1 = entry - (range_height * 1.272)
                insight = "Trend SHORT + Breakdown. RSI: {:.1f}".format(rsi)
        
        if not direction:
            return None
        
        atr = calculate_atr(candles, 14) or 0
        vol_data = get_volume_data(symbol)
        
        # Pattern
        pattern = ""
        if len(candles) >= 3:
            if candles[-1][2] > candles[-2][2] and candles[-1][1] < candles[-2][1]:
                pattern = "INSIDE_BAR"
        
        return {
            'strategy': 'TECHNICAL',
            'symbol': symbol,
            'direction': direction,
            'current': entry,
            'change_24h': price_change,
            'sl': sl,
            'tp': tp1,
            'tp2': entry + (range_height * 1.618) if direction == "LONG" else entry - (range_height * 1.618),
            'atr': atr,
            'rsi': rsi,
            'ema_21': ema_21,
            'ema_50': ema_50,
            'ema_200': ema_200,
            'trend': trend,
            'structure': structure,
            'support': support,
            'resistance': resistance,
            'range': range_height,
            'volume_info': "Volume Spike" if vol_data.get('spike') else "",
            'pattern_info': pattern,
            'insight': insight
        }
    except:
        return None

def format_signal(analysis, order_result=None):
    s = analysis
    symbol = s['symbol'].replace('USDT', '')
    emoji = "🟢" if s['direction'] == "LONG" else "🔴"
    
    # Build message
    msg = "{0} {1} SIGNAL {0}\n\n".format(emoji, s['direction'])
    msg += "📈 {}USDT TECHNICAL ANALYSIS 📊\n".format(symbol)
    msg += "📊 Chart: https://www.tradingview.com/chart/?symbol=BINANCE:{}USDT\n\n".format(symbol)
    
    if s.get('rsi'):
        msg += "📐 MULTI-TF CONFIRMATION:\n"
        msg += "• Trend 1H: {}\n".format(s.get('trend', 'N/A'))
        msg += "• Trend 4H: N/A\n"
        msg += "• Structure: {}\n".format(s.get('structure', 'N/A'))
        msg += "📊 24h Change: {:.2f}%\n\n".format(s.get('change_24h', 0))
        
        msg += "📐 INDICATORS:\n"
        msg += "• RSI (14): {:.1f}\n".format(s.get('rsi', 0))
        msg += "• EMA 21: {:.6f}\n".format(s.get('ema_21', 0))
        msg += "• EMA 50: {:.6f}\n".format(s.get('ema_50', 0))
        msg += "• EMA 200: {:.6f}\n".format(s.get('ema_200', 0))
        msg += "• ATR: {:.6f}\n\n".format(s.get('atr', 0))
        
        vol = s.get('volume_info', '')
        msg += "🔊 VOLUME: {}\n".format(vol if vol else "N/A")
        
        pat = s.get('pattern_info', '')
        msg += "🕯 PATTERNS: {}\n\n".format(pat if pat else "N/A")
        
        msg += "📊 STRUCTURE:\n"
        msg += "• Support: {:.6f}\n".format(s.get('support', 0))
        msg += "• Resistance: {:.6f}\n".format(s.get('resistance', 0))
        msg += "• Range: {:.6f}\n\n".format(s.get('range', 0))
    
    msg += "💡 INSIGHT: {}\n".format(s['insight'])
    msg += "🎯 Entry: ${:.6f}\n".format(s['current'])
    msg += "📈 TP1: ${:.6f} (Fib 1.272)\n".format(s['tp'])
    msg += "📈 TP2: ${:.6f} (Fib 1.618)\n".format(s.get('tp2', s['tp']))
    msg += "🛡 SL: ${:.6f}\n".format(s['sl'])
    msg += "⏰ Timeframe: 1H"
    
    if order_result:
        msg += "\n\n✅ ORDER EXECUTED: {}".format(s['direction'])
        msg += "\n📋 Order ID: {} | Status: {}".format(order_result.get('orderId', 'N/A'), order_result.get('status', 'NEW'))
    
    return msg

def send_telegram(message):
    if not TELEGRAM_BOT_TOKEN:
        return False
    url = "https://api.telegram.org/bot{}/sendMessage".format(TELEGRAM_BOT_TOKEN)
    try:
        r = requests.post(url, data={'chat_id': TELEGRAM_CHANNEL, 'text': message}, timeout=30)
        return r.status_code == 200
    except:
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
print("🔍 Scanner v7 [MOMENTUM + TECHNICAL] Starting...")
print("  Momentum: ON (2-20% hot coins)")
print("  Technical: ON (Multi-TF)")

balance = get_balance()
print("  Balance: ${:.2f}".format(balance))

positions = get_positions()
open_count = len([p for p in positions if float(p.get('positionAmt', 0)) != 0])
print("  Open: {}/{}".format(open_count, MAX_POSITIONS))

print("\n📊 Fetching market data...")
stats_24h = get_24h_stats()
print("  Found {} symbols".format(len(stats_24h)))

# Scan
last_signals = load_last_signals()
new_signals = {}
signals_found = 0

for i, symbol in enumerate(SYMBOLS):
    if open_count >= MAX_POSITIONS:
        print("⚠️ Max positions reached")
        break
    
    print("  [{}/{}] {}...".format(i+1, len(SYMBOLS), symbol), end=" ", flush=True)
    
    candles = get_klines(symbol, '1h', 200)
    if not candles or len(candles) < 20:
        print("(no data)")
        continue
    
    closes = [c[3] for c in candles]
    current = closes[-1]
    
    # Try momentum first
    analysis = analyze_momentum(symbol, stats_24h, candles, closes)
    strategy = "MOMENTUM"
    
    if not analysis and USE_TECHNICAL:
        analysis = analyze_technical(symbol, stats_24h, candles, closes)
        strategy = "TECHNICAL"
    
    if analysis:
        signal_key = "{}_{}_{}".format(symbol, analysis['direction'], strategy)
        
        if signal_key not in last_signals:
            trade_amount = (balance * ENTRY_PERCENT / 100) * LEVERAGE
            quantity = round(trade_amount / analysis['current'], 3)
            
            side = "BUY" if analysis['direction'] == "LONG" else "SELL"
            prefix = "🔥" if strategy == "MOMENTUM" else "📈"
            print("{} {}...".format(prefix, side), end=" ")
            
            # Get TP/SL from analysis
            tp_price = analysis.get('tp')
            sl_price = analysis.get('sl')
            
            order_result = place_order(symbol, side, quantity, tp_price, sl_price)
            
            if order_result:
                msg = format_signal(analysis, order_result)
                if send_telegram(msg):
                    print("✅ Done!")
                    open_count += 1
                    signals_found += 1
                else:
                    print("❌ Post failed")
            else:
                print("❌ Order failed")
            
            new_signals[signal_key] = analysis['insight'][:50]
        else:
            print("(already)")
            new_signals[signal_key] = last_signals.get(signal_key, "")
    else:
        print("(no signal)")

save_last_signals(new_signals)
print("\n✅ Scan complete! Found {} signals!".format(signals_found))
