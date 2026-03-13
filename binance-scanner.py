#!/usr/bin/env python3
"""
Neko Sentinel - Binance Futures Signal Scanner v5
With DCA (Dollar Cost Averaging) & Hedging
"""

import hmac, hashlib, time, requests, json, os
from datetime import datetime

# Config - Load from environment variables
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

# DCA Config
DCA_ENABLED = True
DCA_THRESHOLD = -2.0  # % loss before DCA trigger
DCA_MAX_LAYERS = 3  # Max DCA layers per position
DCA_LAYER_PERCENT = [5, 7, 10]  # % of original position size for each layer

# Hedging Config
HEDGE_ENABLED = True
HEDGE_THRESHOLD = -3.0  # % loss before hedge
HEDGE_SIZE_PERCENT = 50  # Hedge size = 50% of original position

# Load symbols
with open('/root/.openclaw/workspace/binance-futures/futures_symbols.json') as f:
    SYMBOLS = json.load(f)

SYMBOLS = [s for s in SYMBOLS if 'USDT' in s and 'USDC' not in s and len(s) < 20][:80]

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

def place_order(symbol, side, quantity, order_type="MARKET"):
    ts = int(time.time() * 1000)
    set_leverage(symbol, LEVERAGE)
    precision = get_precision(symbol)
    quantity = round(quantity, precision)
    
    params = f"symbol={symbol}&side={side}&quantity={quantity}&type={order_type}&timestamp={ts}"
    sig = get_signature(params)
    
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

def close_position(symbol, side, quantity):
    """Close partial or full position"""
    return place_order(symbol, side, quantity)

# DCA State
DCA_STATE_FILE = '/root/.openclaw/workspace/.dca_state.json'

def load_dca_state():
    try:
        with open(DCA_STATE_FILE) as f:
            return json.load(f)
    except:
        return {}

def save_dca_state(state):
    with open(DCA_STATE_FILE, 'w') as f:
        json.dump(state, f)

def check_dca(position, balance):
    """Check if DCA is needed for a position"""
    if not DCA_ENABLED:
        return None
    
    symbol = position.get('symbol')
    amt = float(position.get('positionAmt', 0))
    if amt == 0:
        return None
    
    entry = float(position.get('entryPrice', 0) or 0)
    current = float(position.get('markPrice', 0) or 0)
    pnl_percent = float(position.get('percentage', 0) or 0)
    
    direction = "LONG" if amt > 0 else "SHORT"
    
    # Load DCA state
    dca_state = load_dca_state()
    pos_key = f"{symbol}_{direction}"
    
    if pos_key not in dca_state:
        dca_state[pos_key] = {'layers': 0, 'entry': entry}
    
    # Check if DCA triggered
    if pnl_percent <= -DCA_THRESHOLD:
        layers = dca_state[pos_key].get('layers', 0)
        
        if layers < DCA_MAX_LAYERS:
            # Calculate DCA amount
            dca_percent = DCA_LAYER_PERCENT[layers] if layers < len(DCA_LAYER_PERCENT) else DCA_LAYER_PERCENT[-1]
            dca_amount = (balance * dca_percent / 100) * LEVERAGE / current
            
            print(f"  🔄 DCA triggered for {symbol}! Layer {layers+1}")
            print(f"     Loss: {pnl_percent:.2f}%, DCA amount: {dca_amount}")
            
            # Execute DCA
            side = "BUY" if direction == "LONG" else "SELL"
            result = place_order(symbol, side, dca_amount)
            
            if result:
                dca_state[pos_key]['layers'] = layers + 1
                dca_state[pos_key]['entry'] = entry  # Update average entry
                save_dca_state(dca_state)
                return {
                    'action': 'DCA',
                    'symbol': symbol,
                    'direction': direction,
                    'layer': layers + 1,
                    'pnl_percent': pnl_percent
                }
    
    return None

def check_hedge(position, balance):
    """Check if hedging is needed"""
    if not HEDGE_ENABLED:
        return None
    
    symbol = position.get('symbol')
    amt = float(position.get('positionAmt', 0))
    if amt == 0:
        return None
    
    current = float(position.get('markPrice', 0) or 0)
    pnl_percent = float(position.get('percentage', 0) or 0)
    
    direction = "LONG" if amt > 0 else "SHORT"
    
    # Check if hedge triggered
    if pnl_percent <= -HEDGE_THRESHOLD:
        # Open opposite position as hedge
        hedge_side = "SELL" if direction == "LONG" else "BUY"
        hedge_amount = (abs(amt) * HEDGE_SIZE_PERCENT / 100)
        
        print(f"  🛡️ HEDGE triggered for {symbol}!")
        print(f"     Loss: {pnl_percent:.2f}%, Hedge size: {hedge_amount}")
        
        result = place_order(symbol, hedge_side, hedge_amount)
        
        if result:
            return {
                'action': 'HEDGE',
                'symbol': symbol,
                'direction': direction,
                'hedge_side': hedge_side,
                'pnl_percent': pnl_percent
            }
    
    return None

