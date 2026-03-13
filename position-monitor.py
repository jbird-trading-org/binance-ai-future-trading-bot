#!/usr/bin/env python3
"""
Neko Sentinel - Position Monitor with Quick Rescan
Triggers immediate scan when positions close
"""

import hmac, hashlib, time, requests, json, os
from datetime import datetime

API_KEY = 'Vi9YDQ8qFK4a3he1vbv9gXFYYok75CK3GlU21LmkPZRf0Y8dAWQicqtKic8AEKPp'
SECRET = 'f6wzxpMtieMkEqBLxDwswocfQCvSSpxEFbggF9T9s6zjYet62NlXfHKCxQq4pdN7'
TELEGRAM_CHANNEL = "-1003847994290"
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

STATE_FILE = '/root/.openclaw/workspace/.position_state.json'
SCAN_INTERVAL = 60  # Check every 60 seconds
SCAN_AFTER_CLOSE = True

def get_signature(params):
    return hmac.new(SECRET.encode(), params.encode(), hashlib.sha256).hexdigest()

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

def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except:
        return {}

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)

def send_telegram(msg):
    if not TELEGRAM_BOT_TOKEN:
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, data={'chat_id': TELEGRAM_CHANNEL, 'text': msg}, timeout=30)
        return r.status_code == 200
    except:
        return False

def quick_scan():
    """Trigger immediate scan"""
    print("🔍 Quick scan triggered...")
    os.system('cd /root/.openclaw/workspace && TELEGRAM_BOT_TOKEN=***REDACTED_TELEGRAM_TOKEN*** python3 binance-scanner.py >> /root/.openclaw/workspace/scanner.log 2>&1')

def main():
    print("👀 Watching positions...")
    prev_state = load_state()
    
    while True:
        positions = get_positions()
        current_positions = {}
        open_count = 0
        
        for pos in positions:
            symbol = pos.get('symbol', '')
            amt = float(pos.get('positionAmt', 0))
            if amt != 0:
                current_positions[symbol] = {
                    'amt': abs(amt),
                    'entry': float(pos.get('entryPrice', 0) or 0),
                    'pnl': float(pos.get('unrealizedProfit', 0) or 0)
                }
                open_count += 1
        
        # Check for closed positions
        closed = []
        if prev_state:
            for symbol in prev_state:
                if symbol not in current_positions:
                    prev = prev_state[symbol]
                    pnl = prev.get('pnl', 0)
                    emoji = "🎉" if pnl > 0 else "💔"
                    closed.append(f"{emoji} {symbol} closed - PnL: ${pnl:.2f}")
        
        # Alert if positions closed
        if closed:
            print("⚠️ Positions closed detected!")
            for c in closed:
                print(f"  {c}")
                send_telegram(f"📊 POSITION CLOSED\n{c}\n\n🔍 Triggering quick scan...")
            
            # Quick rescan
            if SCAN_AFTER_CLOSE:
                quick_scan()
        
        # Alert if all closed
        if open_count == 0 and prev_state:
            print("⚠️ All positions closed!")
            msg = "⚠️ ALL POSITIONS CLOSED - Triggering quick scan for new opportunities..."
            send_telegram(msg)
            if SCAN_AFTER_CLOSE:
                quick_scan()
        
        save_state(current_positions)
        print(f"  Watching: {open_count} positions | Next check in {SCAN_INTERVAL}s")
        time.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    main()
