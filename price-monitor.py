#!/usr/bin/env python3
"""
Price Monitor - Auto close positions when SL/TP hit
Uses SL/TP saved by scanner.py
"""

import os
import time
import hmac
import hashlib
import requests
import json

from datetime import datetime

# === LOAD CONFIG ===
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from config import *
except ImportError:
    pass  # Use defaults

# === LOAD FROM ENV FILE ===
script_dir = os.path.dirname(os.path.abspath(__file__))
env_file = os.path.join(script_dir, '.env')

if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and '=' in line:
                k, v = line.split('=', 1)
                os.environ[k] = v

# === LOAD CONFIG ===
sys.path.insert(0, script_dir)
try:
    from config import *
except ImportError:
    pass

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

# === LOAD CONFIG FROM config.py ===
try:
    from config import *
except ImportError:
    pass
CHECK_INTERVAL = 15  # seconds (reduced from 60 — TP1 was missing price spikes)

def get_sig(params):
    return hmac.new(SECRET.encode(), params.encode(), hashlib.sha256).hexdigest()

def should_move_sl_to_breakeven(entry, current, sl, side, profit_threshold=1.0):
    """Move SL to breakeven when profit > threshold%"""
    if side == 'LONG':
        profit_pct = ((current - entry) / entry) * 100
        if profit_pct >= profit_threshold and sl < entry:
            return entry
    else:
        profit_pct = ((entry - current) / entry) * 100
        if profit_pct >= profit_threshold and sl > entry:
            return entry
    return None

def should_trail_sl(entry, current, sl, side, profit_threshold=5.0, trail_distance=2.0, lock_profit=2.0, peak_profit=None):
    """
    Trailing SL that locks in profit.
    When profit > profit_threshold%:
      - SL = max(entry + lock_profit%, current - trail_distance%)
      - Never moves SL down, only up
    
    FIX (2026-05-13): Added peak_profit parameter. If peak_profit ever hit
    the threshold but current pulled back, we still lock entry + lock_profit%.
    This prevents missed trailing SL when price spikes and retraces within
    the check interval.
    """
    if side == 'LONG':
        profit_pct = ((current - entry) / entry) * 100
        # Use peak_profit for threshold check if available (high-water mark)
        effective_peak = peak_profit if peak_profit is not None else profit_pct
        if effective_peak >= profit_threshold:
            # Minimum lock: entry + lock_profit%
            lock_sl = entry * (1 + lock_profit / 100)
            # Trailing: current - trail_distance%
            trail_sl = current * (1 - trail_distance / 100)
            # Use the higher of the two
            new_sl = max(lock_sl, trail_sl)
            # Only move SL up, never down
            if new_sl > sl:
                return new_sl
    else:
        profit_pct = ((entry - current) / entry) * 100
        effective_peak = peak_profit if peak_profit is not None else profit_pct
        if effective_peak >= profit_threshold:
            lock_sl = entry * (1 - lock_profit / 100)
            trail_sl = current * (1 + trail_distance / 100)
            new_sl = min(lock_sl, trail_sl)
            if new_sl < sl:
                return new_sl
    return None

def should_activate_trailing_tp(entry, current, tp, side, trail_percent=10.0, trail_distance=2.0):
    """Activate trailing TP when profit > trail_percent%.
    
    For LONG: TP trails trail_distance% BELOW current (triggers on pullback).
    For SHORT: TP trails trail_distance% ABOVE current (triggers on bounce).
    """
    if side == 'LONG':
        profit_pct = ((current - entry) / entry) * 100
        if profit_pct >= trail_percent:
            new_tp = current * (1 - trail_distance / 100)
            return new_tp if new_tp > entry else tp  # Never set TP below entry
    else:
        profit_pct = ((entry - current) / entry) * 100
        if profit_pct >= trail_percent:
            new_tp = current * (1 + trail_distance / 100)
            return new_tp if new_tp < entry else tp  # Never set TP above entry
    return None

