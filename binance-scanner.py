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
    """Get comprehensive volume analysis"""
    candles = get_klines(symbol, interval, limit)
    if not candles:
        return {'volume_info': '', 'obv': 0, 'vwap': 0}
    
    volumes = [c[4] for c in candles]
    closes = [c[3] for c in candles]
    
    avg_volume = sum(volumes) / len(volumes) if volumes else 0
    recent_avg = sum(volumes[-5:]) / 5 if volumes else 0
    
    # Volume spike/drop
    spike = recent_avg > avg_volume * 1.5
    drop = recent_avg < avg_volume * 0.5
    
    # OBV (On Balance Volume)
    obv = 0
    for i in range(1, len(candles)):
        if closes[i] > closes[i-1]:
            obv += volumes[i]
        elif closes[i] < closes[i-1]:
            obv -= volumes[i]
    
    # VWAP (Volume Weighted Average Price)
    vwap = 0
    tp_sum = 0
    vol_sum = 0
    for i in range(-20, 0):
        typical_price = (candles[i][1] + candles[i][2] + candles[i][3]) / 3
        tp_sum += typical_price * volumes[i]
        vol_sum += volumes[i]
    vwap = tp_sum / vol_sum if vol_sum > 0 else 0
    
    # Build volume info string
    info_parts = []
    if spike:
        info_parts.append("VOLUME_SPIKE")
    if drop:
        info_parts.append("VOLUME_DROP")
    if obv > 0:
        info_parts.append("OBV_UP")
    elif obv < 0:
        info_parts.append("OBV_DOWN")
    if vwap > 0 and closes[-1] > vwap:
        info_parts.append("PRICE_ABOVE_VWAP")
    elif vwap > 0 and closes[-1] < vwap:
        info_parts.append("PRICE_BELOW_VWAP")
    
    return {
        'volume_info': ", ".join(info_parts) if info_parts else "NORMAL",
        'avg_volume': avg_volume,
        'recent_volume': recent_avg,
        'spike': spike,
        'drop': drop,
        'obv': obv,
        'vwap': vwap
    }

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

def calculate_sma(prices, period=20):
    """Simple Moving Average"""
    if len(prices) < period: return None
    return sum(prices[-period:]) / period

def calculate_macd(prices, fast=12, slow=26, signal=9):
    """MACD - Moving Average Convergence Divergence"""
    if len(prices) < slow: return None
    try:
        ema_fast = calculate_ema(prices, fast)
        ema_slow = calculate_ema(prices, slow)
        if not ema_fast or not ema_slow: return None
        
        macd_line = ema_fast - ema_slow
        
        # Signal line (EMA of MACD)
        # Approximate with simple calculation
        signal_line = macd_line * 0.9  # Simplified
        
        histogram = macd_line - signal_line
        
        return {'macd': macd_line, 'signal': signal_line, 'histogram': histogram}
    except:
        return None

def calculate_stochastic(candles, k_period=14, d_period=3):
    """Stochastic Oscillator"""
    if len(candles) < k_period: return None
    try:
        highs = [c[1] for c in candles]
        lows = [c[2] for c in candles]
        closes = [c[3] for c in candles]
        
        highest = max(highs[-k_period:])
        lowest = min(lows[-k_period:])
        
        if highest == lowest: return None
        
        k = 100 * (closes[-1] - lowest) / (highest - lowest)
        
        # %D is SMA of %K
        d = k  # Simplified
        
        return {'k': k, 'd': d}
    except:
        return None

def calculate_bollinger_bands(prices, period=20, std_dev=2):
    """Bollinger Bands"""
    if len(prices) < period: return None
    try:
        sma = calculate_sma(prices, period)
        if not sma: return None
        
        variance = sum((p - sma) ** 2 for p in prices[-period:]) / period
        std = variance ** 0.5
        
        upper = sma + (std_dev * std)
        lower = sma - (std_dev * std)
        
        return {'upper': upper, 'middle': sma, 'lower': lower}
    except:
        return None

