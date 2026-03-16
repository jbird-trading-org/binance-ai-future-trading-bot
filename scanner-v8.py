#!/usr/bin/env python3
"""
Simplified Scanner v8 - Aggressive momentum trading
"""

import os
import json
import time
import hmac
import hashlib
import requests
from datetime import datetime

# === CONFIG ===
API_KEY = os.environ.get('BINANCE_API_KEY', 'ZP97eSsGupjeR7JcOUwSZnPPFIXFKGSe7Yw7gdZSAN3fkPlPxrfTwzk4QEEQftCx')
SECRET = os.environ.get('BINANCE_SECRET', 'rKUgMVksTn3qeUk0jl1aau8lS4LShOR2ILoSygpaRlauI130FuFJrUTuYoAfanUl')

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '***REDACTED_TELEGRAM_TOKEN***')
TELEGRAM_CHANNEL = os.environ.get('TELEGRAM_CHANNEL', '-1003847994290')
BRAVE_API_KEY = os.environ.get('BRAVE_API_KEY', '')

LEVERAGE = 10
MAX_POSITIONS = 8
ENTRY_PERCENT = 5
MIN_GAIN = 0.5

# Only trade top coins - safe for futures
SAFE_COINS = [
    'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT',
    'AVAXUSDT', 'DOTUSDT', 'MATICUSDT', 'LINKUSDT', 'UNIUSDT', 'ATOMUSDT', 'LTCUSDT',
    'BCHUSDT', 'ETCUSDT', 'XLMUSDT', 'ALGOUSDT', 'VETUSDT', 'FILUSDT', 'THETAUSDT',
    'AAVEUSDT', 'EOSUSDT', 'XMRUSDT', 'ALICEUSDT', 'AXSUSDT', 'FTMUSDT', 'GRTUSDT',
    'SNXUSDT', 'NEOUSDT', 'KAVAUSDT', 'RUNEUSDT', 'ZECUSDT', 'DASHUSDT', 'COMPUSDT',
    'MKRUSDT', 'YFIUSDT', 'SUSHIUSDT', 'CRVUSDT', 'ENJUSDT', 'CHZUSDT', 'MANAUSDT',
    'SANDUSDT', 'GALAUSDT', 'AXSUSDT', 'APEUSDT', 'RNDRUSDT', 'INJUSDT', 'OPUSDT',
    'ARBUSDT', 'BLURUSDT', 'PEPEUSDT', 'SHIBUSDT', 'WIFUSDT', 'BONKUSDT', 'SEIUSDT',
    'TIAUSDT', 'SUIUSDT', 'SEIAMPTUSDT', 'IMXUSDT', 'STXUSDT', 'RUNEUSDT', 'NEARUSDT',
    'APTUSDT', 'ARBUSDT', 'OPUSDT', 'GMXUSDT', 'LRCUSDT', 'ENSUSDT', '1INCHUSDT'
]
# Remove duplicates
SAFE_COINS = list(set(SAFE_COINS))

# === API HELPERS ===
def get_signature(params):
    return hmac.new(SECRET.encode(), params.encode(), hashlib.sha256).hexdigest()

def binance_get(url, params=None):
    if params:
        params['timestamp'] = int(time.time() * 1000)
        params['signature'] = get_signature('&'.join(f'{k}={v}' for k, v in params.items()))
    headers = {'X-MBX-APIKEY': API_KEY}
    r = requests.get(url, params=params, headers=headers, timeout=15)
    return r.json()

def binance_post(url, params):
    params['timestamp'] = int(time.time() * 1000)
    params['signature'] = get_signature('&'.join(f'{k}={v}' for k, v in params.items()))
    headers = {'X-MBX-APIKEY': API_KEY}
    r = requests.post(url, data=params, headers=headers, timeout=15)
    return r.json()

# === GET DATA ===
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

def get_positions():
    ts = int(time.time() * 1000)
    params = "timestamp={}".format(ts)
    sig = get_signature(params)
    r = requests.get("https://fapi.binance.com/fapi/v3/account?{}&signature={}".format(params, sig),
                     headers={"X-MBX-APIKEY": API_KEY}, timeout=15)
    if r:
        return [p for p in r.json().get('positions', []) if float(p.get('positionAmt', 0)) != 0]
    return []

def get_24h_tickers():
    return binance_get('https://fapi.binance.com/fapi/v1/ticker/24hr')