def update_sl_to_breakeven(symbol, side, new_sl, tp_price=None):
    """Update stop loss via Binance API. Also replaces TP if tp_price provided.
    
    cancel_algo_orders removes ALL orders (SL + TP), so we must replace both.
    """
    headers = {'X-MBX-APIKEY': API_KEY}

    # Cancel existing algo orders for this symbol (SL + TP)
    cancel_algo_orders(symbol)
    
    ts = int(time.time() * 1000)
    close_side = 'SELL' if side == 'LONG' else 'BUY'
    
    # Round to tickSize for proper precision
    try:
        info_r = requests.get('https://fapi.binance.com/fapi/v1/exchangeInfo', timeout=10)
        tick_size = 0.00001
        for s in info_r.json().get('symbols', []):
            if s['symbol'] == symbol:
                for f in s.get('filters', []):
                    if f.get('filterType') == 'PRICE_FILTER':
                        tick_size = float(f.get('tickSize', 0.00001))
                break
        import math
        new_sl_rounded = float(math.floor(new_sl / tick_size) * tick_size)
    except:
        new_sl_rounded = new_sl
    
    # Place new SL
    params = f'symbol={symbol}&side={close_side}&type=STOP_MARKET&orderType=STOP_MARKET&algoType=CONDITIONAL&quantity=0&triggerPrice={new_sl_rounded}&stopPrice={new_sl_rounded}&workingType=CONTRACT_PRICE&closePosition=true&timestamp={ts}'
    sig = get_sig(params)
    sl_result = None
    try:
        r = requests.post(f'https://fapi.binance.com/fapi/v1/algoOrder?{params}&signature={sig}',
                        headers=headers, timeout=15)
        sl_result = r.json()
    except:
        pass
    
    # Replace TP if provided (cancel_algo_orders killed it)
    if tp_price:
        try:
            tp_rounded = float(math.floor(tp_price / tick_size) * tick_size)
        except:
            tp_rounded = tp_price
        ts2 = int(time.time() * 1000)
        tp_params = f'symbol={symbol}&side={close_side}&type=TAKE_PROFIT_MARKET&orderType=TAKE_PROFIT_MARKET&algoType=CONDITIONAL&quantity=0&triggerPrice={tp_rounded}&stopPrice={tp_rounded}&workingType=CONTRACT_PRICE&closePosition=true&timestamp={ts2}'
        tp_sig = get_sig(tp_params)
        try:
            requests.post(f'https://fapi.binance.com/fapi/v1/algoOrder?{tp_params}&signature={tp_sig}',
                         headers=headers, timeout=15)
        except:
            pass
    
    return sl_result

def update_tp_trailing(symbol, side, new_tp, sl_price=None):
    """Update TP to trailing level via Binance API.
    
    Cancels existing orders and replaces both TP and SL if sl_price provided.
    """
    headers = {'X-MBX-APIKEY': API_KEY}
    close_side = 'SELL' if side == 'LONG' else 'BUY'
    
    # Cancel existing algo orders (kills both SL and TP)
    cancel_algo_orders(symbol)
    
    # Round to tickSize for proper precision
    try:
        info_r = requests.get('https://fapi.binance.com/fapi/v1/exchangeInfo', timeout=10)
        tick_size = 0.00001
        for s in info_r.json().get('symbols', []):
            if s['symbol'] == symbol:
                for f in s.get('filters', []):
                    if f.get('filterType') == 'PRICE_FILTER':
                        tick_size = float(f.get('tickSize', 0.00001))
                break
        import math
        new_tp_rounded = float(math.floor(new_tp / tick_size) * tick_size)
    except:
        new_tp_rounded = new_tp
    
    # Place new TP
    ts = int(time.time() * 1000)
    params = f'symbol={symbol}&side={close_side}&type=TAKE_PROFIT_MARKET&orderType=TAKE_PROFIT_MARKET&algoType=CONDITIONAL&quantity=0&triggerPrice={new_tp_rounded}&stopPrice={new_tp_rounded}&workingType=CONTRACT_PRICE&closePosition=true&timestamp={ts}'
    sig = get_sig(params)
    tp_result = None
    try:
        r = requests.post(f'https://fapi.binance.com/fapi/v1/algoOrder?{params}&signature={sig}',
                        headers=headers, timeout=15)
        tp_result = r.json()
    except:
        pass
    
    # Replace SL if provided (cancel_algo_orders killed it)
    if sl_price:
        try:
            sl_rounded = float(math.floor(sl_price / tick_size) * tick_size)
        except:
            sl_rounded = sl_price
        ts2 = int(time.time() * 1000)
        sl_params = f'symbol={symbol}&side={close_side}&type=STOP_MARKET&orderType=STOP_MARKET&algoType=CONDITIONAL&quantity=0&triggerPrice={sl_rounded}&stopPrice={sl_rounded}&workingType=CONTRACT_PRICE&closePosition=true&timestamp={ts2}'
        sl_sig = get_sig(sl_params)
        try:
            requests.post(f'https://fapi.binance.com/fapi/v1/algoOrder?{sl_params}&signature={sl_sig}',
                         headers=headers, timeout=15)
        except:
            pass
    
    return tp_result

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

def get_algo_open_orders(symbol=None):
    """Get open algo orders via GET /fapi/v1/openAlgoOrders.
    
    Algo orders (STOP_MARKET, TAKE_PROFIT_MARKET placed via /fapi/v1/algoOrder)
    are NOT returned by /fapi/v1/openOrders — they need this dedicated endpoint.
    """
    headers = {'X-MBX-APIKEY': API_KEY}
    try:
        ts = int(time.time() * 1000)
        if symbol:
            params = f'symbol={symbol}&timestamp={ts}'
        else:
            params = f'timestamp={ts}'
        sig = get_sig(params)
        r = requests.get(
            f'https://fapi.binance.com/fapi/v1/openAlgoOrders?{params}&signature={sig}',
            headers=headers, timeout=15
        )
        if r.status_code == 200:
            data = r.json()
            # API may return dict with 'orders' key or a plain list
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return data.get('orders', [])
            return []
    except Exception as e:
        print(f"  ⚠️ Get algo orders error: {e}")
    return []