def calculate_adx(candles, period=14):
    """Average Directional Index - Trend strength"""
    if len(candles) < period * 2: return None
    try:
        highs = [c[1] for c in candles]
        lows = [c[2] for c in candles]
        closes = [c[3] for c in candles]
        
        plus_dm = []
        minus_dm = []
        tr = []
        
        for i in range(1, min(period * 2, len(candles))):
            high_diff = highs[i] - highs[i-1]
            low_diff = lows[i-1] - lows[i]
            
            if high_diff > low_diff and high_diff > 0:
                plus_dm.append(high_diff)
            else:
                plus_dm.append(0)
            
            if low_diff > high_diff and low_diff > 0:
                minus_dm.append(low_diff)
            else:
                minus_dm.append(0)
            
            tr.append(max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1])))
        
        if not tr: return None
        
        atr = sum(tr[:period]) / period
        plus_di = 100 * sum(plus_dm[:period]) / atr if atr > 0 else 0
        minus_di = 100 * sum(minus_dm[:period]) / atr if atr > 0 else 0
        
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di) if (plus_di + minus_di) > 0 else 0
        adx = dx  # Simplified
        
        return {'adx': adx, 'plus_di': plus_di, 'minus_di': minus_di}
    except:
        return None

def calculate_williams_r(candles, period=14):
    """Williams %R - Overbought/Oversold"""
    if len(candles) < period: return None
    try:
        highs = [c[1] for c in candles]
        lows = [c[2] for c in candles]
        closes = [c[3] for c in candles]
        
        highest = max(highs[-period:])
        lowest = min(lows[-period:])
        
        if highest == lowest: return None
        
        wr = -100 * (highest - closes[-1]) / (highest - lowest)
        
        return wr
    except:
        return None

def calculate_cci(candles, period=20):
    """Commodity Channel Index"""
    if len(candles) < period: return None
    try:
        highs = [c[1] for c in candles]
        lows = [c[2] for c in candles]
        closes = [c[3] for c in candles]
        
        typical_prices = [(h + l + c) / 3 for h, l, c in zip(highs[-period:], lows[-period:], closes[-period:])]
        sma = sum(typical_prices) / period
        
        mean_deviation = sum(abs(tp - sma) for tp in typical_prices) / period
        
        if mean_deviation == 0: return None
        
        cci = (typical_prices[-1] - sma) / (0.015 * mean_deviation)
        
        return cci
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

def get_4h_analysis(symbol):
    """Get 4H timeframe analysis"""
    candles_4h = get_klines(symbol, '4h', 100)
    if not candles_4h or len(candles_4h) < 50:
        return {'trend': 'N/A', 'structure': 'N/A', 'rsi': 50}
    
    closes_4h = [c[3] for c in candles_4h]
    highs_4h = [c[1] for c in candles_4h]
    lows_4h = [c[2] for c in candles_4h]
    
    # EMA 200
    ema_200_4h = calculate_ema(closes_4h, 200)
    ema_50_4h = calculate_ema(closes_4h, 50)
    
    # Trend
    trend = "BULLISH" if closes_4h[-1] > ema_200_4h else "BEARISH" if ema_200_4h else "N/A"
    
    # Structure
    recent_highs = highs_4h[-5:]
    recent_lows = lows_4h[-5:]
    hh = recent_highs[-1] > recent_highs[-2] > recent_highs[-3]
    hl = recent_lows[-1] > recent_lows[-2] > recent_lows[-3]
    lh = recent_highs[-1] < recent_highs[-2] < recent_highs[-3]
    ll = recent_lows[-1] < recent_lows[-2] < recent_lows[-3]
    
    if hh and hl:
        structure = "UPTREND"
    elif lh and ll:
        structure = "DOWNTREND"
    else:
        structure = "CONSOLIDATION"
    
    # RSI 4H
    try:
        gains, losses = 0, 0
        for i in range(1, 15):
            if i >= len(closes_4h): break
            diff = closes_4h[-i] - closes_4h[-i-1]
            if diff > 0: gains += diff
            else: losses -= diff
        avg_gain = gains/14 if gains else 0
        avg_loss = losses/14 if losses else 0
        rsi_4h = 100 - (100/(1+(avg_gain/avg_loss))) if avg_loss > 0 else 50
    except:
        rsi_4h = 50
    
    return {
        'trend': trend,
        'ema_200': ema_200_4h,
        'ema_50': ema_50_4h,
        'structure': structure,
        'rsi': rsi_4h
    }