def get_klines(symbol, interval='1h', limit=100):
    url = f'https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={interval}&limit={limit}'
    r = requests.get(url, timeout=15)
    return r.json()

def place_order_with_sl_tp(symbol, side, quantity, sl_price, tp_price):
    """Place order with auto SL/TP"""
    ts = int(time.time() * 1000)
    
    # First place the order
    params = "symbol={}&side={}&type=MARKET&quantity={}&timestamp={}".format(symbol, side, quantity, ts)
    sig = get_signature(params)
    url = "https://fapi.binance.com/fapi/v1/order?{}&signature={}".format(params, sig)
    headers = {'X-MBX-APIKEY': API_KEY}
    r = requests.post(url, headers=headers, timeout=15)
    result = r.json()
    
    # Then set stop loss - use working price instead of closePosition
    if sl_price:
        sl_side = "SELL" if side == "BUY" else "BUY"
        # Get current price for working price
        r = requests.get(f'https://fapi.binance.com/fapi/v1/ticker/price?symbol={symbol}', timeout=10)
        current_price = float(r.json()['price'])
        sl_price_adj = current_price * 0.99 if side == "BUY" else current_price * 1.01
        
        sl_params = "symbol={}&side={}&type=STOP&price={}&stopPrice={}&timeInForce=GTC&quantity={}&timestamp={}".format(
            symbol, sl_side, round(sl_price_adj, 6), round(sl_price, 6), quantity, int(time.time() * 1000))
        sl_sig = get_signature(sl_params)
        sl_url = "https://fapi.binance.com/fapi/v1/order?{}&signature={}".format(sl_params, sl_sig)
        requests.post(sl_url, headers=headers, timeout=15)
    
    # Then set take profit
    if tp_price:
        tp_side = "SELL" if side == "BUY" else "BUY"
        r = requests.get(f'https://fapi.binance.com/fapi/v1/ticker/price?symbol={symbol}', timeout=10)
        current_price = float(r.json()['price'])
        tp_price_adj = current_price * 1.01 if side == "BUY" else current_price * 0.99
        
        tp_params = "symbol={}&side={}&type=STOP&price={}&stopPrice={}&timeInForce=GTC&quantity={}&timestamp={}".format(
            symbol, tp_side, round(tp_price_adj, 6), round(tp_price, 6), quantity, int(time.time() * 1000))
        tp_sig = get_signature(tp_params)
        tp_url = "https://fapi.binance.com/fapi/v1/order?{}&signature={}".format(tp_params, tp_sig)
        requests.post(tp_url, headers=headers, timeout=15)
    
    return result

def place_order(symbol, side, quantity):
    ts = int(time.time() * 1000)
    params = "symbol={}&side={}&type=MARKET&quantity={}&timestamp={}".format(symbol, side, quantity, ts)
    sig = get_signature(params)
    url = "https://fapi.binance.com/fapi/v1/order?{}&signature={}".format(params, sig)
    headers = {'X-MBX-APIKEY': API_KEY}
    r = requests.post(url, headers=headers, timeout=15)
    return r.json()

def set_leverage(symbol, lev=LEVERAGE):
    ts = int(time.time() * 1000)
    params = "symbol={}&leverage={}&timestamp={}".format(symbol, lev, ts)
    sig = get_signature(params)
    url = "https://fapi.binance.com/fapi/v1/leverage?{}&signature={}".format(params, sig)
    headers = {'X-MBX-APIKEY': API_KEY}
    r = requests.post(url, headers=headers, timeout=15)
    return r.json()

def send_telegram(msg):
    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
    data = {'chat_id': TELEGRAM_CHANNEL, 'text': msg, 'parse_mode': 'Markdown'}
    r = requests.post(url, data=data, timeout=15)
    return r.status_code == 200

# === ANALYSIS ===
def calc_ema(prices, period):
    if len(prices) < period:
        return None
    mul = 2 / (period + 1)
    ema = sum(prices[:period]) / period
    for p in prices[period:]:
        ema = (p - ema) * mul + ema
    return ema

def calc_atr(candles, period=14):
    if len(candles) < period + 1:
        return None
    trs = []
    for i in range(1, min(period + 1, len(candles))):
        high = float(candles[-i][1])
        low = float(candles[-i][2])
        prev = float(candles[-i-1][3])
        tr = max(high - low, abs(high - prev), abs(low - prev))
        trs.append(tr)
    return sum(trs) / len(trs) if trs else None