def has_sl_tp_orders(symbol):
    """Check if a position has both SL and TP orders (algo or regular)."""
    # Check algo orders (placed via /fapi/v1/algoOrder)
    algo_orders = get_algo_open_orders(symbol)
    has_algo_sl = any('STOP' in o.get('orderType', '') for o in algo_orders)
    has_algo_tp = any('TAKE_PROFIT' in o.get('orderType', '') for o in algo_orders)
    
    # Check regular orders (placed via /fapi/v1/order)
    headers = {'X-MBX-APIKEY': API_KEY}
    try:
        ts = int(time.time() * 1000)
        params = f'symbol={symbol}&timestamp={ts}'
        sig = get_sig(params)
        r = requests.get(
            f'https://fapi.binance.com/fapi/v1/openOrders?{params}&signature={sig}',
            headers=headers, timeout=10
        )
        if r.status_code == 200:
            orders = r.json() if isinstance(r.json(), list) else []
            has_reg_sl = any('STOP' in o.get('type', '') for o in orders)
            has_reg_tp = any('TAKE_PROFIT' in o.get('type', '') for o in orders)
        else:
            has_reg_sl, has_reg_tp = False, False
    except:
        has_reg_sl, has_reg_tp = False, False
    
    return (has_algo_sl or has_reg_sl), (has_algo_tp or has_reg_tp)

def cancel_algo_orders(symbol):
    """Cancel all open algo AND regular SL/TP orders for a symbol.
    
    Some positions have algo orders (via /fapi/v1/algoOrder),
    others have regular orders (via /fapi/v1/order). Cancel both types.
    Only cancels SL/TP order types, not limit entry orders.
    """
    headers = {'X-MBX-APIKEY': API_KEY}
    cancelled = False
    
    # 1. Cancel algo orders via DELETE /fapi/v1/algoOpenOrders
    try:
        ts = int(time.time() * 1000)
        params = f'symbol={symbol}&timestamp={ts}'
        sig = get_sig(params)
        r = requests.delete(
            f'https://fapi.binance.com/fapi/v1/algoOpenOrders?{params}&signature={sig}',
            headers=headers, timeout=15
        )
        if r.status_code == 200:
            cancelled = True
    except Exception as e:
        print(f"  ⚠️ Cancel algo orders error for {symbol}: {e}")
    
    # 2. Cancel regular SL/TP orders individually (via openOrders query)
    try:
        ts2 = int(time.time() * 1000)
        params2 = f'symbol={symbol}&timestamp={ts2}'
        sig2 = get_sig(params2)
        r2 = requests.get(
            f'https://fapi.binance.com/fapi/v1/openOrders?{params2}&signature={sig2}',
            headers=headers, timeout=10
        )
        if r2.status_code == 200 and isinstance(r2.json(), list):
            for o in r2.json():
                otype = o.get('type', '')
                # Only cancel SL/TP orders, NOT limit entry orders
                if 'STOP' in otype or 'TAKE_PROFIT' in otype:
                    ts3 = int(time.time() * 1000)
                    cp = f'symbol={symbol}&orderId={o["orderId"]}&timestamp={ts3}'
                    cs = get_sig(cp)
                    requests.delete(
                        f'https://fapi.binance.com/fapi/v1/order?{cp}&signature={cs}',
                        headers=headers, timeout=10
                    )
                    cancelled = True
    except Exception as e:
        print(f"  ⚠️ Cancel regular orders error for {symbol}: {e}")
    
    if cancelled:
        print(f"  🧹 Cancelled orders for {symbol}")
    return cancelled

def place_sl_tp_only(symbol, side, quantity, sl_price, tp_price):
    """Place SL and TP algo orders after a limit order is filled."""
    headers = {'X-MBX-APIKEY': API_KEY}
    
    # Get tick size for rounding
    try:
        info_r = requests.get('https://fapi.binance.com/fapi/v1/exchangeInfo', timeout=10)
        tick_size = 0.00001
        for s in info_r.json().get('symbols', []):
            if s['symbol'] == symbol:
                for f in s.get('filters', []):
                    if f.get('filterType') == 'PRICE_FILTER':
                        tick_size = float(f.get('tickSize', 0.00001))
                break
    except:
        tick_size = 0.00001
    
    def round_to_tick(price, tick):
        tick_str = f"{tick:.10f}".rstrip('0')
        decimals = len(tick_str.split('.')[1]) if '.' in tick_str else 0
        return float(f"{price:.{decimals}f}")
    
    sl_trigger = round_to_tick(sl_price, tick_size)
    tp_trigger = round_to_tick(tp_price, tick_size)
    
    sl_side = "SELL" if side == "BUY" else "BUY"
    tp_side = "SELL" if side == "BUY" else "BUY"
    
    # Place SL
    sl_params = "symbol={}&side={}&type=STOP_MARKET&orderType=STOP_MARKET&algoType=CONDITIONAL&quantity={}&reduceOnly=true&triggerPrice={}&stopPrice={}&workingType=CONTRACT_PRICE&timestamp={}".format(
        symbol, sl_side, quantity, sl_trigger, sl_trigger, int(time.time() * 1000))
    sl_sig = get_sig(sl_params)
    sl_url = "https://fapi.binance.com/fapi/v1/algoOrder?{}&signature={}".format(sl_params, sl_sig)
    try:
        sl_r = requests.post(sl_url, headers=headers, timeout=10)
        if sl_r.status_code == 200:
            print(f"    🛡 SL placed: {sl_trigger}")
        else:
            print(f"    ⚠️ SL failed: {sl_r.text[:80]}")
    except Exception as e:
        print(f"    ⚠️ SL error: {e}")
    
    # Place TP
    tp_params = "symbol={}&side={}&type=TAKE_PROFIT_MARKET&orderType=TAKE_PROFIT_MARKET&algoType=CONDITIONAL&quantity={}&reduceOnly=true&triggerPrice={}&stopPrice={}&workingType=CONTRACT_PRICE&timestamp={}".format(
        symbol, tp_side, quantity, tp_trigger, tp_trigger, int(time.time() * 1000))
    tp_sig = get_sig(tp_params)
    tp_url = "https://fapi.binance.com/fapi/v1/algoOrder?{}&signature={}".format(tp_params, tp_sig)
    try:
        tp_r = requests.post(tp_url, headers=headers, timeout=10)
        if tp_r.status_code == 200:
            print(f"    📈 TP placed: {tp_trigger}")
        else:
            print(f"    ⚠️ TP failed: {tp_r.text[:80]}")
    except Exception as e:
        print(f"    ⚠️ TP error: {e}")


