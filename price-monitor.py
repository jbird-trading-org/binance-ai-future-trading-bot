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

def close_position_limit(symbol, side, quantity, limit_price):
    """Close position using LIMIT order at specific price for accuracy"""
    ts = int(time.time() * 1000)
    # Use GTC (Good Till Cancel) and place at exact TP/SL price
    params = f'symbol={symbol}&side={side}&type=LIMIT&quantity={quantity}&price={limit_price}&timeInForce=GTC&timestamp={ts}'
    r = requests.post(f'https://fapi.binance.com/fapi/v1/order?{params}&signature={get_sig(params)}',
                     headers={'X-MBX-APIKEY': API_KEY}, timeout=15)
    return r.json()

def close_position_market(symbol, side, quantity):
    """Close position using MARKET order"""
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
                
                # Check if SL/TP hit - STRICT logic
                # For LONG: SL must be BELOW entry, TP must be ABOVE entry
                # For SHORT: SL must be ABOVE entry, TP must be BELOW entry
                hit = None
                target_price = 0
                
                if side == 'LONG':
                    # LONG: Entry > SL (SL below entry), Entry < TP (TP above entry)
                    # SL hit: price goes DOWN to SL (current < sl_price < entry)
                    # TP hit: price goes UP to TP (current > tp1 > entry)
                    
                    # STRICT: Only trigger if price has actually moved to the level
                    if current <= sl_price and sl_price < entry:
                        # Price dropped below SL
                        hit = 'SL'
                        target_price = sl_price
                    elif current >= tp1 and tp1 > entry:
                        # Price rose above TP1
                        hit = 'TP'
                        target_price = tp1
                        
                else:  # SHORT
                    # SHORT: Entry < SL (SL above entry), Entry > TP (TP below entry)
                    # SL hit: price goes UP to SL (current > sl_price > entry)
                    # TP hit: price goes DOWN to TP (current < tp1 < entry)
                    
                    if current >= sl_price and sl_price > entry:
                        # Price rose above SL
                        hit = 'SL'
                        target_price = sl_price
                    elif current <= tp1 and tp1 < entry:
                        # Price dropped below TP1
                        hit = 'TP'
                        target_price = tp1
                
                if hit and symbol not in triggered:
                    print(f"⚠️ {symbol} {hit} triggered! Verifying...")
                    
                    # DOUBLE CHECK - wait 60 seconds and verify price is still at level
                    print(f"  ⏳ Waiting 60s to confirm...")
                    time.sleep(60)
                    current_check = get_price(symbol)
                    
                    # STRICT verification - must still be at the level
                    still_hit = False
                    if side == 'LONG':
                        if hit == 'SL' and current_check <= sl_price and sl_price < entry:
                            still_hit = True
                        elif hit == 'TP' and current_check >= tp1 and tp1 > entry:
                            still_hit = True
                    else:
                        if hit == 'SL' and current_check >= sl_price and sl_price > entry:
                            still_hit = True
                        elif hit == 'TP' and current_check <= tp1 and tp1 < entry:
                            still_hit = True
                    
                    if not still_hit:
                        print(f"  ⚠️ False alarm - price recovered. Current={current_check:.6f} Entry={entry:.6f}")
                        triggered[symbol] = hit  # Mark as checked
                        continue
                    
                    print(f"  ✅ Confirmed! Closing at {target_price:.6f}...")
                    
                    close_side = 'SELL' if side == 'LONG' else 'BUY'
                    
                    # Try LIMIT order first at exact TP/SL price
                    result = close_position_limit(symbol, close_side, abs(amt), round(target_price, 6))
                    
                    # Check if LIMIT order was accepted
                    order_status = result.get('status', '')
                    if order_status in ['NEW', 'FILLED', 'PARTIALLY_FILLED']:
                        print(f"  📝 LIMIT order placed at {target_price:.6f}")
                    else:
                        # Fallback to MARKET if LIMIT fails
                        print(f"  ⚠️ LIMIT failed, using MARKET")
                        result = close_position_market(symbol, close_side, abs(amt))
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
                            exit_price = current_check
                            break
                    
                    # Fallback if still no exit price
                    if exit_price == 0:
                        exit_price = current_check
                    
                    # Calculate PnL using the actual exit price
                    if side == 'LONG':
                        pnl = (exit_price - entry) * abs(amt)
                        pnl_pct = ((exit_price - entry) / entry) * 100
                    else:
                        pnl = (entry - exit_price) * abs(amt)
                        pnl_pct = ((entry - exit_price) / entry) * 100
                    
                    emoji = "🟢" if pnl > 0 else "🔴"
                    
                    # Correct message based on hit type
                    if hit == 'TP':
                        win_loss = "🎉💰 PROFIT TAKEN! 💰🎉"
                    else:
                        win_loss = "❌ STOP HIT"
                    
                    msg = f"{win_loss}\n\n"
                    msg += f"{emoji} {symbol} {side}\n"
                    # Format message to match template
                    fib_note = "Fib 1.272" if hit == 'TP' else ""
                    
                    msg = f"{win_loss}\n\n"
                    msg += f"{emoji} {symbol} {side}\n"
                    msg += f"📈 {pnl_pct:+.2f}% (${pnl:+.2f})\n"
                    msg += f"Entry: ${entry:.6f} → Exit: ${exit_price:.6f}\n"
                    msg += f"\n"
                    msg += f"🛡 SL: ${sl_price:.6f} (1.5×ATR)\n"
                    msg += f"📈 TP1: ${tp1:.6f} (3×ATR)\n"
                    msg += f"📈 TP2: ${tp2:.6f} (4.5×ATR)\n"
                    msg += f"🎯 Hit: {hit} @ ${target_price:.6f}\n"
                    
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
