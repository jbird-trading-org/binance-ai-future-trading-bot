#!/usr/bin/env python3
"""
Price Monitor - Auto close positions when SL/TP hit
Uses SL/TP saved by scanner-v8.py
"""

import os
import time
import hmac
import hashlib
import requests
import json
from datetime import datetime

# === LOAD FROM ENV FILE ===
script_dir = os.path.dirname(os.path.abspath(__file__))
env_file = os.path.join(script_dir, '.env')

if env_file and os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

API_KEY = os.environ.get('BINANCE_API_KEY', '')
SECRET = os.environ.get('BINANCE_SECRET', '')
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHANNEL = os.environ.get('TELEGRAM_CHANNEL', '')

POSITIONS_FILE = os.path.join(script_dir, '.positions_sl_tp.json')
CHECK_INTERVAL = 60  # seconds

def get_sig(params):
    return hmac.new(SECRET.encode(), params.encode(), hashlib.sha256).hexdigest()

def get_positions():
    ts = int(time.time() * 1000)
    params = f'timestamp={ts}'
    r = requests.get(f'https://fapi.binance.com/fapi/v2/positionRisk?{params}&signature={get_sig(params)}', 
                   headers={'X-MBX-APIKEY': API_KEY}, timeout=15)
    return [p for p in r.json() if float(p.get('positionAmt', 0)) != 0]

def get_price(symbol):
    ts = int(time.time() * 1000)
    params = f'timestamp={ts}'
    r = requests.get(f'https://fapi.binance.com/fapi/v2/positionRisk?symbol={symbol}&{params}&signature={get_sig(params)}', 
                   headers={'X-MBX-APIKEY': API_KEY}, timeout=15)
    data = r.json()
    if isinstance(data, list) and len(data) > 0:
        return float(data[0].get('markPrice', 0))
    return 0

