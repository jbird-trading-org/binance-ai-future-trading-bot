#!/usr/bin/env python3
"""
Price Monitor - Auto close positions when SL/TP hit
Fibonacci + ATR based SL/TP levels
All config from environment variables - no hardcoded secrets
"""

import os
import time
import hmac
import hashlib
import requests
from datetime import datetime

# === LOAD FROM ENV FILE ===
# Only load from the same directory as the script
script_dir = os.path.dirname(os.path.abspath(__file__))
env_file = os.path.join(script_dir, '.env')

if env_file and os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

# === LOAD FROM ENV ===
API_KEY = os.environ.get('BINANCE_API_KEY', '')
SECRET = os.environ.get('BINANCE_SECRET', '')

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHANNEL = os.environ.get('TELEGRAM_CHANNEL', '')

CHECK_INTERVAL = int(os.environ.get('CHECK_INTERVAL', 60))  # seconds

def get_sig(params):
    return hmac.new(SECRET.encode(), params.encode(), hashlib.sha256).hexdigest()

def get_positions():
    ts = int(time.time() * 1000)
    params = f'timestamp={ts}'
    r = requests.get(f'https://fapi.binance.com/fapi/v2/positionRisk?{params}&signature={get_sig(params)}', 
                   headers={'X-MBX-APIKEY': API_KEY}, timeout=15)
    return [p for p in r.json() if float(p.get('positionAmt', 0)) != 0]

def get_price(symbol):
    # Use mark price for more accurate SL/TP checks
    ts = int(time.time() * 1000)
    params = f'timestamp={ts}'
    r = requests.get(f'https://fapi.binance.com/fapi/v2/positionRisk?symbol={symbol}&{params}&signature={get_sig(params)}', 
                   headers={'X-MBX-APIKEY': API_KEY}, timeout=15)
    data = r.json()
    if isinstance(data, list) and len(data) > 0:
        return float(data[0].get('markPrice', 0))
    return 0

def get_atr(symbol, period=14):
    """Get ATR for SL/TP calculation"""
    r = requests.get(f'https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval=1h&limit=50', timeout=10)
    candles = r.json()
    
    trs = []
    for i in range(1, min(period + 1, len(candles))):
        high = float(candles[-i][1])
        low = float(candles[-i][2])
        prev = float(candles[-i-1][3])
        tr = max(high - low, abs(high - prev), abs(low - prev))
        trs.append(tr)
    
    return sum(trs) / len(trs) if trs else None

def calculate_fibonacci_sl_tp(entry, atr, side):
    """Calculate SL/TP based on Fibonacci + ATR"""
    if side == 'LONG':
        sl = entry - (atr * 1.5)  # 1.5 ATR stop loss
        tp1 = entry + (atr * 3.0)  # TP1 at 3 ATR (Fib 1.272)
        tp2 = entry + (atr * 4.5)  # TP2 at 4.5 ATR (Fib 1.618)
    else:  # SHORT
        sl = entry + (atr * 1.5)
        tp1 = entry - (atr * 3.0)
        tp2 = entry - (atr * 4.5)
    
    return sl, tp1, tp2

def close_position(symbol, side, quantity):
    ts = int(time.time() * 1000)
    params = f'symbol={symbol}&side={side}&type=MARKET&quantity={quantity}&timestamp={ts}'
    r = requests.post(f'https://fapi.binance.com/fapi/v1/order?{params}&signature={get_sig(params)}',
                     headers={'X-MBX-APIKEY': API_KEY}, timeout=15)
    return r.json()

def send_telegram(msg):
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL:
        requests.post(f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage',
                    data={'chat_id': TELEGRAM_CHANNEL, 'text': msg, 'parse_mode': 'Markdown'})