def detect_candlestick_patterns(candles, closes):
    """Detect multiple candlestick patterns"""
    if len(candles) < 3:
        return ""
    
    patterns = []
    c1 = candles[-3]  # [open, high, low, close, volume]
    c2 = candles[-2]
    c3 = candles[-1]
    
    # Previous candle for context
    prev = candles[-4] if len(candles) >= 4 else c2
    
    # Calculate candle properties
    def get_props(c):
        return {'open': c[0], 'high': c[1], 'low': c[2], 'close': c[3]}
    
    p1, p2, p3 = get_props(c1), get_props(c2), get_props(c3)
    
    # INSIDE BAR
    if p3['low'] > p2['low'] and p3['high'] < p2['high']:
        patterns.append("INSIDE_BAR")
    
    # BULLISH ENGULFING
    if p2['close'] < p2['open'] and p3['close'] > p3['open']:  # Red then green
        if p3['open'] < p2['close'] and p3['close'] > p2['open']:  # Engulfing
            patterns.append("BULLISH_ENGULFING")
    
    # BEARISH ENGULFING
    if p2['close'] > p2['open'] and p3['close'] < p3['open']:  # Green then red
        if p3['open'] > p2['close'] and p3['close'] < p2['open']:  # Engulfing
            patterns.append("BEARISH_ENGULFING")
    
    # BULLISH PIN BAR (Hammer-like)
    body3 = abs(p3['close'] - p3['open'])
    lower_wick3 = p3['open'] - p3['low'] if p3['close'] > p3['open'] else p3['close'] - p3['low']
    upper_wick3 = p3['high'] - p3['close'] if p3['close'] > p3['open'] else p3['high'] - p3['open']
    if lower_wick3 > body3 * 2 and upper_wick3 < body3 * 0.5:
        patterns.append("BULLISH_PINBAR")
    
    # BEARISH PIN BAR (Shooting star)
    if upper_wick3 > body3 * 2 and lower_wick3 < body3 * 0.5:
        patterns.append("BEARISH_PINBAR")
    
    # DOJI
    body = abs(p3['close'] - p3['open'])
    total_range = p3['high'] - p3['low']
    if total_range > 0 and body / total_range < 0.1:
        patterns.append("DOJI")
    
    # MORNING STAR (3 candles)
    if len(candles) >= 4:
        p0 = get_props(prev)
        # First candle: red/down
        # Second candle: small body (doji-like)
        # Third candle: green with body covering first
        if p0['close'] < p0['open'] and p2['close'] < p2['open'] and p3['close'] > p3['open']:
            if p2['high'] - p2['low'] < (p0['high'] - p0['low']) * 0.3:  # Small middle
                if p3['close'] > (p0['open'] + p0['close']) / 2:  # Above midpoint
                    patterns.append("MORNING_STAR")
    
    # EVENING STAR (reverse of morning)
    if len(candles) >= 4:
        p0 = get_props(prev)
        if p0['close'] > p0['open'] and p2['close'] > p2['open'] and p3['close'] < p3['open']:
            if p2['high'] - p2['low'] < (p0['high'] - p0['low']) * 0.3:
                if p3['close'] < (p0['open'] + p0['close']) / 2:
                    patterns.append("EVENING_STAR")
    
    return ", ".join(patterns) if patterns else ""