def analyze_symbol(symbol, stats):
    """Runner-focused analysis - look for momentum explosions"""
    stat = stats.get(symbol, {})
    price_change = float(stat.get('priceChangePercent', 0))
    
    # Get candles first to check volume/momentum
    candles = get_klines(symbol, '1h', 50)
    if not candles or len(candles) < 20:
        return None
    
    closes = [float(c[3]) for c in candles]
    highs = [float(c[1]) for c in candles]
    lows = [float(c[2]) for c in candles]
    volumes = [float(c[5]) for c in candles]
    current = closes[-1]
    
    # === RUNNER CRITERIA ===
    # 1. Volume Spike (5x+ average)
    avg_vol = sum(volumes[-24:]) / 24 if len(volumes) >= 24 else sum(volumes) / len(volumes)
    recent_vol = volumes[-1]
    vol_ratio = recent_vol / avg_vol if avg_vol > 0 else 1
    
    # 2. 1H Momentum (continuation)
    change_1h = ((closes[-1] - closes[-6]) / closes[-6]) * 100 if len(closes) >= 6 else 0
    
    # 3. Breakout (breaking recent high)
    recent_high = max(highs[-10:])
    prev_high = max(highs[-20:-10]) if len(highs) >= 20 else max(highs[:-10])
    breakout = recent_high > prev_high * 1.02  # 2% above
    
    # Runner score
    runner_score = 0
    if vol_ratio > 3: runner_score += 2
    elif vol_ratio > 2: runner_score += 1
    if price_change > 10: runner_score += 2
    elif price_change > 5: runner_score += 1
    if abs(change_1h) > 3: runner_score += 1
    if breakout: runner_score += 2
    
    # Must have at least score 3 for signal
    if runner_score < 3:
        return None
    
    # Must have positive change for LONG
    if price_change <= 0:
        return None
    
    # EMAs
    ema_21 = calc_ema(closes, 21)
    ema_50 = calc_ema(closes, 50)
    if not ema_21 or not ema_50:
        return None
    
    # ATR for SL/TP
    atr = calc_atr(candles, 14) or (current * 0.02)
    
    # Direction - LONG only for runners
    direction = "LONG"
    sl = current - (atr * 1.5)
    tp1 = current + (atr * 3.0)
    tp2 = current + (atr * 4.5)
    
    # Trend
    trend = "BULLISH" if current > ema_50 else "BEARISH"
    
    # Structure
    if breakout:
        structure = "BREAKOUT"
    elif price_change > 10:
        structure = "STRONG_MOMENTUM"
    else:
        structure = "MOMENTUM"
    
    # Support/Resistance
    resistance = max(highs[-50:]) if len(highs) >= 50 else max(highs)
    support = min(lows[-50:]) if len(lows) >= 50 else min(lows)
    
    # RSI
    rsi = 50
    try:
        gains, losses = 0, 0
        for i in range(1, 15):
            if i >= len(closes): break
            diff = closes[-i] - closes[-i-1]
            if diff > 0: gains += diff
            else: losses -= diff
        avg_gain = gains / 14 if gains else 0
        avg_loss = losses / 14 if losses else 0
        rsi = 100 - (100 / (1 + (avg_gain / avg_loss))) if avg_loss > 0 else 50
    except:
        rsi = 50
    
    return {
        'symbol': symbol,
        'direction': direction,
        'current': current,
        'price_change': price_change,
        'change_1h': change_1h,
        'sl': sl,
        'tp1': tp1,
        'tp2': tp2,
        'atr': atr,
        'rsi': rsi,
        'ema_21': ema_21,
        'ema_50': ema_50,
        'trend': trend,
        'structure': structure,
        'support': support,
        'resistance': resistance,
        'vol_spike': vol_ratio > 2,
        'vol_ratio': vol_ratio,
        'breakout': breakout,
        'runner_score': runner_score
    }

def fetch_brave_news(query, count=2):
    """Fetch news using Brave Search API"""
    try:
        import requests
        brave_key = os.environ.get('BRAVE_API_KEY', '')
        url = f"https://api.search.brave.com/res/v1/web/search?q={query}&count={count}"
        headers = {"Accept": "application/json", "X-Subscription-Token": brave_key}
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            data = r.json()
            results = data.get('web', {}).get('results', [])
            news = []
            for item in results[:count]:
                title = item.get('title', '')[:50]
                if title:
                    news.append(title)
            return news if news else None
    except:
        pass
    return None