def close_position(symbol, side, quantity):
    ts = int(time.time() * 1000)
    params = f'symbol={symbol}&side={side}&type=MARKET&quantity={quantity}&timestamp={ts}'
    sig = get_sig(params)
    r = requests.post(f'https://fapi.binance.com/fapi/v1/order?{params}&signature={sig}',
                     headers={'X-MBX-APIKEY': API_KEY}, timeout=15)
    result = r.json()

    # Cancel orphaned SL/TP algo orders after position closes
    if result.get('orderId'):
        cancel_algo_orders(symbol)

    return result

def log_trade(symbol, side, entry, exit_price, qty, pnl, reason, signal_data=None):
    """Log closed trade to .trade_history.json for metrics tracking.
    
    If signal_data is provided (indicator scores at entry), include them in the log
    for later correlation analysis between indicators and PNL outcomes.
    """
    import json
    from datetime import datetime
    history_file = os.path.join(os.path.dirname(__file__), '.trade_history.json')
    trades = []
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r') as f:
                trades = json.load(f)
        except:
            trades = []
    trade_entry = {
        'symbol': symbol, 'side': side,
        'entry': entry, 'exit': exit_price, 'qty': qty,
        'pnl': pnl,
        'pnl_pct': ((exit_price - entry) / entry * 100) if side == 'LONG' else ((entry - exit_price) / entry * 100),
        'reason': reason, 'closed_at': datetime.now().isoformat(),
    }
    # Enrich with indicator scores at entry for correlation analysis
    if signal_data:
        trade_entry['signal'] = {
            'score': signal_data.get('signal_score', 0),
            'rsi': signal_data.get('signal_rsi', 50),
            'adx': signal_data.get('signal_adx', 0),
            'stoch_rsi_k': signal_data.get('signal_stoch_rsi_k', 50),
            'fisher': signal_data.get('signal_fisher', 0),
            'taker_ratio': signal_data.get('signal_taker_ratio', 1.0),
            'chop': signal_data.get('signal_chop', 50),
            'vol_ratio': signal_data.get('signal_vol_ratio', 1),
            'ema_position': signal_data.get('signal_ema_position', 50),
            'macd_histogram': signal_data.get('signal_macd_histogram', 0),
            'squeeze': signal_data.get('signal_squeeze', 0),
            'direction': signal_data.get('signal_direction', side),
            'plus_di': signal_data.get('signal_plus_di', 0),
            'minus_di': signal_data.get('signal_minus_di', 0),
            'price_change': signal_data.get('signal_price_change', 0),
            'weekly_change': signal_data.get('signal_weekly_change', 0),
            'oi_change': signal_data.get('signal_oi_change', 0),
        }
    trades.append(trade_entry)
    with open(history_file, 'w') as f:
        json.dump(trades, f, indent=2)
    print(f"    📝 Trade logged: {symbol} {side} PNL={pnl:.2f} ({reason})")