def check_market_structure(candles):
    """Enhanced market structure detection"""
    if len(candles) < 30:
        return {'structure': 'N/A', 'detail': ''}
    
    highs = [c[1] for c in candles[-30:]]
    lows = [c[2] for c in candles[-30:]]
    closes = [c[3] for c in candles[-30:]]
    
    recent_highs = highs[-10:]
    recent_lows = lows[-10:]
    current = closes[-1]
    
    # Basic HH/HL/LH/LL
    hh = recent_highs[-1] > recent_highs[-2] > recent_highs[-3]
    hl = recent_lows[-1] > recent_lows[-2] > recent_lows[-3]
    lh = recent_highs[-1] < recent_highs[-2] < recent_highs[-3]
    ll = recent_lows[-1] < recent_lows[-2] < recent_lows[-3]
    
    # Basic trend
    if hh and hl:
        structure = "UPTREND"
    elif lh and ll:
        structure = "DOWNTREND"
    else:
        structure = "CONSOLIDATION"
    
    # Additional patterns
    detail_parts = []
    
    # BREAKOUT - price breaks recent high
    if len(highs) >= 5:
        if current > max(highs[-5:-1]):
            detail_parts.append("BREAKOUT")
    
    # BREAKDOWN - price breaks recent low
    if len(lows) >= 5:
        if current < min(lows[-5:-1]):
            detail_parts.append("BREAKDOWN")
    
    # DOUBLE TOP - two highs near same level
    if len(recent_highs) >= 6:
        if abs(recent_highs[-1] - recent_highs[-3]) / recent_highs[-1] < 0.02:  # within 2%
            if recent_highs[-1] > recent_highs[-2]:
                detail_parts.append("DOUBLE_TOP")
    
    # DOUBLE BOTTOM - two lows near same level
    if len(recent_lows) >= 6:
        if abs(recent_lows[-1] - recent_lows[-3]) / recent_lows[-1] < 0.02:
            if recent_lows[-1] < recent_lows[-2]:
                detail_parts.append("DOUBLE_BOTTOM")
    
    # ASCENDING TRIANGLE - flat resistance, higher lows
    if len(recent_highs) >= 5 and len(recent_lows) >= 5:
        res_range = max(recent_highs[-5:]) - min(recent_highs[-5:])
        sup_range = max(recent_lows[-5:]) - min(recent_lows[-5:])
        # Higher lows
        higher_lows = all(recent_lows[-(i+1)] > recent_lows[-(i+2)] for i in range(3))
        # Flat resistance
        flat_res = res_range < sup_range * 0.5
        if higher_lows and flat_res:
            detail_parts.append("ASCENDING_TRIANGLE")
    
    # DESCENDING TRIANGLE - flat support, lower highs
    if len(recent_highs) >= 5 and len(recent_lows) >= 5:
        res_range = max(recent_highs[-5:]) - min(recent_highs[-5:])
        sup_range = max(recent_lows[-5:]) - min(recent_lows[-5:])
        lower_highs = all(recent_highs[-(i+1)] < recent_highs[-(i+2)] for i in range(3))
        flat_sup = sup_range < res_range * 0.5
        if lower_highs and flat_sup:
            detail_parts.append("DESCENDING_TRIANGLE")
    
    # WEDGE - converging highs and lows
    if len(recent_highs) >= 5 and len(recent_lows) >= 5:
        high_slope = recent_highs[-1] - recent_highs[-5]
        low_slope = recent_lows[-1] - recent_lows[-5]
        if high_slope < 0 and low_slope > 0:
            detail_parts.append("WEDGE")
    
    # CHANNEL - parallel highs and lows
    if len(recent_highs) >= 5 and len(recent_lows) >= 5:
        high_range = max(recent_highs) - min(recent_highs)
        low_range = max(recent_lows) - min(recent_lows)
        if abs(high_range - low_range) / high_range < 0.3:
            detail_parts.append("CHANNEL")
    
    detail = ", ".join(detail_parts) if detail_parts else ""
    
    return {'structure': structure, 'detail': detail}

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
        
        # Get 4H analysis
        analysis_4h = get_4h_analysis(symbol)
        
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
            'trend_4h': analysis_4h.get('trend', 'N/A'),
            'structure_4h': analysis_4h.get('structure', 'N/A'),
            'insight': "HOT COIN - {}% today! {} momentum. {}".format(price_change, analysis_4h.get('trend', ''), vol_confirm)
        }
    except:
        return None