def main():
    if not API_KEY or not SECRET:
        print("❌ ERROR: BINANCE_API_KEY and BINANCE_SECRET must be set in environment")
        return
    
    print(f"🔔 Price Monitor Starting...")
    print(f"   Check interval: {CHECK_INTERVAL}s")
    
    # Track triggered positions (per cycle)
    triggered = {}
    
    while True:
        try:
            positions = get_positions()
            
            # Clean triggered dict - keep only positions that are still open
            triggered = {s: t for s, t in triggered.items() if any(p.get('symbol') == s for p in positions)}
            
            if not positions:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] No positions")
                time.sleep(CHECK_INTERVAL)
                continue
            
            for p in positions:
                symbol = p.get('symbol')
                amt = float(p.get('positionAmt', 0))
                entry = float(p.get('entryPrice', 0) or 0)
                current = float(p.get('markPrice', 0) or 0)
                
                if not entry or entry == 0:
                    entry = get_price(symbol)
                
                if not current or current == 0:
                    current = get_price(symbol)
                
                side = 'LONG' if amt > 0 else 'SHORT'
                
                # Get ATR and calculate Fibonacci SL/TP
                atr = get_atr(symbol)
                if not atr:
                    atr = entry * 0.02  # Default 2% if no ATR
                
                sl_price, tp1, tp2 = calculate_fibonacci_sl_tp(entry, atr, side)
                
                current = get_price(symbol)
                
                # Debug: print levels
                print(f"  {symbol}: Entry={entry:.6f} Current={current:.6f} SL={sl_price:.6f} TP1={tp1:.6f} TP2={tp2:.6f} ATR={atr:.6f}")
                
                # Check if SL/TP hit
                hit = None
                if side == 'LONG':
                    if current <= sl_price:
                        hit = 'SL'
                    elif current >= tp1:
                        hit = 'TP'
                else:  # SHORT
                    if current >= sl_price:
                        hit = 'SL'
                    elif current <= tp1:
                        hit = 'TP'
                
                if hit and symbol not in triggered:
                    print(f"⚠️ {symbol} {hit} triggered! Closing...")
                    
                    close_side = 'SELL' if side == 'LONG' else 'BUY'
                    result = close_position(symbol, close_side, abs(amt))
                    
                    # Check if order was accepted
                    order_status = result.get('status', '')
                    if order_status not in ['NEW', 'FILLED', 'PARTIALLY_FILLED']:
                        print(f"  ❌ Close failed: {result}")
                        continue
                    
                    # Wait for order to fill and get actual exit price
                    order_id = result.get('orderId')
                    exit_price = 0
                    max_retries = 5
                    for _ in range(max_retries):
                        time.sleep(1)
                        check_params = f'orderId={order_id}&symbol={symbol}&timestamp={int(time.time() * 1000)}'
                        check_r = requests.get(f'https://fapi.binance.com/fapi/v1/order?{check_params}&signature={get_sig(check_params)}', 
                                              headers={'X-MBX-APIKEY': API_KEY}, timeout=15)
                        order_data = check_r.json()
                        status = order_data.get('status', '')
                        avg_price = float(order_data.get('avgPrice', 0))
                        if status == 'FILLED' and avg_price > 0:
                            exit_price = avg_price
                            break
                        elif status == 'FILLED':
                            # Use current price as fallback
                            exit_price = current
                            break
                    
                    # Fallback if still no exit price
                    if exit_price == 0:
                        exit_price = current
                    
                    # Calculate PnL using the actual exit price
                    if side == 'LONG':
                        pnl = (exit_price - entry) * abs(amt)
                        pnl_pct = ((exit_price - entry) / entry) * 100
                    else:
                        pnl = (entry - exit_price) * abs(amt)
                        pnl_pct = ((entry - exit_price) / entry) * 100
                    
                    emoji = "🟢" if pnl > 0 else "🔴"
                    
                    # Fix message - correctly show TP or SL
                    if hit == 'TP':
                        win_loss = "🎉💰 PROFIT TAKEN! 💰🎉"
                    else:
                        win_loss = "❌ STOP HIT"
                    
                    msg = f"{win_loss}\n\n"
                    msg += f"{emoji} {symbol} {side}\n"
                    msg += f"📈 {pnl_pct:+.2f}% (${pnl:+.2f})\n"
                    msg += f"Entry: ${entry:.6f} → Exit: ${exit_price:.6f}\n"
                    msg += f"Target: ${tp1:.6f} ({hit}) 🎯\n"
                    
                    if hit == 'SL':
                        msg += f"\n#StopLoss #Trading #Crypto"
                    else:
                        msg += f"\n#TakeProfit #Winning #Crypto"
                    
                    send_telegram(msg)
                    triggered[symbol] = hit
                    print(f"  ✅ Closed! {hit} | PnL: ${pnl:.2f}")
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Checked {len(positions)} positions")
            
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
        
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