def manage_positions():
    """Check all positions for DCA/Hedge opportunities"""
    positions = get_positions()
    balance = get_balance()
    
    actions = []
    
    for pos in positions:
        amt = float(pos.get('positionAmt', 0))
        if amt == 0:
            continue
        
        # Check DCA first
        dca_result = check_dca(pos, balance)
        if dca_result:
            actions.append(dca_result)
            send_telegram_alert(f"🔄 DCA EXECUTED\n{pos.get('symbol')}: {dca_result['direction']} Layer {dca_result['layer']}\nLoss: {dca_result['pnl_percent']:.2f}%")
            continue
        
        # Check Hedge
        hedge_result = check_hedge(pos, balance)
        if hedge_result:
            actions.append(hedge_result)
            send_telegram_alert(f"🛡️ HEDGE EXECUTED\n{pos.get('symbol')}: {hedge_result['direction']} → {hedge_result['hedge_side']}\nLoss: {hedge_result['pnl_percent']:.2f}%")
    
    return actions

def send_telegram_alert(message):
    if not TELEGRAM_BOT_TOKEN:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={'chat_id': TELEGRAM_CHANNEL, 'text': message}, timeout=30)
    except:
        pass

# Rest of scanner functions... (get_klines, analyze_symbol, etc.)
# For brevity, using simplified versions

def get_klines(symbol, interval='1h', limit=100):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    r = requests.get(url, timeout=10)
    if not r:
        return []
    try:
        return [[float(c[1]), float(c[2]), float(c[3]), float(c[4])] for c in r.json()]
    except:
        return []

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

def analyze_symbol(symbol):
    try:
        candles = get_klines(symbol, '1h', 100)
        if not candles or len(candles) < 50:
            return None
        
        closes = [c[3] for c in candles]
        highs = [c[1] for c in candles]
        lows = [c[2] for c in candles]
        current = closes[-1]
        
        ema_200 = calculate_ema(closes, 200)
        if not ema_200:
            return None
        
        resistance = max(highs[-50:])
        support = min(lows[-50:])
        
        # Simple entry logic
        if current > ema_200:  # Uptrend
            if (current - support) / current * 100 < 3:
                return {'symbol': symbol, 'direction': 'LONG', 'current': current, 'sl': support * 0.98}
        else:
            if (resistance - current) / current * 100 < 3:
                return {'symbol': symbol, 'direction': 'SHORT', 'current': current, 'sl': resistance * 1.02}
        
        return None
    except:
        return None

def format_signal(analysis):
    s = analysis
    symbol = s['symbol'].replace('USDT', '')
    emoji = "🟢" if s['direction'] == "LONG" else "🔴"
    
    msg = f"""{emoji} {s['direction']} SIGNAL {emoji}

📈 {symbol}USDT
🎯 Entry: ${s['current']:.6f}
🛡 SL: ${s['sl']:.6f}
⏰ Timeframe: 1H"""
    return msg

def send_telegram(message):
    if not TELEGRAM_BOT_TOKEN:
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
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
print(f"🔍 Scanner v5 [DCA + HEDGE] Starting...")
print(f"  DCA: {'ON' if DCA_ENABLED else 'OFF'} (threshold: {DCA_THRESHOLD}%, max layers: {DCA_MAX_LAYERS})")
print(f"  Hedge: {'ON' if HEDGE_ENABLED else 'OFF'} (threshold: {HEDGE_THRESHOLD}%)")

balance = get_balance()
print(f"  Balance: ${balance:.2f}")

# Check for DCA/Hedge opportunities first
print("\n📊 Checking positions for DCA/Hedge...")
dca_actions = manage_positions()
if dca_actions:
    print(f"  ✅ {len(dca_actions)} actions taken")
else:
    print("  No DCA/Hedge needed")

# Then normal scanning
print(f"\n🔍 Scanning {len(SYMBOLS)} symbols...")
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
            trade_amount = (balance * ENTRY_PERCENT / 100) * LEVERAGE
            quantity = round(trade_amount / analysis['current'], 3)
            
            side = "BUY" if analysis['direction'] == "LONG" else "SELL"
            print(f"Executing {side}...", end=" ")
            order_result = place_order(symbol, side, quantity)
            
            if order_result:
                msg = format_signal(analysis)
                print(f"Posting...", end=" ")
                sent = send_telegram(msg)
                if sent:
                    print(f"✅ Done!")
                    open_count += 1
                else:
                    print(f"❌ Post failed")
                new_signals[signal_key] = msg[:50]
            else:
                print(f"❌ Order failed")
                new_signals[signal_key] = last_signals.get(signal_key, "")
        else:
            print(f"(already posted)")
            new_signals[signal_key] = last_signals[signal_key]
    else:
        print(f"(no signal)")
        new_signals[signal_key] = last_signals.get(f"{symbol}_LONG", "")

save_last_signals(new_signals)
print("✅ Scan complete!")