def get_token_news(symbol, stats):
    """Get latest info for a token - price action + market context + real news"""
    sym = symbol.replace('USDT', '')
    
    # Token name mapping for search
    token_names = {
        'BTC': 'Bitcoin', 'ETH': 'Ethereum', 'BNB': 'Binance', 'SOL': 'Solana',
        'XRP': 'XRP Ripple', 'ADA': 'Cardano', 'DOGE': 'Dogecoin', 'AVAX': 'Avalanche',
        'DOT': 'Polkadot', 'MATIC': 'Polygon', 'LINK': 'Chainlink', 'UNI': 'Uniswap',
        'ATOM': 'Cosmos', 'LTC': 'Litecoin', 'FIL': 'Filecoin', 'AAVE': 'Aave',
        'PEPE': 'Pepe crypto', 'SHIB': 'Shiba Inu', 'WIF': 'dogwifhat', 'BONK': 'Bonk',
        'INJ': 'Injective', 'OP': 'Optimism', 'ARB': 'Arbitrum', 'TIA': 'Celestia',
        'SUI': 'Sui blockchain', 'SEI': 'Sei blockchain', 'NEAR': 'NEAR Protocol',
        'APT': 'Aptos', 'RUNE': 'THORChain', 'GRT': 'The Graph', 'ENS': 'Ethereum Name Service',
        'IMX': 'Immutable X', 'STX': 'Stacks', 'RNDR': 'Render Token',
        'XAN': 'XANA metaverse', 'AXS': 'Axie Infinity', 'FTM': 'Fantom',
        'GALA': 'Gala', 'SAND': 'The Sandbox', 'MANA': 'Decentraland',
        'ALGO': 'Algorand', 'VET': 'VeChain', 'THETA': 'Theta'
    }
    
    # Get real news first
    token_name = token_names.get(sym, sym)
    real_news = None
    try:
        import requests
        # Use web search for news
        brave_url = "https://api.search.brave.com/res/v1/web/search"
        headers = {"Accept": "application/json"}
        params = {"q": f"{token_name} crypto news 2026", "count": 2}
        r = requests.get(brave_url, params=params, headers=headers, timeout=5)
        if r.status_code == 200:
            data = r.json()
            results = data.get('web', {}).get('results', [])
            if results:
                news_titles = [r.get('title', '')[:45] for r in results[:2] if r.get('title')]
                if news_titles:
                    real_news = " | ".join(news_titles)
    except:
        pass
    
    # Get stats
    stat = stats.get(symbol, {})
    change_24h = float(stat.get('priceChangePercent', 0))
    volume = float(stat.get('volume', 0))
    high_24h = float(stat.get('highPrice', 0))
    low_24h = float(stat.get('lowPrice', 0))
    
    # Format volume
    if volume > 1e9:
        vol_str = f"${volume/1e9:.1f}B"
    elif volume > 1e6:
        vol_str = f"${volume/1e6:.1f}M"
    else:
        vol_str = f"${volume/1e3:.1f}K"
    
    # Market context
    if change_24h > 10:
        context = "🔥 Hot momentum"
    elif change_24h > 5:
        context = "📈 Strong gain"
    elif change_24h > 0:
        context = "📊 Positive"
    elif change_24h < -10:
        context = "💥 Heavy selloff"
    elif change_24h < -5:
        context = "📉 Sharp drop"
    else:
        context = "➡️ Sideways"
    
    # If we have real news, use it
    if real_news:
        return f"📰 {real_news}"
    
    return f"{context} | 24h: {change_24h:+.2f}% | Vol: {vol_str}"

