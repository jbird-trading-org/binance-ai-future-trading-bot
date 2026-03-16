#!/usr/bin/env python3
"""
Price Monitor - Auto close positions when SL/TP hit
No algo orders needed - just monitors and closes manually
"""

import os
import time
import hmac
import hashlib
import requests
from datetime import datetime

# === CONFIG ===
API_KEY = os.environ.get('BINANCE_API_KEY', '3EEWdnVXIdygfKe2mwFC7640bmE4JuBSk6XVkBK7BIB9TNyagUWzAbQUBl75aN5n')
SECRET = os.environ.get('BINANCE_SECRET', 'kaxEZJRVaqHKxWM4cIr9b3cl3CEUk82XHpEVwSFkQzY2sOdmzNWbbcfQtNI2xhqr')

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '***REDACTED_TELEGRAM_TOKEN***')
TELEGRAM_CHANNEL = os.environ.get('TELEGRAM_CHANNEL', '-1003847994290')

CHECK_INTERVAL = 60  # Check every 60 seconds

def get_sig(params):
    return hmac.new(SECRET.encode(), params.encode(), hashlib.sha256).hexdigest()

def get_positions():
    ts = int(time.time() * 1000)
    params = f'timestamp={ts}'
    r = requests.get(f'https://fapi.binance.com/fapi/v3/account?{params}&signature={get_sig(params)}', 
                   headers={'X-MBX-APIKEY': API_KEY}, timeout=15)
    return [p for p in r.json().get('positions', []) if float(p.get('positionAmt', 0)) != 0]

def get_price(symbol):
    r = requests.get(f'https://fapi.binance.com/fapi/v1/ticker/price?symbol={symbol}', timeout=10)
    return float(r.json()['price'])

def close_position(symbol, side, quantity):
    ts = int(time.time() * 1000)
    params = f'symbol={symbol}&side={side}&type=MARKET&quantity={quantity}&timestamp={ts}'
    r = requests.post(f'https://fapi.binance.com/fapi/v1/order?{params}&signature={get_sig(params)}',
                     headers={'X-MBX-APIKEY': API_KEY}, timeout=15)
    return r.json()

def send_telegram(msg):
    requests.post(f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage',
                data={'chat_id': TELEGRAM_CHANNEL, 'text': msg, 'parse_mode': 'Markdown'})

def main():
    print(f"🔔 Price Monitor Starting...")
    
    # Track triggered positions
    triggered = {}
    
    while True:
        try:
            positions = get_positions()
            
            if not positions:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] No positions")
                time.sleep(CHECK_INTERVAL)
                continue
            
            for p in positions:
                symbol = p.get('symbol')
                amt = float(p.get('positionAmt', 0))
                entry = float(p.get('entryPrice', 0) or 0)
                
                if not entry or entry == 0:
                    entry = get_price(symbol)
                
                side = 'LONG' if amt > 0 else 'SHORT'
                direction = 1 if side == 'LONG' else -1
                
                # Default SL/TP (3% / 5%)
                sl_price = entry * (0.97 if side == 'LONG' else 1.03)
                tp_price = entry * (1.05 if side == 'LONG' else 0.95)
                
                current = get_price(symbol)
                
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
                
                if hit and symbol not in triggered:
                    print(f"⚠️ {symbol} {hit} triggered! Closing...")
                    
                    close_side = 'SELL' if side == 'LONG' else 'BUY'
                    result = close_position(symbol, close_side, abs(amt))
                    
                    msg = f"🚨 {hit} TRIGGERED!\n\n"
                    msg += f"{symbol} {side}\n"
                    msg += f"Entry: ${entry:.6f}\n"
                    msg += f"Current: ${current:.6f}\n"
                    msg += f"Target: ${sl_price if hit == 'SL' else tp_price:.6f}\n"
                    msg += f"\n✅ Position Closed"
                    
                    send_telegram(msg)
                    triggered[symbol] = True
                    print(f"  Closed! {hit}")
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Checked {len(positions)} positions")
            
        except Exception as e:
            print(f"Error: {e}")
        
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