def build_insight(direction, structure, structure_detail, rsi, patterns, vol_data, analysis_4h):
    """Build enhanced trading insight"""
    parts = []
    
    # Basic direction
    if direction == "LONG":
        parts.append("Bullish")
    else:
        parts.append("Bearish")
    
    # Structure
    if structure_detail and "BREAKOUT" in structure_detail:
        parts.append("Breakout")
    elif structure_detail and "BREAKDOWN" in structure_detail:
        parts.append("Breakdown")
    elif structure_detail and "DOUBLE_TOP" in structure_detail:
        parts.append("Double Top")
    elif structure_detail and "DOUBLE_BOTTOM" in structure_detail:
        parts.append("Double Bottom")
    elif structure_detail and "ASCENDING" in structure_detail:
        parts.append("Ascending Triangle")
    elif structure_detail and "DESCENDING" in structure_detail:
        parts.append("Descending Triangle")
    elif structure_detail and "WEDGE" in structure_detail:
        parts.append("Wedge")
    elif structure_detail and "CHANNEL" in structure_detail:
        parts.append("Channel")
    
    # RSI conditions
    if rsi < 30:
        parts.append("RSI Oversold")
    elif rsi > 70:
        parts.append("RSI Overbought")
    elif rsi < 40:
        parts.append("RSI Low")
    elif rsi > 60:
        parts.append("RSI High")
    
    # Patterns
    if patterns:
        if "BULLISH_ENGULFING" in patterns or "MORNING_STAR" in patterns:
            parts.append("Bullish Pattern")
        elif "BEARISH_ENGULFING" in patterns or "EVENING_STAR" in patterns:
            parts.append("Bearish Pattern")
        elif "BULLISH_PINBAR" in patterns:
            parts.append("Bullish Pinbar")
        elif "BEARISH_PINBAR" in patterns:
            parts.append("Bearish Pinbar")
        elif "INSIDE_BAR" in patterns:
            parts.append("Inside Bar")
    
    # Volume
    if vol_data.get('spike'):
        parts.append("Volume Spike")
    elif vol_data.get('drop'):
        parts.append("Low Volume")
    
    # OBV
    if vol_data.get('obv', 0) > 0:
        parts.append("OBV Up")
    elif vol_data.get('obv', 0) < 0:
        parts.append("OBV Down")
    
    # 4H alignment
    trend_4h = analysis_4h.get('trend', 'N/A')
    if trend_4h != 'N/A':
        if (direction == "LONG" and trend_4h == "BULLISH") or (direction == "SHORT" and trend_4h == "BEARISH"):
            parts.append("4H Aligned")
    
    # Join parts
    return " | ".join(parts)

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
        
        struct = check_market_structure(candles)
        structure = struct.get('structure', 'N/A')
        structure_detail = struct.get('detail', '')
        
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
        # Build enhanced insight
        insight = build_insight(direction, structure, structure_detail, rsi, patterns, vol_data, analysis_4h)
        
        if not insight:
            return None
        
        atr = calculate_atr(candles, 14) or 0
        vol_data = get_volume_data(symbol)
        
        # Detect multiple candlestick patterns
        patterns = detect_candlestick_patterns(candles, closes)
        
        # Get 4H analysis
        analysis_4h = get_4h_analysis(symbol)
        
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
            'structure_detail': structure_detail,
            'support': support,
            'resistance': resistance,
            'range': range_height,
            'volume_info': "Volume Spike" if vol_data.get('spike') else "",
            'pattern_info': patterns,
            'trend_4h': analysis_4h.get('trend', 'N/A'),
            'structure_4h': analysis_4h.get('structure', 'N/A'),
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
        msg += "• Trend 4H: {}\n".format(s.get('trend_4h', 'N/A'))
        msg += "• Structure 1H: {} {}\n".format(s.get('structure', 'N/A'), '(' + s.get('structure_detail', '') + ')' if s.get('structure_detail', '') else '')
        msg += "• Structure 4H: {}\n".format(s.get('structure_4h', 'N/A'))
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