def format_signal(analysis, stats):
    s = analysis
    sym = s['symbol'].replace('USDT', '')
    emoji = "🟢" if s['direction'] == "LONG" else "🔴"
    
    # Get token context
    news = get_token_news(s['symbol'], stats)
    
    msg = f"""{emoji} {s['direction']} SIGNAL {emoji}

📈 {sym}USDT TECHNICAL ANALYSIS 📊
📊 Chart: https://www.tradingview.com/chart/?symbol=BINANCE:{sym}USDT

📐 MULTI-TF CONFIRMATION:
• Trend 1H: {s['trend']}
• Structure: {s['structure']}
📊 24h Change: {s['price_change']:.2f}%

📐 INDICATORS:
• RSI (14): {s['rsi']:.1f}
• EMA 21: {s['ema_21']:.6f}
• EMA 50: {s['ema_50']:.6f}
• ATR: {s['atr']:.6f}

🔊 VOLUME: {'Volume Spike' if s['vol_spike'] else 'Normal'}

📊 STRUCTURE:
• Support: {s['support']:.6f}
• Resistance: {s['resistance']:.6f}

🎯 RUNNER METRICS:
• 1H Momentum: {s.get('change_1h', 0):+.1f}%
• Volume Spike: {s.get('vol_ratio', 1):.1f}x
• Breakout: {'✅ Yes' if s.get('breakout') else '❌ No'}
• Score: {s.get('runner_score', 0)}/10 🚀

💡 INSIGHT: {s['direction']} | {s['structure']} | RSI: {s['rsi']:.1f}
🎯 Entry: ${s['current']:.6f}
📈 TP: ${s['tp1']:.6f}
🛡 SL: ${s['sl']:.6f}
⏰ Timeframe: 1H

📰 {news}
"""
    return msg

# === MAIN ===
def main():
    print(f"🔍 Scanner v8 Starting...")
    
    balance = get_balance()
    positions = get_positions()
    open_count = len(positions)
    
    print(f"  Balance: ${balance:.2f}")
    print(f"  Open: {open_count}/{MAX_POSITIONS}")
    
    if open_count >= MAX_POSITIONS:
        print("⚠️ Max positions reached")
        return
    
    # Get all tickers
    tickers = get_24h_tickers()
    stats = {t['symbol']: t for t in tickers if t['symbol'].endswith('USDT')}
    
    # Sort by price change
    movers = [(s, float(t['priceChangePercent'])) for s, t in stats.items()]
    movers.sort(key=lambda x: x[1], reverse=True)
    
    print(f"  Found {len(movers)} symbols")
    
    # Load posted signals (to avoid duplicates)
    try:
        with open('.posted_signals', 'r') as f:
            posted = set(f.read().strip().split(','))
    except:
        posted = set()
    
    # Only check safe coins
    movers_filtered = [(s, p) for s, p in movers if s in SAFE_COINS]
    
    # Check safe coins with momentum
    for symbol, change in movers_filtered[:50]:
        if open_count >= MAX_POSITIONS:
            break
        
        # Skip if already has position
        if any(p.get('symbol') == symbol for p in positions):
            continue
        
        print(f"  Checking {symbol} ({change:.1f}%)...", end=" ")
        
        try:
            analysis = analyze_symbol(symbol, stats)
            if analysis:
                print(f"✅ SIGNAL! {analysis['direction']}")
                
                # Auto-trade + post signal
                trade_amount = (balance * ENTRY_PERCENT / 100) * LEVERAGE
                quantity = trade_amount / analysis['current']
                
                min_notional = 100
                min_qty = min_notional / analysis['current']
                if quantity * analysis['current'] < min_notional:
                    quantity = min_qty
                
                quantity = int(quantity)
                
                set_leverage(symbol, LEVERAGE)
                
                side = "BUY" if analysis['direction'] == "LONG" else "SELL"
                
                # Get SL/TP from analysis
                sl_price = analysis.get('sl')
                tp_price = analysis.get('tp1')
                
                # Place order with SL/TP
                result = place_order_with_sl_tp(symbol, side, quantity, sl_price, tp_price)
                
                order_id = result.get('orderId', 'N/A')
                status = result.get('status', 'UNKNOWN')
                
                # Only post if order succeeded (has valid orderId)
                if order_id and order_id != 'N/A':
                    if symbol in posted:
                        print(f"  (already posted)")
                    else:
                        msg = format_signal(analysis, stats)
                        msg += f"\n✅ ORDER EXECUTED: {analysis['direction']}\n"
                        msg += f"🛡 SL: ${analysis['sl']:.6f}\n"
                        msg += f"📈 TP: ${analysis['tp1']:.6f}\n"
                        msg += f"📋 Order ID: {order_id} | Status: {status}"
                        
                        send_telegram(msg)
                        print(f"  Order: {order_id} | Posted to Telegram")
                        
                        posted.add(symbol)
                        with open('.posted_signals', 'w') as f:
                            f.write(','.join(posted))
                        
                        open_count += 1
                else:
                    print(f"  Order failed: {status}")
            else:
                print("no signal")
        except Exception as e:
            print(f"error: {e}")
    
    print(f"\n✅ Scan complete!")

if __name__ == "__main__":
    main()