def notify_trade(notification_type, data):
    """Send notification based on config settings"""
    # Check if posting is enabled
    post_enabled = True
    try:
        post_enabled = POST_SIGNALS_TO_TELEGRAM
    except:
        pass
    
    if not post_enabled:
        return False
    
    # Check specific notification types
    try:
        if notification_type == 'close' and not NOTIFY_ON_CLOSE:
            return False
        elif notification_type == 'breakeven' and not NOTIFY_ON_BREAKEVEN:
            return False
        elif notification_type == 'trailing_tp' and not NOTIFY_ON_TRAILING_TP:
            return False
    except:
        pass
    
    msg = ""
    
    if notification_type == 'close':
        msg = f"""🔴 *POSITION CLOSED*

🔖 Symbol: {data['symbol']}
📊 Type: {data['close_type']}
💵 Entry: ${data['entry']:.6f}
💵 Exit: ${data['exit']:.6f}
💰 PnL: ${data['pnl']:.2f}"""
    
    elif notification_type == 'breakeven':
        msg = f"""🛡 *TRAILING STOP LOSS*

🔖 Symbol: {data['symbol']}
💵 Entry: ${data['entry']:.6f}
🛡 New SL: ${data['sl']:.6f}
💰 Current Profit: {data['profit_pct']:.2f}%"""
    
    elif notification_type == 'trailing_tp':
        msg = f"""📈 *TRAILING TP ACTIVATED*

🔖 Symbol: {data['symbol']}
📈 Old TP: ${data['old_tp']:.6f}
📈 New TP: ${data['new_tp']:.6f}
💰 Current Profit: {data['profit_pct']:.2f}%"""
    
    elif notification_type == 'error':
        msg = f"""❌ *TRADING ERROR*

🔖 Symbol: {data['symbol']}
📝 Error: {data['error']}"""
    
    if msg:
        return send_telegram(msg)
    return False

def add_to_recently_closed(symbol):
    """Add symbol to recently closed list"""
    try:
        with open('.recently_closed', 'a') as f:
            f.write(f'{symbol},{int(time.time())}\n')
    except:
        pass

def send_telegram(msg):
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL:
        requests.post(f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage',
                    data={'chat_id': TELEGRAM_CHANNEL, 'text': msg, 'parse_mode': 'Markdown'})

def check_multi_tp(symbol, side, entry, current, position_amt, original_amt, pos_data=None):
    """Check for multi-TP levels and close partial positions.
    
    TP1: Close TP1_CLOSE_PCT (25%) at TP1_PERCENT (5%) profit
    TP2: Close TP2_CLOSE_PCT (25%) at TP2_PERCENT (10%) profit
    Remaining 50% runs to PRICE_TP or trailing TP
    
    FIX (2026-05-10): Added tp1_done/tp2_done flags to prevent double-close.
    FIX (2026-05-12): Added high-water mark (peak_profit) — if profit EVER hit
    the TP level, trigger TP even if current profit pulled back. This prevents
    missed TPs when price spikes and retraces within the check interval.
    """
    if side == 'LONG':
        profit_pct = ((current - entry) / entry) * 100
    else:
        profit_pct = ((entry - current) / entry) * 100
    
    # Load config
    try:
        tp1 = TP1_PERCENT
        tp2 = TP2_PERCENT
        tp1_pct = TP1_CLOSE_PCT
        tp2_pct = TP2_CLOSE_PCT
    except:
        tp1, tp2 = 5.0, 10.0
        tp1_pct, tp2_pct = 0.25, 0.25
    
    # Check flags to prevent double-close across loop iterations
    tp1_done = pos_data.get('tp1_done', False) if pos_data else False
    tp2_done = pos_data.get('tp2_done', False) if pos_data else False
    
    # === HIGH-WATER MARK: Track peak profit ===
    # If profit EVER hit a TP level, we trigger it even on pullback
    peak_profit = pos_data.get('peak_profit', 0.0) if pos_data else 0.0
    if profit_pct > peak_profit:
        peak_profit = profit_pct
        if pos_data is not None:
            pos_data['peak_profit'] = peak_profit
    
    remaining_pct = (abs(position_amt) / original_amt) * 100 if original_amt > 0 else 0
    close_side = 'SELL' if side == 'LONG' else 'BUY'
    
    # TP2: Close tp2_pct at +tp2% (if peak ever reached OR current >= tp2)
    if (profit_pct >= tp2 or peak_profit >= tp2) and remaining_pct > (tp2_pct * 100) and not tp2_done:
        close_amt = abs(original_amt * tp2_pct)
        result = close_position(symbol, close_side, close_amt)
        if result and 'orderId' in result:
            if pos_data is not None:
                pos_data['tp2_done'] = True
            log_trade(symbol, side, entry, current, close_amt, 
                     (current - entry) * close_amt if side == 'LONG' else (entry - current) * close_amt,
                     'TP2', pos_data)
            trigger_reason = "peak" if peak_profit >= tp2 and profit_pct < tp2 else "live"
            print(f"    📈 TP2 HIT! Closed {tp2_pct*100:.0f}% at +{profit_pct:.2f}% (peak={peak_profit:.2f}%, {trigger_reason})")
            return True
    
    # TP1: Close tp1_pct at +tp1% (if peak ever reached OR current >= tp1)
    if (profit_pct >= tp1 or peak_profit >= tp1) and remaining_pct > (tp1_pct * 100) and not tp1_done:
        close_amt = abs(original_amt * tp1_pct)
        result = close_position(symbol, close_side, close_amt)
        if result and 'orderId' in result:
            if pos_data is not None:
                pos_data['tp1_done'] = True
            log_trade(symbol, side, entry, current, close_amt,
                     (current - entry) * close_amt if side == 'LONG' else (entry - current) * close_amt,
                     'TP1', pos_data)
            trigger_reason = "peak" if peak_profit >= tp1 and profit_pct < tp1 else "live"
            print(f"    📈 TP1 HIT! Closed {tp1_pct*100:.0f}% at +{profit_pct:.2f}% (peak={peak_profit:.2f}%, {trigger_reason})")
            return True
    
    return False