def load_positions_sl_tp():
    try:
        if os.path.exists(POSITIONS_FILE):
            with open(POSITIONS_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return {}

def get_atr(symbol, period=14):
    """Get ATR for SL/TP calculation - Template: 1h period"""
    try:
        r = requests.get(f'https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval=1h&limit={period+1}', timeout=10)
        candles = r.json()
        
        if len(candles) < period + 1:
            return None
        
        trs = []
        for i in range(1, len(candles)):
            high = float(candles[i][2])  # High
            low = float(candles[i][3])    # Low
            prev_close = float(candles[i-1][4])  # Previous close
            
            # True Range = max(High - Low, |High - PrevClose|, |Low - PrevClose|)
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            trs.append(tr)
        
        return sum(trs) / len(trs) if trs else None
    except:
        return None

def save_positions_sl_tp(data):
    try:
        with open(POSITIONS_FILE, 'w') as f:
            json.dump(data, f)
    except:
        pass

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
        print("❌ ERROR: API keys not set")
        return
    
    print(f"🔔 Price Monitor Starting...")
    print(f"   Check interval: {CHECK_INTERVAL}s")
    
    while True:
        try:
            # Get current open positions from Binance
            positions = get_positions()
            open_symbols = {p.get('symbol') for p in positions}
            
            # Load saved SL/TP data
            saved_data = load_positions_sl_tp()
            
            # Clean stale entries
            stale = [s for s in saved_data if s not in open_symbols]
            if stale:
                for s in stale:
                    del saved_data[s]
                save_positions_sl_tp(saved_data)
                print(f"  🗑 Cleaned {len(stale)} stale positions")
            
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
                
                # Get SL/TP from saved data, or calculate from ATR
                pos_data = saved_data.get(symbol, {})
                
                if pos_data and 'sl' in pos_data and 'tp1' in pos_data:
                    # Use saved SL/TP from scanner
                    sl_price = float(pos_data['sl'])
                    tp_price = float(pos_data['tp1'])
                    print(f"  {symbol}: [SAVED] Entry={entry:.6f} Current={current:.6f} SL={sl_price:.6f} TP={tp_price:.6f}")
                else:
                    # Calculate SL/TP from ATR (template formula)
                    atr = get_atr(symbol)
                    if not atr:
                        atr = entry * 0.02  # Default 2%
                    
                    if side == 'LONG':
                        sl_price = entry - (atr * 1.5)  # Template: Entry - 1.5×ATR
                        tp_price = entry + (atr * 3.0)   # Template: Entry + 3×ATR
                    else:  # SHORT
                        sl_price = entry + (atr * 1.5)
                        tp_price = entry - (atr * 3.0)
                    
                    print(f"  {symbol}: [CALC] Entry={entry:.6f} Current={current:.6f} SL={sl_price:.6f} TP={tp_price:.6f} (ATR={atr:.6f})")
                
                # Check if SL/TP hit
                hit = None
                if side == 'LONG':
                    if current <= sl_price:
                        hit = 'SL'
                    elif current >= tp_price:
                        hit = 'TP'
                else:  # SHORT
                    if current >= sl_price:
                        hit = 'SL'
                    elif current <= tp_price:
                        hit = 'TP'
                
                if hit:
                    print(f"    ⚠️ {hit} triggered! Waiting 60s to confirm...")
                    time.sleep(60)
                    
                    # Verify still hit
                    current_check = get_price(symbol)
                    still_hit = False
                    
                    if side == 'LONG':
                        if hit == 'SL' and current_check <= sl_price:
                            still_hit = True
                        elif hit == 'TP' and current_check >= tp_price:
                            still_hit = True
                    else:
                        if hit == 'SL' and current_check >= sl_price:
                            still_hit = True
                        elif hit == 'TP' and current_check <= tp_price:
                            still_hit = True
                    
                    if not still_hit:
                        print(f"    ⚠️ False alarm - price recovered")
                        continue
                    
                    print(f"    ✅ Confirmed! Closing...")
                    
                    # Close position
                    close_side = 'SELL' if side == 'LONG' else 'BUY'
                    result = close_position(symbol, close_side, abs(amt))
                    
                    order_status = result.get('status', '')
                    order_id = result.get('orderId')
                    
                    if order_status not in ['NEW', 'FILLED', 'PARTIALLY_FILLED']:
                        print(f"    ❌ Close failed: {result}")
                        continue
                    
                    # Wait for order to fill and get actual exit price
                    exit_price = 0
                    max_retries = 10
                    for i in range(max_retries):
                        time.sleep(1)
                        check_params = f'orderId={order_id}&symbol={symbol}&timestamp={int(time.time() * 1000)}'
                        check_r = requests.get(f'https://fapi.binance.com/fapi/v1/order?{check_params}&signature={get_sig(check_params)}', 
                                              headers={'X-MBX-APIKEY': API_KEY}, timeout=15)
                        order_data = check_r.json()
                        status = order_data.get('status', '')
                        avg_price = float(order_data.get('avgPrice', 0))
                        
                        if status == 'FILLED' and avg_price > 0:
                            exit_price = avg_price
                            print(f"    📝 Order filled at {exit_price:.6f}")
                            break
                        elif status == 'FILLED':
                            # Use current price as fallback
                            exit_price = current_check
                            break
                    
                    # Fallback if still no exit price
                    if exit_price == 0:
                        exit_price = current_check
                        print(f"    ⚠️ Using current price: {exit_price:.6f}")
                    
                    # Calculate PnL
                    if side == 'LONG':
                        pnl = (exit_price - entry) * abs(amt)
                        pnl_pct = ((exit_price - entry) / entry) * 100
                    else:
                        pnl = (entry - exit_price) * abs(amt)
                        pnl_pct = ((entry - exit_price) / entry) * 100
                    
                    emoji = "🟢" if pnl > 0 else "🔴"
                    
                    # Send Telegram
                    if hit == 'TP':
                        msg = f"🎉💰 PROFIT TAKEN! 💰🎉\n\n"
                    else:
                        msg = f"❌ STOP HIT\n\n"
                    
                    msg += f"{emoji} {symbol} {side}\n"
                    msg += f"📈 {pnl_pct:+.2f}% (${pnl:+.2f})\n"
                    msg += f"Entry: ${entry:.6f} → Exit: ${exit_price:.6f}\n"
                    msg += f"\n"
                    msg += f"🛡 SL: ${sl_price:.6f}\n"
                    msg += f"📈 TP: ${tp_price:.6f}\n"
                    msg += f"🎯 Hit: {hit}\n"
                    
                    if hit == 'SL':
                        msg += f"\n#StopLoss #Trading #Crypto"
                    else:
                        msg += f"\n#TakeProfit #Winning #Crypto"
                    
                    send_telegram(msg)
                    
                    # Remove from saved
                    if symbol in saved_data:
                        del saved_data[symbol]
                        save_positions_sl_tp(saved_data)
                    
                    print(f"    ✅ Closed! {hit} | PnL: ${pnl:.2f}")
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Checked {len(positions)} positions")
            
        except Exception as e:
            print(f"Error: {e}")
        
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