def main():
    if not API_KEY or not SECRET:
        print("❌ ERROR: API keys not set")
        return
    
    print(f"🔔 Price Monitor Starting...")
    print(f"   Check interval: {CHECK_INTERVAL}s (adaptive: 5s when in-profit)")
    print(f"   Trailing SL: peak-profit tracking enabled")
    
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
                    # Continue to SL/TP checks and trailing logic below
                else:
                    # FIX (2026-05-13): Auto-calculate SL/TP from ATR when missing
                    # Previously skipped entirely — positions had NO protection at all
                    atr = get_atr(symbol)
                    if atr and entry > 0:
                        if side == 'LONG':
                            sl_price = entry - (atr * 2)
                            tp_price = entry + (atr * 4)
                        else:
                            sl_price = entry + (atr * 2)
                            tp_price = entry - (atr * 4)
                        pos_data['sl'] = sl_price
                        pos_data['tp1'] = tp_price
                        pos_data['side'] = 'BUY' if side == 'LONG' else 'SELL'
                        pos_data['entry'] = entry
                        pos_data['original_amt'] = abs(amt)
                        saved_data[symbol] = pos_data
                        save_positions_sl_tp(saved_data)
                        print(f"  {symbol}: [AUTO-CALC] Entry={entry:.6f} SL={sl_price:.6f} TP={tp_price:.6f} (ATR={atr:.6f})")
                    else:
                        # Fallback: use percentage-based SL/TP from config
                        try:
                            sl_pct = PRICE_SL / 100
                            tp_pct = PRICE_TP / 100
                        except:
                            sl_pct, tp_pct = 0.05, 0.15
                        if side == 'LONG':
                            sl_price = entry * (1 - sl_pct)
                            tp_price = entry * (1 + tp_pct)
                        else:
                            sl_price = entry * (1 + sl_pct)
                            tp_price = entry * (1 - tp_pct)
                        pos_data['sl'] = sl_price
                        pos_data['tp1'] = tp_price
                        pos_data['side'] = 'BUY' if side == 'LONG' else 'SELL'
                        pos_data['entry'] = entry
                        pos_data['original_amt'] = abs(amt)
                        saved_data[symbol] = pos_data
                        save_positions_sl_tp(saved_data)
                        print(f"  {symbol}: [FALLBACK] Entry={entry:.6f} SL={sl_price:.6f} TP={tp_price:.6f} (config %)")

                # === AUTO-HEAL MISSING SL/TP (2026-05-20) ===
                # Verify Binance side has both SL and TP placed. If scanner failed to
                # place them on entry (network glitch, timeout, etc), they go missing
                # forever. Detect + re-place. Throttled to avoid hitting rate limits.
                heal_throttle_key = f'_heal_check_{symbol}'
                last_heal_check = pos_data.get(heal_throttle_key, 0)
                if (time.time() - last_heal_check) > 300:  # check every 5 min per symbol
                    try:
                        has_sl, has_tp = has_sl_tp_orders(symbol)
                        if not has_sl or not has_tp:
                            close_side = 'SELL' if side == 'LONG' else 'BUY'
                            # Get tickSize for proper rounding
                            try:
                                info_r = requests.get('https://fapi.binance.com/fapi/v1/exchangeInfo', timeout=10)
                                tick_size = 0.00001
                                for s_info in info_r.json().get('symbols', []):
                                    if s_info['symbol'] == symbol:
                                        for f in s_info.get('filters', []):
                                            if f.get('filterType') == 'PRICE_FILTER':
                                                tick_size = float(f.get('tickSize', 0.00001))
                                        break
                                import math
                                # Round to tickSize multiple AND format to correct decimals
                                tick_str = f"{tick_size:.10f}".rstrip('0')
                                decimals = len(tick_str.split('.')[1]) if '.' in tick_str else 0
                                sl_floor = math.floor(sl_price / tick_size) * tick_size
                                tp_floor = math.floor(tp_price / tick_size) * tick_size
                                sl_rounded = float(f"{sl_floor:.{decimals}f}")
                                tp_rounded = float(f"{tp_floor:.{decimals}f}")
                            except:
                                sl_rounded, tp_rounded = sl_price, tp_price

                            if not has_sl:
                                print(f"  {symbol}: [HEAL] Missing SL — placing @ {sl_rounded}")
                                ts_h = int(time.time() * 1000)
                                sl_p = f'symbol={symbol}&side={close_side}&type=STOP_MARKET&orderType=STOP_MARKET&algoType=CONDITIONAL&quantity=0&triggerPrice={sl_rounded}&stopPrice={sl_rounded}&workingType=CONTRACT_PRICE&closePosition=true&timestamp={ts_h}'
                                try:
                                    rh = requests.post(f'https://fapi.binance.com/fapi/v1/algoOrder?{sl_p}&signature={get_sig(sl_p)}',
                                                       headers={'X-MBX-APIKEY': API_KEY}, timeout=15)
                                    if rh.status_code == 200:
                                        print(f"  {symbol}: [HEAL] ✅ SL placed")
                                    else:
                                        print(f"  {symbol}: [HEAL] ⚠️ SL failed: {rh.text[:100]}")
                                except Exception as e:
                                    print(f"  {symbol}: [HEAL] ⚠️ SL error: {e}")

                            if not has_tp:
                                print(f"  {symbol}: [HEAL] Missing TP — placing @ {tp_rounded}")
                                ts_h = int(time.time() * 1000)
                                tp_p = f'symbol={symbol}&side={close_side}&type=TAKE_PROFIT_MARKET&orderType=TAKE_PROFIT_MARKET&algoType=CONDITIONAL&quantity=0&triggerPrice={tp_rounded}&stopPrice={tp_rounded}&workingType=CONTRACT_PRICE&closePosition=true&timestamp={ts_h}'
                                try:
                                    rh = requests.post(f'https://fapi.binance.com/fapi/v1/algoOrder?{tp_p}&signature={get_sig(tp_p)}',
                                                       headers={'X-MBX-APIKEY': API_KEY}, timeout=15)
                                    if rh.status_code == 200:
                                        print(f"  {symbol}: [HEAL] ✅ TP placed")
                                    else:
                                        print(f"  {symbol}: [HEAL] ⚠️ TP failed: {rh.text[:100]}")
                                except Exception as e:
                                    print(f"  {symbol}: [HEAL] ⚠️ TP error: {e}")

                        pos_data[heal_throttle_key] = time.time()
                        saved_data[symbol] = pos_data
                        save_positions_sl_tp(saved_data)
                    except Exception as e:
                        print(f"  {symbol}: [HEAL] ⚠️ check error: {e}")

                # Check for Multi-TP levels (partial closes)
                # Store original amount in pos_data so it persists across iterations
                if 'original_amt' not in pos_data:
                    pos_data['original_amt'] = abs(amt)
                    saved_data[symbol] = pos_data
                    save_positions_sl_tp(saved_data)
                original_amt = pos_data.get('original_amt', abs(amt))
                tp_hit = check_multi_tp(symbol, side, entry, current, amt, original_amt, pos_data)
                # Persist flags + peak_profit to disk after any change
                if tp_hit or pos_data.get('peak_profit', 0.0) > 0:
                    saved_data[symbol] = pos_data
                    save_positions_sl_tp(saved_data)
                
                # === TRAILING SL — MUST RUN BEFORE SL HIT CHECK ===
                # FIX (2026-05-13): Moved trailing SL update BEFORE SL hit check.
                # Previously, if price spiked down, position would close at old SL
                # instead of the updated trailing SL, causing unnecessary losses.
                try:
                    be_thresh = MIN_PROFIT_BREAKEVEN if 'MIN_PROFIT_BREAKEVEN' in dir() else 5.0
                    trail_dist_sl = TRAIL_SL_DISTANCE if 'TRAIL_SL_DISTANCE' in dir() else 2.0
                    lock_pct = TRAIL_SL_LOCK if 'TRAIL_SL_LOCK' in dir() else 2.0
                except:
                    be_thresh = 5.0
                    trail_dist_sl = 2.0
                    lock_pct = 2.0
                # Use peak_profit from multi-TP tracking (high-water mark)
                peak_profit = pos_data.get('peak_profit', 0.0)
                profit_now = ((current - entry) / entry * 100) if side == 'LONG' else ((entry - current) / entry * 100)
                # Update peak_profit here too (for positions without multi-TP)
                if profit_now > peak_profit:
                    peak_profit = profit_now
                    pos_data['peak_profit'] = peak_profit
                new_trail_sl = should_trail_sl(entry, current, sl_price, side,
                    profit_threshold=be_thresh, trail_distance=trail_dist_sl, lock_profit=lock_pct,
                    peak_profit=peak_profit)
                if new_trail_sl and new_trail_sl != sl_price:
                    trigger_reason = "peak" if peak_profit >= be_thresh and profit_now < be_thresh else "live"
                    print(f"    🛡 Trailing SL: {sl_price:.6f} -> {new_trail_sl:.6f} (profit: {profit_now:.1f}%, peak: {peak_profit:.1f}%, {trigger_reason})")
                    update_sl_to_breakeven(symbol, side, new_trail_sl, tp_price)
                    notify_trade('breakeven', {
                        'symbol': symbol,
                        'entry': entry,
                        'sl': new_trail_sl,
                        'profit_pct': profit_now
                    })
                    sl_price = new_trail_sl
                    # Persist new SL to disk so it survives restarts
                    pos_data['sl'] = sl_price
                    saved_data[symbol] = pos_data
                    save_positions_sl_tp(saved_data)

                # Check for trailing TP - activate when profit > configured %
                try:
                    trail_thresh = MIN_PROFIT_TRAILING_TP if 'MIN_PROFIT_TRAILING_TP' in dir() else 10.0
                    trail_dist = TRAIL_PERCENT if 'TRAIL_PERCENT' in dir() else 2.0
                except:
                    trail_thresh = 10.0
                    trail_dist = 2.0
                new_trailing_tp = should_activate_trailing_tp(entry, current, tp_price, side, trail_percent=trail_thresh, trail_distance=trail_dist)
                if new_trailing_tp and new_trailing_tp != tp_price:
                    print(f"    📈 Trailing TP: {tp_price:.6f} -> {new_trailing_tp:.6f}")
                    update_tp_trailing(symbol, side, new_trailing_tp, sl_price)
                    tp_price = new_trailing_tp
                    # Mark as trailing TP — only close on pullback, not immediately
                    pos_data['trailing_tp_active'] = True
                    # Persist new TP to disk
                    pos_data['tp1'] = tp_price
                    saved_data[symbol] = pos_data
                    save_positions_sl_tp(saved_data)

                # === AGGRESSIVE AUTO-CLOSE ===
                # Check if SL should trigger (price crosses SL level)
                if side == 'LONG' and current <= sl_price:
                    print(f"    🚨 LONG SL HIT! {current:.6f} <= {sl_price:.6f}")
                    result = close_position(symbol, 'SELL', abs(amt))
                    if result and 'orderId' in result:
                        pnl = (current - entry) * abs(amt)
                        notify_trade('close', {
                            'symbol': symbol, 'close_type': 'SL',
                            'entry': entry, 'exit': current, 'pnl': pnl
                        })
                        log_trade(symbol, side, entry, current, abs(amt), pnl, 'SL', pos_data)
                        add_to_recently_closed(symbol)
                    continue
                
                elif side == 'SHORT' and current >= sl_price:
                    print(f"    🚨 SHORT SL HIT! {current:.6f} >= {sl_price:.6f}")
                    result = close_position(symbol, 'BUY', abs(amt))
                    if result and 'orderId' in result:
                        pnl = (entry - current) * abs(amt)
                        notify_trade('close', {
                            'symbol': symbol, 'close_type': 'SL',
                            'entry': entry, 'exit': current, 'pnl': pnl
                        })
                        log_trade(symbol, side, entry, current, abs(amt), pnl, 'SL', pos_data)
                        add_to_recently_closed(symbol)
                    continue
                
                # Check if TP should trigger
                # FIX (2026-05-13): When trailing TP is active, only close on pullback.
                # Previously, trailing TP would close immediately because current > TP.
                # Now: trailing TP only triggers when price drops TO the TP level.
                is_trailing_tp = pos_data.get('trailing_tp_active', False)
                if side == 'LONG':
                    if is_trailing_tp:
                        # Pullback: close when price drops to or below trailing TP
                        tp_hit = current <= tp_price
                    else:
                        # Normal TP: close when price reaches TP
                        tp_hit = current >= tp_price
                    if tp_hit:
                        close_reason = "Trailing TP pullback" if is_trailing_tp else "TP"
                        print(f"    🎯 LONG TP HIT! {current:.6f} ({close_reason}) TP={tp_price:.6f}")
                        result = close_position(symbol, 'SELL', abs(amt))
                        if result and 'orderId' in result:
                            pnl = (current - entry) * abs(amt)
                            notify_trade('close', {
                                'symbol': symbol, 'close_type': 'TP',
                                'entry': entry, 'exit': current, 'pnl': pnl
                            })
                            log_trade(symbol, side, entry, current, abs(amt), pnl, 'TP', pos_data)
                            add_to_recently_closed(symbol)
                        continue
                
                elif side == 'SHORT':
                    if is_trailing_tp:
                        # Pullback: close when price rises to or above trailing TP
                        tp_hit = current >= tp_price
                    else:
                        # Normal TP: close when price reaches TP
                        tp_hit = current <= tp_price
                    if tp_hit:
                        close_reason = "Trailing TP pullback" if is_trailing_tp else "TP"
                        print(f"    🎯 SHORT TP HIT! {current:.6f} ({close_reason}) TP={tp_price:.6f}")
                        result = close_position(symbol, 'BUY', abs(amt))
                        if result and 'orderId' in result:
                            pnl = (entry - current) * abs(amt)
                            notify_trade('close', {
                                'symbol': symbol, 'close_type': 'TP',
                                'entry': entry, 'exit': current, 'pnl': pnl
                        })
                        log_trade(symbol, side, entry, current, abs(amt), pnl, 'TP', pos_data)
                        add_to_recently_closed(symbol)
                    continue

                # (end of position loop — trailing SL already updated above before SL/TP checks)
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Checked {len(positions)} positions")
            
            # Persist peak_profit changes to disk
            save_positions_sl_tp(saved_data)
            
            # Adaptive interval: faster when positions are in profit
            has_profit = False
            for p in positions:
                sym = p.get('symbol')
                pd = saved_data.get(sym, {})
                if pd.get('peak_profit', 0.0) > 3.0:
                    has_profit = True
                    break
            next_interval = 5 if has_profit else CHECK_INTERVAL
            
        except Exception as e:
            print(f"Error: {e}")
            next_interval = CHECK_INTERVAL
        
        time.sleep(next_interval)

if __name__ == "__main__":
    main()
